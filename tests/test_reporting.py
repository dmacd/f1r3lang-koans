import io
import os
import re
from unittest.mock import Mock, patch

from koans_lib.cli import main
from koans_lib.reporting import color_enabled, failure_message, report_message
from koans_lib.runner import Result, RunSummary
from test_runner import COST, Fixture


class ReportingTests(Fixture):
    def message(self, result):
        return failure_message(self.root, self.exercises, 0, result)

    def test_expected_output_is_visible_even_when_compilation_fails(self):
        diagnostic = "Unknown variable at SourcePos { line: 1, col: 1 }\nnative detail\n"
        message = self.message(Result(False, "compiler", stderr=diagnostic))
        self.assertIn("FAIL 1: Example", message)
        self.assertIn("Expected stdout\n   1 | 7", message)
        self.assertIn("Actual stdout\n  (not run: compilation failed)", message)
        self.assertIn(diagnostic.rstrip(), message)

    def test_output_preserves_string_quotes_and_distinguishes_blank_lines(self):
        message = self.message(Result(False, "assertion", ['"7"', ""]))
        self.assertIn('1 | "7"', message)
        self.assertIn('2 | (blank line)', message)
        self.assertIn('Missing: 7 (1 occurrence)', message)
        self.assertIn('Unexpected: "7" (1 occurrence)', message)
        self.assertNotIn("nothing printed", message)
        silent = self.message(Result(False, "no-output", []))
        self.assertIn("Actual stdout\n  (nothing printed)", silent)
        self.assertNotIn("(blank line)", silent)

    def test_unordered_mismatch_counts_duplicates_without_inventing_order(self):
        self.exercises[0]["expect"]["events"] = ["1", "2", "2", "2"]
        message = self.message(Result(False, "assertion", ["2", "1", "3"]))
        self.assertIn("in any order; repeated values count", message)
        self.assertIn("Missing: 2 (2 occurrences)", message)
        self.assertIn("Unexpected: 3 (1 occurrence)", message)
        self.assertNotIn("Missing: 1", message)

    def test_ordered_mismatch_points_to_the_first_different_line(self):
        self.exercises[0]["expect"] = {"mode": "ordered", "events": ["1", "2"]}
        message = self.message(Result(False, "assertion", ["2", "1"]))
        self.assertIn("in this order", message)
        self.assertIn("First difference at line 1: expected 1, got 2.", message)
        self.exercises[0]["expect"]["events"] = ["(no line)"]
        missing = self.message(Result(False, "no-output", []))
        self.assertIn("First difference at line 1", missing)

    def test_partial_output_and_native_error_streams_are_separate(self):
        raw = "7\n" + COST + "Errors received during evaluation:\nDivision by zero\n"
        message = self.message(Result(False, "runtime", ["7"], stdout=raw))
        self.assertIn("Actual stdout (before the runtime error)\n   1 | 7", message)
        self.assertIn("Native diagnostics · stdout (unmodified)\n" + raw.rstrip(), message)
        timeout = self.message(Result(False, "timeout", ["7"], stdout="7\n"))
        self.assertIn("Actual stdout (before timeout)\n   1 | 7", timeout)

    def test_module_tests_show_expected_and_actual_definitions(self):
        expected = {key: [] for key in ("Types", "Exports", "Terms", "Equations", "Rewrites")}
        expected["Types"] = ["Value"]
        self.exercises[0].update(backend="module", expect=expected)
        actual = {**expected, "Types": ["Other"]}
        message = self.message(Result(False, "assertion", actual))
        self.assertIn("Declarations only", message)
        self.assertIn("Expected definitions\n  Types:\n    Value", message)
        self.assertIn("Actual definitions\n  Types:\n    Other", message)
        self.assertIn("Types — Missing: Value", message)
        self.assertIn("Types — Unexpected: Other", message)
        self.assertIn("Rewrites:\n    (none)", message)
        self.assertNotIn("Actual stdout", message)
        failed = self.message(Result(False, "compiler", stderr="native module error"))
        self.assertIn("Expected definitions", failed)
        self.assertIn("not available: module did not compile", failed)

    def test_last_success_remains_visible_including_when_every_koan_passes(self):
        passed = Result(True, "pass", ["7"], stdout="7\n" + COST)
        failed = Result(False, "compiler", stderr="native error")
        summary = RunSummary(1, failed, passed, True)
        message = report_message(self.root, self.exercises, summary)
        self.assertLess(message.index("PASS 1:"), message.index("FAIL 2:"))
        self.assertIn("Last passing test · cached; source unchanged", message)
        self.assertIn("Actual stdout\n   1 | 7", message)
        self.assertNotIn(COST.strip(), message)
        complete = report_message(self.root, self.exercises, RunSummary(3, None, passed))
        self.assertIn("PASS 3:", complete)
        self.assertIn("Actual stdout\n   1 | 7", complete)
        self.assertIn("All 3 koans pass", complete)
        self.assertNotIn("FAIL", complete)

    def test_color_selection_respects_terminal_environment_and_explicit_flags(self):
        tty = Mock()
        tty.isatty.return_value = True
        with patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=True):
            self.assertTrue(color_enabled("auto", tty))
            self.assertFalse(color_enabled("auto", io.StringIO()))
            os.environ["NO_COLOR"] = "1"
            self.assertFalse(color_enabled("auto", tty))
            self.assertTrue(color_enabled("always", io.StringIO()))
            self.assertFalse(color_enabled("never", tty))
            del os.environ["NO_COLOR"]
            os.environ["TERM"] = "dumb"
            self.assertFalse(color_enabled("auto", tty))

    def test_cli_color_changes_presentation_without_changing_feedback_or_status(self):
        summary = RunSummary(0, Result(False, "compiler", stderr="native error"))
        outputs = {}
        for mode in ("auto", "always", "never"):
            with patch("koans_lib.cli.first_failure", return_value=summary), patch("sys.stdout", new_callable=io.StringIO) as output:
                self.assertEqual(main(["--once", "--color", mode], self.root), 1)
                outputs[mode] = output.getvalue()
        self.assertIn("\033[", outputs["always"])
        self.assertNotIn("\033[", outputs["auto"])
        self.assertEqual(outputs["auto"], outputs["never"])
        self.assertEqual(re.sub(r"\x1b\[[0-9;]*m", "", outputs["always"]), outputs["never"])
