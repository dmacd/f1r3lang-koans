"""Invoke the real language tools and compare observable results."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import tempfile
from dataclasses import dataclass
from collections import Counter


class CourseError(Exception):
    """An installation or course configuration error, rather than a koan failure."""


@dataclass
class Result:
    passed: bool
    kind: str
    actual: object = None
    detail: str = ""
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class CachedPass:
    fingerprint: str
    result: Result


@dataclass(frozen=True)
class RunSummary:
    completed: int
    failure: Result | None
    last_pass: Result | None = None
    last_pass_cached: bool = False


@dataclass(frozen=True)
class Source:
    path: Path
    text: str
    first_line: int
    last_line: int
    sectioned: bool = False


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inside(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name:
        raise CourseError("A course file path is missing.")
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise CourseError(f"Course path escapes the project: {name}")
    return path


def read_source(root: Path, exercise: dict, solution: bool = False) -> Source:
    name = exercise["solution"] if solution else exercise["source"]
    path = inside(root, name)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if "section" not in exercise:
        return Source(path, text, 1, max(1, len(lines)))

    comment = "//" if exercise["backend"] == "rho" else "--"
    marker = re.compile(r"^\s*" + re.escape(comment) + r"\s+koan:\s+(\S+)(?:\s.*)?$")
    sections = []
    seen = set()
    for index, line in enumerate(lines):
        match = marker.match(line)
        if not match:
            continue
        key = match.group(1)
        if key in seen:
            raise CourseError(f"Duplicate koan marker {key!r} in {name}.")
        seen.add(key)
        sections.append((index, key))
    for index, (line, key) in enumerate(sections):
        if key == exercise["section"]:
            start = line + 1
            stop = sections[index + 1][0] if index + 1 < len(sections) else len(lines)
            return Source(path, "".join(lines[start:stop]), start + 1,
                          max(start + 1, stop), sectioned=True)
    raise CourseError(f"Missing '{comment} koan: {exercise['section']}' in {name}. Keep each koan's section marker.")


def stage_source(root: Path, source: Source, work: Path) -> Path:
    if not source.sectioned:
        return source.path
    # Mirror the path to the chapter with symlinked siblings. Local imports,
    # including ../ paths and nested imports, keep their original meaning.
    original, staged = root.resolve(), work / "source"
    for component in source.path.relative_to(original).parts:
        staged.mkdir(parents=True, exist_ok=True)
        for sibling in original.iterdir():
            if sibling.name != component:
                (staged / sibling.name).symlink_to(sibling, target_is_directory=sibling.is_dir())
        original, staged = original / component, staged / component
    # Leading blank lines preserve the chapter's native line/column numbers.
    staged.write_text("\n" * (source.first_line - 1) + source.text, encoding="utf-8")
    return staged


def source_diagnostics(raw: Result, root: Path, source: Source, staged: Path, work: Path) -> Result:
    if not source.sectioned:
        return raw

    def remap(text: str) -> str:
        text = text.replace(str(work / "source") + os.sep, str(root.resolve()) + os.sep)
        # The elaborator prints the entry file's basename, unlike rholang-cli.
        return re.sub(r"(?m)^" + re.escape(staged.name) + r":(?=\s*\d+:)",
                      lambda _: str(source.path) + ":", text)

    raw.stderr = remap(raw.stderr)
    if not raw.passed or RUNTIME_ERRORS in raw.stdout.splitlines():
        raw.stdout = remap(raw.stdout)
    return raw


def load_course(root: Path, *, starters: bool = False) -> list[dict]:
    try:
        data = json.loads((root / "course.json").read_text())
        if not isinstance(data, dict) or data.get("version") != 1:
            raise CourseError("Unsupported course manifest version.")
        exercises = data["exercises"]
        if not isinstance(exercises, list) or not exercises:
            raise CourseError("The course contains no exercises.")
        seen = set()
        for e in exercises:
            if not isinstance(e, dict):
                raise CourseError("Each exercise must be an object.")
            for field in ("id", "title", "chapter", "source", "solution", "context", "hints", "expect"):
                if field not in e:
                    raise CourseError(f"Exercise is missing {field!r}.")
            if any(not isinstance(e[field], str) or not e[field] for field in ("id", "title", "chapter", "source", "solution", "context")):
                raise CourseError("Exercise identifiers, paths, titles, and context must be nonempty strings.")
            if e["id"] in seen:
                raise CourseError(f"Duplicate exercise ID: {e['id']}")
            seen.add(e["id"])
            if e.get("backend") not in ("rho", "module"):
                raise CourseError(f"Unknown backend for {e['id']}.")
            if not e["hints"] or not isinstance(e["hints"], list) or not all(isinstance(hint, str) for hint in e["hints"]):
                raise CourseError(f"Missing hints for {e['id']}.")
            if not isinstance(e["expect"], dict):
                raise CourseError(f"Invalid expectations for {e['id']}.")
            if e["backend"] == "rho":
                if e["expect"].get("mode") not in ("ordered", "unordered") or not isinstance(e["expect"].get("events"), list) or not e["expect"]["events"] or not all(isinstance(event, str) for event in e["expect"]["events"]):
                    raise CourseError(f"Missing output expectations for {e['id']}.")
            elif set(e["expect"]) != {"Types", "Exports", "Terms", "Equations", "Rewrites"}:
                raise CourseError(f"Incomplete presentation expectations for {e['id']}.")
            elif not all(isinstance(entries, list) and all(isinstance(entry, str) for entry in entries) for entries in e["expect"].values()):
                raise CourseError(f"Invalid presentation expectations for {e['id']}.")
            if not isinstance(e.get("inputs", []), list):
                raise CourseError(f"Invalid support files for {e['id']}.")
            if not isinstance(e.get("focus", 1), int) or e.get("focus", 1) < 1:
                raise CourseError(f"Invalid focus line for {e['id']}.")
            if "section" in e and (not isinstance(e["section"], str) or not e["section"] or any(c.isspace() for c in e["section"])):
                raise CourseError(f"Invalid section marker for {e['id']}.")
            if starters:
                # Verification reads the published course even if practice
                # files have been solved, changed, or never initialized.
                def starter_path(name: str) -> str:
                    return str(Path("starters") / Path(name).relative_to("exercises"))
                e["source"] = starter_path(e["source"])
                if "inputs" in e:
                    e["inputs"] = [starter_path(name) for name in e["inputs"]]
            for name in (e["source"], e["solution"], *e.get("inputs", [])):
                if not inside(root, name).is_file():
                    raise CourseError(f"Missing course file: {name}")
        return exercises
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CourseError(f"Cannot read course.json: {exc}") from exc


def installed_tools(root: Path) -> dict[str, Path]:
    try:
        state = json.loads((root / ".toolchain/installed.json").read_text())
        if state["lock_sha256"] != digest(root / "toolchain.lock.json"):
            raise ValueError("the toolchain lock changed")
        tools = {}
        for backend, name in (("rho", "rholang-cli"), ("module", "mettail-elab")):
            path = root / ".toolchain/bin" / name
            if not os.access(path, os.X_OK) or digest(path) != state["binaries"][name]:
                raise ValueError(f"{name} is missing or changed")
            tools[backend] = path
        return tools
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CourseError(f"The language tools need setup ({exc}). Run ./setup.") from exc


def run_process(args: list[str], cwd: Path, timeout: float) -> Result:
    # No shell or inherited stdin: an exercise cannot consume the watcher's input.
    env = os.environ.copy()
    env.update(NO_COLOR="1", RUST_BACKTRACE="0", RUST_MIN_STACK="8388608")
    try:
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(args, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=errors, start_new_session=True)
            timed_out = False
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            except BaseException:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise
            output.seek(0)
            errors.seek(0)
            stdout = output.read().decode("utf-8", errors="replace")
            stderr = errors.read().decode("utf-8", errors="replace")
        if timed_out:
            return Result(False, "timeout", detail=f"Evaluation exceeded {timeout:g} seconds. Check for unbounded recursion or repeated communication.", stdout=stdout, stderr=stderr)
        if process.returncode:
            kind = "crash" if process.returncode < 0 or process.returncode == 101 else "compiler"
            return Result(False, kind, detail=f"The language tool exited with status {process.returncode}.", stdout=stdout, stderr=stderr)
        return Result(True, "completed", stdout=stdout, stderr=stderr)
    except OSError as exc:
        raise CourseError(f"Cannot start the language tool: {exc}. Run ./setup.") from exc


COST = re.compile(r"^Estimated deploy cost: Cost \{.*\}$")
WAIT = "This is taking a long time. Feel free to ^C and quit."
RUNTIME_ERRORS = "Errors received during evaluation:"


def stdout_events(text: str) -> list[str]:
    """Separate printed observations from the pinned CLI's own diagnostics."""
    events = []
    for line in text.splitlines():
        if line == RUNTIME_ERRORS:
            break
        if line != WAIT and not COST.fullmatch(line):
            events.append(line)
    return events


def rho_result(raw: Result, expect: dict) -> Result:
    if not raw.passed:
        if raw.kind in ("timeout", "crash"):
            raw.actual = stdout_events(raw.stdout)
        return raw
    # This CLI returns zero even when EvalResult.errors is nonempty. Never use
    # exit status alone, and never hide its diagnostics behind an output mismatch.
    if RUNTIME_ERRORS in raw.stdout.splitlines():
        raw.passed, raw.kind = False, "runtime"
        raw.actual = stdout_events(raw.stdout)
        raw.detail = "The interpreter reported a runtime error."
        return raw
    lines = raw.stdout.splitlines()
    costs = [i for i, line in enumerate(lines) if COST.fullmatch(line)]
    if len(costs) != 1:
        raise CourseError("Unrecognized interpreter output: expected one evaluation-cost footer. The backend adapter needs checking.")
    events = stdout_events(raw.stdout)
    # Blank lines are data too. Authored output uses one printed value per event.
    expected = expect["events"]
    passed = (events == expected if expect["mode"] == "ordered" else Counter(events) == Counter(expected))
    return Result(passed, "pass" if passed else ("no-output" if not events else "assertion"),
                  events, "No expected result was produced; a receive may have no matching message." if not events else "", raw.stdout, raw.stderr)


def presentation(text: str) -> dict[str, list[str]]:
    """Read only the pinned elaborator's printed presentation, not source syntax."""
    lines = text.splitlines()
    if not lines or lines[0] != "Presentation":
        raise CourseError("Unrecognized elaborator output: missing Presentation header.")
    result = {}
    index = 1
    for section in ("Types", "Exports"):
        if index >= len(lines):
            raise CourseError("Incomplete elaborator output.")
        match = re.fullmatch(r"  " + section + r" \{(.*) \}", lines[index])
        if not match:
            raise CourseError(f"Unrecognized elaborator {section} section.")
        result[section] = [x.strip() for x in match.group(1).split(";") if x.strip()]
        index += 1
    for section in ("Terms", "Equations", "Rewrites"):
        if index >= len(lines) or lines[index] != f"  {section} {{":
            raise CourseError(f"Unrecognized elaborator {section} section.")
        index += 1
        entries = []
        while index < len(lines) and lines[index] != "  }":
            if not lines[index].startswith("    "):
                raise CourseError(f"Malformed elaborator {section} entry.")
            entries.append(lines[index].strip())
            index += 1
        if index >= len(lines):
            raise CourseError("Incomplete elaborator output.")
        result[section] = entries
        index += 1
    if index != len(lines):
        raise CourseError("Unexpected text after the elaborator presentation.")
    return result


def evaluate(root: Path, exercise: dict, tools: dict[str, Path], timeout: float = 10,
             solution: bool = False) -> Result:
    source = read_source(root, exercise, solution)
    with tempfile.TemporaryDirectory(prefix="f1r3lang-koan-") as directory:
        work = Path(directory)
        staged = stage_source(root, source, work)
        if exercise["backend"] == "rho":
            # The CLI distinguishes a new store by whether its path exists.
            # Pass a fresh child, not TemporaryDirectory's already-created root.
            raw = run_process([str(tools["rho"]), "--quiet", "--data-dir", str(work / "data"), str(staged)], root, timeout)
            raw = source_diagnostics(raw, root, source, staged, work)
            return rho_result(raw, exercise["expect"])
        raw = run_process([str(tools["module"]), str(staged)], root, timeout)
        raw = source_diagnostics(raw, root, source, staged, work)
        if not raw.passed:
            return raw
        actual = presentation(raw.stdout)
        passed = all(Counter(actual[k]) == Counter(exercise["expect"][k]) for k in actual)
        return Result(passed, "pass" if passed else "assertion", actual,
                      "The module elaborates, but its resulting definitions do not yet match the exercise." if not passed else "", raw.stdout, raw.stderr)


def fingerprint(root: Path, exercise: dict, tools: dict[str, Path]) -> str:
    h = hashlib.sha256(json.dumps(exercise, sort_keys=True).encode())
    source = read_source(root, exercise)
    h.update(source.text.encode("utf-8"))
    # Include all .module files in the lesson's directory tree: local imports
    # added by a learner invalidate the result even before metadata is updated.
    files = {inside(root, name) for name in exercise.get("inputs", [])}
    if exercise["backend"] == "module":
        files.update((root / "exercises").rglob("*.module"))
    # Editing another koan in this chapter does not invalidate a passed section.
    files = {path for path in files if path.resolve() != source.path}
    for path in sorted(files):
        h.update(str(path).encode())
        h.update(path.read_bytes())
    tool = tools[exercise["backend"]]
    h.update(str(tool).encode())
    stat = tool.stat()
    h.update(str((stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)).encode())
    h.update((root / "toolchain.lock.json").read_bytes())
    h.update((root / ".toolchain/installed.json").read_bytes())
    return h.hexdigest()


def first_failure(root: Path, exercises: list[dict], tools: dict[str, Path], timeout: float,
                  cache: dict[str, CachedPass] | None = None) -> RunSummary:
    previous = None
    previous_cached = False
    for index, exercise in enumerate(exercises):
        key = fingerprint(root, exercise, tools) if cache is not None else None
        cached = cache.get(exercise["id"]) if cache is not None else None
        if cached is not None and cached.fingerprint == key:
            previous, previous_cached = cached.result, True
            continue
        result = evaluate(root, exercise, tools, timeout)
        if not result.passed:
            if cache is not None:
                cache.pop(exercise["id"], None)
            return RunSummary(index, result, previous, previous_cached)
        if cache is not None:
            cache[exercise["id"]] = CachedPass(key, result)
        previous, previous_cached = result, False
    return RunSummary(len(exercises), None, previous, previous_cached)


def source_frame(root: Path, exercise: dict, result: Result) -> str:
    source = read_source(root, exercise)
    lines = source.text.splitlines()
    # The elaborator emits line:column; the interpreter sometimes names line N.
    diag = result.stderr + "\n" + result.stdout
    match = re.search(r"(?:^|\s|:)(\d+):(\d+)(?=:|\s|$)", diag)
    line = int(match.group(1)) if match else None
    if line is None:
        match = re.search(r"\bline\s*:?\s+(\d+)", diag, re.I)
        line = int(match.group(1)) if match else None
    if line is None or not source.first_line <= line <= source.last_line:
        relative = next((i for i, text in enumerate(lines, 1) if "__" in text and not text.lstrip().startswith(("//", "--"))), exercise.get("focus", 1))
        line = source.first_line - 1 + max(1, min(relative, len(lines)))
    start = max(source.first_line, line - 2)
    stop = min(source.first_line + len(lines) - 1, line + 2)
    excerpt = "\n".join(f"{'>' if i == line else ' '} {i:3} | {lines[i - source.first_line]}" for i in range(start, stop + 1))
    return f"{exercise['source']}:{line}\n{excerpt}"
