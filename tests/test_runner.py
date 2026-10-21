import io
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from koans_lib.cli import main
from koans_lib.runner import (
    CourseError, Result, digest, failure_message, first_failure, inside,
    installed_tools, load_course, presentation, read_source, rho_result, run_process,
)


COST = 'Estimated deploy cost: Cost { value: 42, operation: "subtraction" }\n'
PRESENTATION = '''Presentation
  Types { Value; }
  Exports { }
  Terms {
    Zero .  |- "0" : Value;
  }
  Equations {
  }
  Rewrites {
  }
'''


class AdapterTests(unittest.TestCase):
    def observe(self, text, events, mode="unordered"):
        return rho_result(Result(True, "completed", stdout=text), {"mode": mode, "events": events})

    def test_unordered_output_preserves_multiplicity(self):
        self.assertTrue(self.observe('2\n1\n2\n' + COST, ['1', '2', '2']).passed)
        self.assertFalse(self.observe('2\n1\n' + COST, ['1', '2', '2']).passed)
        self.assertFalse(self.observe('2\n1\n2\n' + COST, ['1', '2']).passed)

    def test_ordered_output_and_string_types(self):
        self.assertFalse(self.observe('2\n1\n' + COST, ['1', '2'], "ordered").passed)
        self.assertFalse(self.observe('"1"\n' + COST, ['1']).passed)
        self.assertTrue(self.observe('1\n' + COST, ['1'], "ordered").passed)

    def test_exit_zero_does_not_hide_runtime_error_after_correct_output(self):
        raw = '7\n' + COST + 'Errors received during evaluation:\nDivision by zero\n'
        result = self.observe(raw, ['7'])
        self.assertFalse(result.passed)
        self.assertEqual(result.kind, "runtime")
        self.assertEqual(result.stdout, raw)

    def test_no_output_fails_and_blank_lines_are_not_discarded(self):
        self.assertEqual(self.observe(COST, ['1']).kind, "no-output")
        self.assertEqual(self.observe('\n' + COST, ['1']).actual, [''])

    def test_unknown_backend_output_is_infrastructure_error(self):
        with self.assertRaisesRegex(CourseError, "footer"):
            self.observe('1\nnew protocol\n', ['1'])

    def test_presentation_is_parsed_as_definitions(self):
        self.assertEqual(presentation(PRESENTATION), {
            "Types": ["Value"], "Exports": [],
            "Terms": ['Zero .  |- "0" : Value;'], "Equations": [], "Rewrites": [],
        })
        for text in ("", PRESENTATION.replace("Presentation", "Changed"),
                     PRESENTATION.rstrip()[:-1], PRESENTATION + "unexpected\n"):
            with self.subTest(text=text), self.assertRaises(CourseError):
                presentation(text)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="koan-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "exercises").mkdir()
        (self.root / "starters").mkdir()
        (self.root / "solutions").mkdir()
        (self.root / "toolchain.lock.json").write_text('{}')
        binary_dir = self.root / ".toolchain/bin"
        binary_dir.mkdir(parents=True)
        self.tools = {}
        for backend, name in (("rho", "rholang-cli"), ("module", "mettail-elab")):
            tool = binary_dir / name
            tool.write_text("#!/bin/sh\nexit 0\n")
            tool.chmod(0o755)
            self.tools[backend] = tool
        self.write_receipt()
        self.exercises = []
        for n in range(1, 4):
            source, solution = f"exercises/{n}.rho", f"solutions/{n}.rho"
            for name in (source, solution, f"starters/{n}.rho"):
                (self.root / name).write_text('new stdout(`rho:io:stdout`) in {stdout!(__)}\n')
            self.exercises.append({
                "id": str(n), "chapter": "Fixture", "title": "Example", "context": "Print 7.",
                "source": source, "solution": solution, "backend": "rho",
                "hints": ["Use a number.", "The number is seven."],
                "expect": {"mode": "unordered", "events": ["7"]},
            })
        self.write_course()

    def write_receipt(self):
        (self.root / ".toolchain/installed.json").write_text(json.dumps({
            "lock_sha256": digest(self.root / "toolchain.lock.json"),
            "binaries": {p.name: digest(p) for p in self.tools.values()},
        }))

    def write_course(self):
        (self.root / "course.json").write_text(json.dumps({"version": 1, "exercises": self.exercises}))


class CourseTests(Fixture):
    def test_path_traversal_and_symlink_escape_are_rejected(self):
        with self.assertRaises(CourseError):
            inside(self.root, "../outside")
        (self.root / "outside").symlink_to(self.root.parent)
        with self.assertRaises(CourseError):
            inside(self.root, "outside/file")

    def test_manifest_requires_unique_ids_and_output_assertions(self):
        self.exercises[1]["id"] = "1"
        self.write_course()
        with self.assertRaisesRegex(CourseError, "Duplicate"):
            load_course(self.root)
        self.exercises[1]["id"] = "2"
        self.exercises[0]["expect"]["events"] = []
        self.write_course()
        with self.assertRaisesRegex(CourseError, "expectations"):
            load_course(self.root)

    def test_changed_binary_and_lock_require_setup(self):
        self.assertEqual(installed_tools(self.root), self.tools)
        self.tools["rho"].write_text("changed")
        with self.assertRaisesRegex(CourseError, "Run ./setup"):
            installed_tools(self.root)
        self.write_receipt()
        (self.root / "toolchain.lock.json").write_text('{"version":2}')
        with self.assertRaisesRegex(CourseError, "lock changed"):
            installed_tools(self.root)

    def test_stops_before_later_exercises(self):
        with patch("koans_lib.runner.evaluate", side_effect=[Result(True, "pass"), Result(False, "assertion")]) as call:
            index, result = first_failure(self.root, self.exercises, self.tools, 1)
        self.assertEqual(index, 1)
        self.assertFalse(result.passed)
        self.assertEqual(call.call_count, 2)

    def test_success_cache_invalidates_on_earlier_edits(self):
        cache = {}
        with patch("koans_lib.runner.evaluate", return_value=Result(True, "pass")) as call:
            first_failure(self.root, self.exercises, self.tools, 1, cache)
            first_failure(self.root, self.exercises, self.tools, 1, cache)
            self.assertEqual(call.call_count, 3)
            (self.root / self.exercises[0]["source"]).write_text("changed")
            call.return_value = Result(False, "compiler")
            index, _ = first_failure(self.root, self.exercises, self.tools, 1, cache)
            self.assertEqual(index, 0)
            self.assertEqual(call.call_count, 4)

    def test_cache_invalidates_for_import_manifest_tool_and_lock(self):
        e = self.exercises[0]
        support = self.root / "exercises/support.module"
        support.write_text("initial")
        e["inputs"] = ["exercises/support.module"]
        cache = {}
        with patch("koans_lib.runner.evaluate", return_value=Result(True, "pass")) as call:
            first_failure(self.root, [e], self.tools, 1, cache)
            support.write_text("edited")
            first_failure(self.root, [e], self.tools, 1, cache)
            e["expect"]["events"] = ["8"]
            first_failure(self.root, [e], self.tools, 1, cache)
            p = self.tools["rho"]
            os.utime(p, ns=(p.stat().st_atime_ns, p.stat().st_mtime_ns + 1))
            first_failure(self.root, [e], self.tools, 1, cache)
            (self.root / "toolchain.lock.json").write_text("changed")
            first_failure(self.root, [e], self.tools, 1, cache)
            self.assertEqual(call.call_count, 5)

    def test_native_diagnostic_and_source_position_are_preserved(self):
        e = self.exercises[0]
        (self.root / e["source"]).write_text('// __ is a hole\nNil\nbroken\n')
        diagnostic = 'Parse failed: SourcePos { line: 3, col: 2 }\nmore detail\n'
        result = Result(False, "compiler", stderr=diagnostic)
        message = failure_message(self.root, self.exercises, 0, result)
        self.assertIn(diagnostic.rstrip(), message)
        self.assertIn('>   3 | broken', message)
        self.assertNotIn(e["hints"][1], message)
        self.assertIn(e["hints"][1], failure_message(self.root, self.exercises, 0, result, True))

    def test_cli_statuses_pass_fail_infrastructure(self):
        for result, expected in ((None, 0), (Result(False, "compiler", stderr="native error"), 1)):
            with self.subTest(status=expected), patch("koans_lib.cli.first_failure", return_value=(0, result)), patch("sys.stdout", new=io.StringIO()):
                self.assertEqual(main(["--once"], self.root), expected)
        (self.root / "course.json").write_text("{")
        with patch("sys.stderr", new=io.StringIO()), patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(main(["--once"], self.root), 2)

    def test_invalid_timeout_is_rejected(self):
        for value in ("0", "-1", "nan", "inf"):
            with self.subTest(value=value), patch("sys.stderr", new=io.StringIO()), self.assertRaises(SystemExit) as error:
                main(["--timeout", value], self.root)
            self.assertEqual(error.exception.code, 2)


class ChapterTests(Fixture):
    def setUp(self):
        super().setUp()
        self.chapter = self.root / "exercises/koans.rho"
        self.chapter.write_text('// Chapter\n\n// koan: 1 — First\nstdout!(__)\n\n// koan: 2 — Second\nstdout!(__)\n')
        for e in self.exercises[:2]:
            e.update(source="exercises/koans.rho", section=e["id"])

    def test_sections_have_independent_source_and_original_line_numbers(self):
        one, two = [read_source(self.root, e) for e in self.exercises[:2]]
        self.assertEqual(one.text, 'stdout!(__)\n\n')
        self.assertEqual((one.first_line, one.last_line), (4, 5))
        self.assertEqual(two.text, 'stdout!(__)\n')
        self.assertEqual((two.first_line, two.last_line), (7, 7))

    def test_missing_and_duplicate_markers_have_actionable_errors(self):
        e = self.exercises[0]
        self.chapter.write_text('// koan: 2\nNil\n')
        with self.assertRaisesRegex(CourseError, "Missing '// koan: 1'.*exercises/koans.rho"):
            read_source(self.root, e)
        self.chapter.write_text('// koan: 1\nNil\n// koan: 1\nNil\n')
        with self.assertRaisesRegex(CourseError, "Duplicate koan marker"):
            read_source(self.root, e)

    def test_source_context_is_limited_to_current_koan(self):
        message = failure_message(self.root, self.exercises, 1, Result(False, "assertion", ["9"]))
        self.assertIn('exercises/koans.rho:7', message)
        self.assertIn('>   7 | stdout!(__)', message)
        self.assertNotIn('4 |', message)

    def test_editing_later_section_keeps_earlier_success_cached(self):
        for backend, comment, suffix in (("rho", "//", ".rho"), ("module", "--", ".module")):
            with self.subTest(backend=backend):
                chapter = self.chapter.with_suffix(suffix)
                e = {**self.exercises[0], "backend": backend, "source": str(chapter.relative_to(self.root))}
                chapter.write_text(f'{comment} koan: 1\nfirst\n{comment} koan: 2\nsecond\n')
                cache = {}
                with patch("koans_lib.runner.evaluate", return_value=Result(True, "pass")) as call:
                    first_failure(self.root, [e], self.tools, 1, cache)
                    chapter.write_text(f'{comment} koan: 1\nfirst\n{comment} koan: 2\nedited\nwith more lines\n')
                    first_failure(self.root, [e], self.tools, 1, cache)
                    self.assertEqual(call.call_count, 1)
                    chapter.write_text(chapter.read_text().replace("first", "changed"))
                    first_failure(self.root, [e], self.tools, 1, cache)
                    self.assertEqual(call.call_count, 2)


class ProcessTests(unittest.TestCase):
    def test_native_error_streams_are_retained(self):
        result = run_process([sys.executable, "-c", "import sys; print('output'); print('native error',file=sys.stderr); sys.exit(3)"], Path.cwd(), 2)
        self.assertEqual((result.kind, result.stdout, result.stderr), ("compiler", "output\n", "native error\n"))

    def test_panic_exit_is_a_crash(self):
        result = run_process([sys.executable, "-c", "raise SystemExit(101)"], Path.cwd(), 2)
        self.assertEqual(result.kind, "crash")

    def test_timeout_kills_process_group_and_keeps_partial_output(self):
        with tempfile.TemporaryDirectory() as work:
            child = Path(work) / "child.pid"
            code = '''import subprocess, sys, time
p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
open(sys.argv[1], 'w').write(str(p.pid))
print('started', flush=True)
time.sleep(30)
'''
            result = run_process([sys.executable, "-c", code, str(child)], Path(work), 0.5)
            self.assertEqual(result.kind, "timeout")
            self.assertEqual(result.stdout, "started\n")
            pid = int(child.read_text())
            # A killed child may remain a zombie briefly until reaped by init.
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                try:
                    state = Path(f"/proc/{pid}/stat").read_text().split()[2]
                except FileNotFoundError:
                    return
                if state == "Z":
                    return
                time.sleep(0.02)
            os.kill(pid, signal.SIGKILL)
            self.fail("the timed-out tool left a live child process")


if __name__ == "__main__":
    unittest.main()
