from pathlib import Path
import shutil
import subprocess

from koans_lib.runner import CourseError
from koans_lib.workspace import initialize_exercises
from test_runner import Fixture


PROJECT = Path(__file__).resolve().parent.parent


class WorkspaceTests(Fixture):
    def test_initialization_preserves_answers_and_only_adds_missing_files(self):
        shutil.rmtree(self.root / "exercises")
        starters = self.root / "starters"
        (starters / "README.md").write_text("Chapter notes")
        support = starters / "support/base.module"
        support.parent.mkdir()
        support.write_text("Original library")
        initialize_exercises(self.root)
        for path in starters.rglob("*"):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (self.root / "exercises" / path.relative_to(starters)).read_bytes())

        answer = self.root / "exercises/1.rho"
        answer.write_text("My partial answer")
        library = self.root / "exercises/support/base.module"
        library.write_text("My edited library")
        (starters / "1.rho").write_text("An updated starter")
        (starters / "new.rho").write_text("A new chapter")
        for _ in range(2):
            initialize_exercises(self.root)
            self.assertEqual(answer.read_text(), "My partial answer")
            self.assertEqual(library.read_text(), "My edited library")
            self.assertEqual(support.read_text(), "Original library")
            self.assertEqual((self.root / "exercises/new.rho").read_text(), "A new chapter")
        (self.root / "exercises/2.rho").unlink()
        initialize_exercises(self.root)
        self.assertEqual((self.root / "exercises/2.rho").read_bytes(), (starters / "2.rho").read_bytes())
        self.assertEqual(answer.read_text(), "My partial answer")

    def test_missing_starters_reports_a_course_error(self):
        shutil.rmtree(self.root / "starters")
        with self.assertRaisesRegex(CourseError, "Missing starters/"):
            initialize_exercises(self.root)

    def test_git_add_includes_starters_and_excludes_local_answers(self):
        # Exercise the project's actual ignore rules in a disposable repository.
        (self.root / ".gitignore").write_bytes((PROJECT / ".gitignore").read_bytes())
        (self.root / "exercises/1.rho").write_text("My private partial answer")
        (self.root / "exercises/editor-backup.rho~").write_text("My answer backup")
        subprocess.run(["git", "init", "--quiet", str(self.root)], check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=self.root, check=True, capture_output=True)
        files = subprocess.check_output(["git", "ls-files"], cwd=self.root, text=True).splitlines()
        self.assertIn("starters/1.rho", files)
        self.assertIn("solutions/1.rho", files)
        self.assertFalse(any(name.startswith("exercises/") for name in files), files)
