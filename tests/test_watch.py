import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import sys
import time

from test_runner import COST, Fixture


PROJECT = Path(__file__).resolve().parent.parent


class WatchTests(Fixture):
    def start_watcher(self):
        # A deterministic executable reports compile failures and records calls.
        # Native tool behavior is checked separately in test_native.py.
        log = self.root / ".toolchain/calls.log"
        self.tools["rho"].write_text('''#!/usr/bin/env python3
import sys
from pathlib import Path
source = Path(sys.argv[-1])
code = source.read_text()
label = next((line.split(':', 1)[1].strip() for line in code.splitlines() if line.startswith('// test-id:')), source.name)
with Path(''' + repr(str(log)) + ''').open('a') as log:
    log.write(label + '\\n')
if '__' in code:
    print('native compiler: unfilled hole', file=sys.stderr)
    raise SystemExit(1)
print('7')
print(''' + repr(COST) + ''', end='')
''')
        self.write_receipt()
        self.master, slave = pty.openpty()
        self.addCleanup(os.close, self.master)
        self.process = subprocess.Popen([
            sys.executable, "-u", "-c",
            "from pathlib import Path; from koans_lib.cli import main; import sys; sys.exit(main([], root=Path(sys.argv[1])))",
            str(self.root),
        ], stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=PROJECT, start_new_session=True)
        os.close(slave)
        self.pending = b""
        self.addCleanup(self.stop_watcher)
        return log

    def stop_watcher(self):
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process.stdout.close()

    def wait_for(self, text):
        needle = text.encode()
        deadline = time.monotonic() + 8
        while needle not in self.pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self.fail(f"Watcher did not show {text!r}; output: {self.pending.decode()}")
            if select.select([self.process.stdout], [], [], remaining)[0]:
                block = os.read(self.process.stdout.fileno(), 65536)
                if not block:
                    self.fail(f"Watcher exited early: {self.pending.decode()}")
                self.pending += block
        offset = self.pending.index(needle) + len(needle)
        self.pending = self.pending[offset:]

    def test_save_advance_cache_import_edit_and_recovery(self):
        support = self.root / "exercises/support.module"
        support.write_text("initial")
        self.exercises[0]["inputs"] = ["exercises/support.module"]
        self.write_course()
        log = self.start_watcher()
        self.wait_for("FAIL 1:")
        self.wait_for("Watching for saves")
        (self.root / self.exercises[0]["source"]).write_text("solved")
        self.wait_for("PASS 1:")
        self.wait_for("Actual stdout\n   1 | 7")
        self.wait_for("FAIL 2:")
        self.wait_for("Actual stdout\n  (not run: compilation failed)")
        self.wait_for("Watching for saves")
        (self.root / self.exercises[1]["source"]).write_text("still __")
        self.wait_for("PASS 1:")
        self.wait_for("Last passing test · cached; source unchanged")
        self.wait_for("Actual stdout\n   1 | 7")
        self.wait_for("FAIL 2:")
        self.wait_for("Watching for saves")
        self.assertEqual(log.read_text().splitlines().count("1.rho"), 2)
        support.write_text("changed")
        self.wait_for("FAIL 2:")
        self.wait_for("Watching for saves")
        self.assertEqual(log.read_text().splitlines().count("1.rho"), 3)
        (self.root / self.exercises[0]["source"]).write_text("broken __")
        self.wait_for("FAIL 1:")
        self.wait_for("Watching for saves")
        source = self.root / self.exercises[0]["source"]
        source.unlink()
        self.wait_for("Missing course file")
        self.wait_for("Watching for saves")
        source.write_text("solved again")
        self.wait_for("FAIL 2:")
        self.wait_for("Watching for saves")
        for e in self.exercises:
            (self.root / e["source"]).write_text("solved")
        self.wait_for("All 3 koans pass")
        self.wait_for("Watching for saves")
        self.process.send_signal(signal.SIGINT)
        self.assertEqual(self.process.wait(timeout=3), 130)

    def test_progress_and_regression_with_one_open_chapter(self):
        chapter = self.root / "exercises/koans.rho"
        answers = ["__", "__", "__"]

        def save():
            chapter.write_text("".join(f'// koan: {n}\n// test-id: {n}\n{code}\n'
                                       for n, code in enumerate(answers, 1)))

        save()
        for e in self.exercises:
            e.update(source="exercises/koans.rho", section=e["id"])
        self.write_course()
        log = self.start_watcher()
        self.wait_for("FAIL 1:")
        self.wait_for("Watching for saves")
        answers[0] = "solved"
        save()
        self.wait_for("PASS 1:")
        self.wait_for("Actual stdout\n   1 | 7")
        self.wait_for("FAIL 2:")
        self.wait_for("Watching for saves")
        answers[1] = "solved\nwith an extra line"
        save()
        self.wait_for("PASS 2:")
        self.wait_for("Actual stdout\n   1 | 7")
        self.wait_for("FAIL 3:")
        self.wait_for("Watching for saves")
        self.assertEqual(log.read_text().splitlines().count("1"), 2)
        self.assertEqual(log.read_text().splitlines().count("2"), 2)
        answers[2] = "solved"
        save()
        self.wait_for("PASS 3:")
        self.wait_for("Actual stdout\n   1 | 7")
        self.wait_for("All 3 koans pass")
        self.wait_for("Watching for saves")
        answers[0] = "broken __"
        save()
        self.wait_for("FAIL 1:")
        self.wait_for("Watching for saves")
        self.process.send_signal(signal.SIGINT)
        self.assertEqual(self.process.wait(timeout=3), 130)
