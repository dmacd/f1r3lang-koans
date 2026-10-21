"""The learner's edit/save/observe loop."""
from __future__ import annotations

import argparse
import hashlib
import math
from pathlib import Path
import sys
import time

from .runner import CourseError, evaluate, first_failure, installed_tools, load_course
from .reporting import Style, color_enabled, report_message
from .workspace import initialize_exercises


ROOT = Path(__file__).resolve().parent.parent


def watch_signature(root: Path) -> str:
    h = hashlib.sha256()
    paths = [root / "course.json", root / "toolchain.lock.json", root / ".toolchain/installed.json"]
    paths.extend((root / "exercises").rglob("*.rho"))
    paths.extend((root / "exercises").rglob("*.module"))
    paths.extend((root / ".toolchain/bin").glob("*"))
    for path in sorted(paths):
        h.update(str(path).encode())
        try:
            # Read small source files so editors with coarse timestamps still work.
            if path.parent == root / ".toolchain/bin":
                h.update(str(path.stat()).encode())
            else:
                h.update(path.read_bytes())
        except FileNotFoundError:
            h.update(b"missing")
    return h.hexdigest()


def verify(root: Path, tools: dict, timeout: float, color: bool = False) -> int:
    style = Style(color)
    exercises = load_course(root, starters=True)
    failures = 0
    for e in exercises:
        answer = evaluate(root, e, tools, timeout, solution=True)
        starter = evaluate(root, e, tools, timeout)
        if not answer.passed or starter.passed:
            failures += 1
            print(style(f"FAIL {e['id']}: solution={answer.kind}, starter={starter.kind}", "fail"))
            if not answer.passed:
                print(answer.detail, answer.actual, answer.stdout, answer.stderr)
        else:
            print(style(f"PASS {e['id']} (solution passes; starter fails)", "pass"), flush=True)
    print(style(f"\nVerified {len(exercises)} koans; {failures} failures.", "fail" if failures else "pass"))
    return 1 if failures else 0


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description="Learn f1r3lang by making one koan pass at a time.")
    parser.add_argument("--once", action="store_true", help="run once and exit (also used when stdin is not a terminal)")
    parser.add_argument("--hint", action="store_true", help="show all hints for the first failing koan")
    parser.add_argument("--verify", action="store_true", help="maintainer check: reference solutions pass and untouched starters fail")
    parser.add_argument("--color", choices=("auto", "always", "never"), default="auto",
                        help="terminal colors (default: auto; honors NO_COLOR)")
    parser.add_argument("--timeout", type=float, default=10, metavar="SECONDS", help="maximum time per exercise (default: 10)")
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")
    color = color_enabled(args.color, sys.stdout)
    style = Style(color)
    try:
        tools = installed_tools(root)
        if args.verify:
            return verify(root, tools, args.timeout, color)
        initialize_exercises(root)
        once = args.once or not sys.stdin.isatty()
        cache = None if once else {}
        print(style("f1r3lang Koans · edit the indicated file and save."), flush=True)
        while True:
            before = watch_signature(root)
            try:
                tools = installed_tools(root)
                exercises = load_course(root)
                summary = first_failure(root, exercises, tools, args.timeout, cache)
                print(report_message(root, exercises, summary, args.hint, color), flush=True)
                status = 0 if summary.failure is None else 1
            except (CourseError, OSError) as exc:
                # Editors may briefly remove a file during an atomic save. Keep
                # watching so a corrected source/configuration can recover.
                print(f"\nSetup / runner error: {exc}", file=sys.stderr, flush=True)
                status = 2
            if once:
                return status
            print("\nWatching for saves. Ctrl-C exits.", flush=True)
            while watch_signature(root) == before:
                time.sleep(0.25)
            # Allow a save that writes in several chunks to finish.
            time.sleep(0.15)
    except KeyboardInterrupt:
        print("\nStopped. Your edits are saved in the exercise files.")
        return 130
    except (CourseError, OSError) as exc:
        print(f"\nSetup / runner error: {exc}", file=sys.stderr)
        return 2
