"""Readable test reports, with optional terminal colors and native diagnostics."""
from collections import Counter
import os
from pathlib import Path
import textwrap

from .runner import Result, RunSummary, source_frame


def color_enabled(mode: str, stream) -> bool:
    if mode != "auto":
        return mode == "always"
    return stream.isatty() and not os.environ.get("NO_COLOR") and os.environ.get("TERM") != "dumb"


class Style:
    CODES = {"pass": "1;32", "fail": "1;31", "heading": "1;36", "hint": "1;33", "muted": "2"}

    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def __call__(self, text: str, role: str = "heading") -> str:
        return f"\033[{self.CODES[role]}m{text}\033[0m" if self.enabled else text


def output_lines(events: list[str]) -> str:
    # Quotation marks remain language output, rather than JSON-escaped strings.
    return "\n".join(f"  {i:>2} | {event if event else '(blank line)'}"
                     for i, event in enumerate(events, 1))


def differences(expected: list[str], actual: list[str], ordered: bool) -> list[str]:
    if ordered:
        for index in range(max(len(expected), len(actual))):
            want = expected[index] if index < len(expected) else "(no line)"
            got = actual[index] if index < len(actual) else "(no line)"
            if index >= min(len(expected), len(actual)) or want != got:
                return ["First difference at line {}: expected {}, got {}.".format(
                    index + 1, want or "(blank line)", got or "(blank line)")]
        return []
    parts = []
    for label, counts in (("Missing", Counter(expected) - Counter(actual)),
                          ("Unexpected", Counter(actual) - Counter(expected))):
        for value, count in counts.items():
            parts.append(f"{label}: {value or '(blank line)'} ({count} {'occurrence' if count == 1 else 'occurrences'}).")
    return parts


def definition_lines(definitions: dict[str, list[str]]) -> str:
    parts = []
    for section, entries in definitions.items():
        parts.append(f"  {section}:")
        parts.extend(f"    {entry}" for entry in entries)
        if not entries:
            parts.append("    (none)")
    return "\n".join(parts)


def assertion_message(exercise: dict, result: Result, style: Style) -> str:
    parts = []
    if exercise["backend"] == "rho":
        ordered = exercise["expect"]["mode"] == "ordered"
        rule = "in this order" if ordered else "in any order; repeated values count"
        parts.append(style(f"Assert stdout matches ({rule})"))
        parts.extend([style("Expected stdout"), output_lines(exercise["expect"]["events"])])
        suffix = {"runtime": " (before the runtime error)", "timeout": " (before timeout)",
                  "crash": " (before the tool crashed)"}.get(result.kind, "")
        parts.append(style("Actual stdout" + suffix, "pass" if result.passed else "fail"))
        if result.actual is None:
            parts.append("  (not run: compilation failed)" if result.kind == "compiler" else "  (no output available)")
        elif not result.actual:
            parts.append("  (nothing printed)")
        else:
            parts.append(output_lines(result.actual))
        if result.kind in ("assertion", "no-output"):
            parts.extend(style(line, "fail") for line in differences(exercise["expect"]["events"], result.actual, ordered))
    else:
        parts.extend([style("Assert module definitions match (order ignored)"),
                      "Declarations only; this test does not execute a program.",
                      style("Expected definitions"), definition_lines(exercise["expect"]),
                      style("Actual definitions", "pass" if result.passed else "fail")])
        if result.actual is None:
            parts.append("  (not available: module did not compile)")
        else:
            parts.append(definition_lines(result.actual))
            if not result.passed:
                for section, expected in exercise["expect"].items():
                    for line in differences(expected, result.actual[section], False):
                        parts.append(style(f"{section} — {line}", "fail"))
    return "\n".join(parts)


def failure_message(root: Path, exercises: list[dict], index: int, result: Result,
                    all_hints: bool = False, color: bool = False) -> str:
    e, style = exercises[index], Style(color)
    parts = [style(f"FAIL {e['id']}: {e['title']}", "fail"), f"Current test · {e['chapter']}", "",
             style("What this tests"), textwrap.fill(e["context"], width=88), "",
             assertion_message(e, result, style), "", style("Source"),
             source_frame(root, e, result), "",
             style(f"{result.kind.upper()}: {result.detail}".rstrip(), "fail")]
    if result.stderr:
        parts.extend([style("Native diagnostics · stderr"), result.stderr.rstrip("\n")])
    if result.kind in ("compiler", "runtime", "crash", "timeout") and result.stdout:
        # Retain the complete native error stream, separately from observations.
        parts.extend([style("Native diagnostics · stdout (unmodified)"), result.stdout.rstrip("\n")])
    hints = e["hints"] if all_hints else e["hints"][:1]
    parts.extend(["", style("Hints", "hint"), *(f"Hint: {hint}" for hint in hints)])
    parts.append(f"Chapter notes: {Path(e['source']).parent / 'README.md'}")
    if not all_hints and len(e["hints"]) > 1:
        parts.append("Use ./koans --hint for another hint.")
    return "\n".join(parts)


def report_message(root: Path, exercises: list[dict], summary: RunSummary,
                   all_hints: bool = False, color: bool = False) -> str:
    style = Style(color)
    separator = style("─" * 64, "muted")
    parts = ["", separator, style(f"{summary.completed}/{len(exercises)} koans complete"), ""]
    if summary.last_pass is not None:
        e = exercises[summary.completed - 1]
        cached = " · cached; source unchanged" if summary.last_pass_cached else ""
        parts.extend([style(f"PASS {e['id']}: {e['title']}", "pass"),
                      "Last passing test" + cached, e["source"], "",
                      assertion_message(e, summary.last_pass, style), ""])
        if summary.last_pass.stderr:
            parts.extend([style("Native diagnostics · stderr"), summary.last_pass.stderr.rstrip("\n"), ""])
    if summary.failure is None:
        parts.append(style(f"All {len(exercises)} koans pass. Take a moment to explain why each one works.", "pass"))
    else:
        if summary.last_pass is not None:
            parts.extend([separator, ""])
        parts.append(failure_message(root, exercises, summary.completed, summary.failure, all_hints, color))
    return "\n".join(parts)
