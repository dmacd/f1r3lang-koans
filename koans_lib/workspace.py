"""Create local practice files without replacing a learner's work."""
from pathlib import Path
import shutil

from .runner import CourseError, inside


def initialize_exercises(root: Path) -> None:
    starters = root / "starters"
    if not starters.is_dir():
        raise CourseError("Missing starters/ directory. Restore the course starter files.")
    for source in sorted(starters.rglob("*")):
        if not source.is_file():
            continue
        destination = inside(root / "exercises", str(source.relative_to(starters)))
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation also preserves edits when setup and the runner
        # start together, or an editor creates a file during initialization.
        try:
            target = destination.open("xb")
        except FileExistsError:
            continue
        with target, source.open("rb") as original:
            shutil.copyfileobj(original, target)
