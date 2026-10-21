import io
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from unittest.mock import patch

from koans_lib import setup
from koans_lib.cli import main
from koans_lib.runner import evaluate, installed_tools


PROJECT = Path(__file__).resolve().parent.parent
EMPTY_PRESENTATION = {k: [] for k in ("Types", "Exports", "Terms", "Equations", "Rewrites")}


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Deliberately fail with a setup instruction, not a silent skipped suite.
        cls.tools = installed_tools(PROJECT)

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="koan-native-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def program(self, code, backend="rho", expect=None):
        source = self.root / ("example.rho" if backend == "rho" else "example.module")
        source.write_text(code)
        e = {"source": source.name, "backend": backend, "expect": expect or {"mode": "unordered", "events": ["7"]}}
        return evaluate(self.root, e, self.tools, timeout=3)

    def rho(self, body, events=None):
        return self.program('new stdout(`rho:io:stdout`) in {\n' + body + '\n}',
                            expect={"mode": "unordered", "events": events or ["7"]})

    def test_compiler_error_keeps_native_position(self):
        result = self.rho('stdout!(unknown)')
        self.assertEqual(result.kind, "compiler")
        self.assertIn("unknown", result.stderr)
        self.assertIn("line: 2", result.stderr)

    def test_zero_exit_runtime_error_is_a_failure(self):
        result = self.rho('stdout!(7) | stdout!(1 / 0)')
        self.assertEqual(result.kind, "runtime")
        self.assertIn("Errors received during evaluation:", result.stdout)
        self.assertIn("Division by zero", result.stdout)

    def test_waiting_receive_does_not_pass_silently(self):
        result = self.rho('new c in { for (@x <- c) { stdout!(x) } }')
        self.assertEqual(result.kind, "no-output")

    def test_evaluations_have_independent_storage(self):
        first = self.rho('@"leftover"!(7) | stdout!(7)')
        second = self.rho('for (@x <- @"leftover") { stdout!(x) }')
        self.assertTrue(first.passed, first)
        self.assertEqual(second.kind, "no-output")

    def test_guarded_join_preserves_messages_for_accepting_join(self):
        result = self.rho('''new a, b in {
          a!(4) | b!(6) |
          for (@x <- a & @y <- b where x > y) { stdout!(-1) } |
          for (@x <- a & @y <- b where x < y) { stdout!(x + y) }
        }''', ["10"])
        self.assertTrue(result.passed, result)

    def test_guarded_match_falls_through(self):
        result = self.rho('match 4 { x where x > 10 => {stdout!(0)} _ => {stdout!(7)} }')
        self.assertTrue(result.passed, result)

    def test_elaboration_requires_the_right_definitions(self):
        expected = {**EMPTY_PRESENTATION, "Types": ["Required"]}
        result = self.program('Module M { Theory T() { Types { Other; } } theory T() }', "module", expected)
        self.assertEqual(result.kind, "assertion")
        self.assertEqual(result.actual["Types"], ["Other"])

    def test_duplicate_constructor_diagnostic(self):
        result = self.program('''Module M { Theory T() {
          Types { Value; }
          Terms { One . |- "1" : Value; One . |- "one" : Value; }
        } theory T() }''', "module", EMPTY_PRESENTATION)
        self.assertEqual(result.kind, "compiler")
        self.assertIn("One", result.stderr)
        self.assertIn("example.module", result.stderr)

    def test_missing_import_keeps_resolver_diagnostic(self):
        result = self.program('import "absent.module" as lib\nModule M { theory lib.T() }', "module", EMPTY_PRESENTATION)
        self.assertEqual(result.kind, "compiler")
        self.assertIn("absent.module", result.stderr)

    def test_import_cycle_is_reported(self):
        (self.root / "a.module").write_text('import "example.module" as other\nModule A { theory other.T() }')
        result = self.program('import "a.module" as a\nModule M { Theory T() { Types { V; } } theory a.T() }', "module", EMPTY_PRESENTATION)
        self.assertEqual(result.kind, "compiler")
        self.assertIn("cycle", result.stderr.lower())

    def test_chapter_isolation_and_native_error_locations(self):
        source = self.root / "koans.rho"
        source.write_text('''// Chapter
// koan: good
new stdout(`rho:io:stdout`) in { stdout!(7) }
// koan: bad
new stdout(`rho:io:stdout`) in {
  stdout!(missing)
}
// koan: unfinished
new { this is deliberately invalid
''')
        e = {"source": source.name, "section": "good", "backend": "rho",
             "expect": {"mode": "unordered", "events": ["7"]}}
        result = evaluate(self.root, e, self.tools)
        self.assertTrue(result.passed, result)
        e["section"] = "bad"
        result = evaluate(self.root, e, self.tools)
        self.assertEqual(result.kind, "compiler")
        self.assertIn(str(source), result.stderr)
        self.assertIn("line: 6", result.stderr)
        self.assertNotIn("f1r3lang-koan-", result.stderr)

    def test_module_chapter_preserves_imports_and_diagnostic_locations(self):
        chapter = self.root / "exercises/chapter/koans.module"
        chapter.parent.mkdir(parents=True)
        support = self.root / "exercises/support"
        support.mkdir()
        (support / "base.module").write_text('Module Base { Theory T() { Types { Value; } } theory T() }')
        (support / "lib.module").write_text('import "base.module" as base\nModule Lib { Theory T() { base.T() } theory T() }')
        chapter.write_text('''-- koan: good
import "../support/lib.module" as lib
Module Good { theory lib.T() }
-- koan: bad
Module Bad {
  Theory T() { Types { Value; } Terms { Zero . |- "0" : Missing; } }
  theory T()
}
-- koan: later
this is unfinished
''')
        e = {"source": str(chapter.relative_to(self.root)), "section": "good", "backend": "module",
             "expect": {**EMPTY_PRESENTATION, "Types": ["Value"]}}
        result = evaluate(self.root, e, self.tools)
        self.assertTrue(result.passed, result)
        e["section"] = "bad"
        result = evaluate(self.root, e, self.tools)
        self.assertEqual(result.kind, "compiler")
        self.assertIn(str(chapter) + ": 6:", result.stderr)
        self.assertIn("Missing", result.stderr)
        self.assertNotIn("f1r3lang-koan-", result.stderr)

    def test_known_limit_multiple_guard_candidates(self):
        # This upstream limitation depends on candidate order. Both the desired
        # answer and a missed match occur. Do not make CI depend on scheduling.
        result = self.program((PROJECT / "tests/fixtures/guard_multiple_candidates.rho").read_text())
        self.assertIn(result.kind, ("pass", "no-output"), result)
        self.assertIn(result.actual, ([], ["7"]))

    def test_known_limit_outer_receive_binding_in_guard(self):
        result = self.program((PROJECT / "tests/fixtures/guard_outer_binding.rho").read_text())
        self.assertEqual(result.kind, "no-output", "Upstream behavior changed; review docs/toolchain.md")
        self.assertEqual(result.actual, [])

    def install_fixture_tools(self):
        cache = self.root / ".toolchain"
        (cache / "bin").mkdir(parents=True)
        for tool in self.tools.values():
            (cache / "bin" / tool.name).symlink_to(tool)
        (cache / "installed.json").write_bytes((PROJECT / ".toolchain/installed.json").read_bytes())
        (self.root / "toolchain.lock.json").write_bytes((PROJECT / "toolchain.lock.json").read_bytes())

    def test_repeated_setup_preserves_edits_without_downloading(self):
        # Exercise the real installed-tools path in an isolated checkout, with
        # deliberate learner edits and downloads forbidden.
        self.install_fixture_tools()
        starters = self.root / "starters"
        starters.mkdir()
        (starters / "answer.rho").write_text('new stdout(`rho:io:stdout`) in { stdout!(__) }\n')
        (starters / "next.rho").write_text('new stdout(`rho:io:stdout`) in { stdout!(__ + 1) }\n')
        learner = self.root / "exercises/answer.rho"
        learner.parent.mkdir()
        learner.write_text('// My own answer\nnew stdout(`rho:io:stdout`) in { stdout!(6 * 7) }\n')
        original = learner.read_bytes()
        with patch.object(setup, "ROOT", self.root), patch("sys.argv", ["setup"]), patch("sys.stdout", new=io.StringIO()), patch("urllib.request.urlopen", side_effect=AssertionError("unexpected network")):
            self.assertEqual(setup.main(), 0)
            self.assertEqual(setup.main(), 0)
        self.assertEqual(learner.read_bytes(), original)
        self.assertEqual((learner.parent / "next.rho").read_bytes(), (starters / "next.rho").read_bytes())

    def test_runner_initializes_practice_and_verifies_independently(self):
        self.install_fixture_tools()
        for name in ("starters", "solutions"):
            shutil.copytree(PROJECT / name, self.root / name)
        course = json.loads((PROJECT / "course.json").read_text())
        # Cover runtime holes and module imports with the actual language tools.
        course["exercises"] = [e for e in course["exercises"] if e["id"] in ("01.01", "11.06")]
        (self.root / "course.json").write_text(json.dumps(course))
        with patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(main(["--once"], self.root), 1)
        self.assertIn("0/2 koans complete", output.getvalue())
        for e in course["exercises"]:
            source = self.root / e["source"]
            starter = self.root / "starters" / Path(e["source"]).relative_to("exercises")
            self.assertEqual(source.read_bytes(), starter.read_bytes())
            source.write_bytes((self.root / e["solution"]).read_bytes())
        # Verification must also use pristine imports, not this learner's library.
        (self.root / "exercises/11_reuse/support/base.module").write_text("broken local import")
        before = {p: p.read_bytes() for p in (self.root / "exercises").rglob("*") if p.is_file()}
        with patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(main(["--verify"], self.root), 0)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        shutil.rmtree(self.root / "exercises")
        with patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(main(["--verify"], self.root), 0)
        self.assertFalse((self.root / "exercises").exists())

    def test_every_chapter_worked_example(self):
        checked = 0
        for path in sorted((PROJECT / "starters").glob("*/README.md")):
            pattern = r'```(rho|module)\n(.*?)\n```\n<!-- koans-(?:output|presentation): (.*?) -->'
            examples = re.findall(pattern, path.read_text(), re.S)
            self.assertEqual(len(examples), 1, f"Missing executable example annotation in {path}")
            for backend, source, expectation in examples:
                with self.subTest(chapter=path.parent.name):
                    result = self.program(source, backend, json.loads(expectation))
                    self.assertTrue(result.passed, result)
                    checked += 1
        self.assertEqual(checked, 12)


if __name__ == "__main__":
    unittest.main()
