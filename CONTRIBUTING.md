# Maintaining the course

The runner uses only Python 3.10+ standard-library modules. The supported
setup targets Ubuntu 22.04 and 24.04 on x86_64. Keep the learner's workflow
to `./setup` and `./koans`.

After setup:

```sh
python3 -m unittest discover -s tests -v
./koans --verify
```

`--verify` executes each reference solution and each starter independently.
Every solution must pass its expectations; every starter must fail. It reads
the shared `starters/` and `solutions/` trees, including their own imports.
Your local answers in `exercises/` do not affect verification; that directory
can even be absent. Verification never creates or changes learner files.

Commit course material in `starters/`, keeping every exercise unsolved there.
`exercises/` is an ignored workspace for your own practice. Setup and the runner
copy only missing files from `starters/`, including guides and import libraries,
and preserve existing files. To try a changed starter locally, copy just that
file or section into `exercises/` after saving any answers you want to retain.

The unit and integration suite covers first-failure behavior, output
comparison, real diagnostics, runtime failures with zero exit status,
timeouts and child cleanup, isolated stores, changed-file caching, imports,
watcher recovery, visible output assertions, color selection, checksum failures,
and partial-download recovery. It also
executes each chapter's worked example. Native tests require `./setup`;
missing tools are an error rather than silently skipped tests.

## Files and expectations

Each entry in `course.json` declares its ID, ordered position, chapter source
path under `exercises/`, matching solution path, `section` ID, backend, teaching context, two
hints, focus line, and expected observations. Several entries share one chapter
file. The `section` selects its `// koan: ID` marker (`-- koan: ID` for modules)
through the next marker or the end of the file. Keep marker IDs unique in each
file. `focus` is a fallback line number relative to the section body. The shared
starter has the same relative path under `starters/`; verification maps `source`
and `inputs` to that tree. No second manifest or list of starter paths is needed.

Sections contain complete programs and run independently, so later holes or
syntax errors cannot prevent earlier koans from passing. The runner pads the
extracted section with blank lines and maps temporary paths back to the
original chapter. Native line and column numbers therefore remain accurate.
Local imports retain their paths through a temporary directory layout; source
files are never overwritten during evaluation. Passed sections are cached by
their own contents, so editing the next section keeps earlier results cached.
The cache retains each passing result as well as its fingerprint. Reports show
the last passing result alongside the current failure, including when that
pass is reused from the cache. An earlier failure must not display a stale
later pass.

`koans_lib/reporting.py` formats the assertions, observations, source context,
hints, and native diagnostics into separate terminal sections. Keep diagnostics
intact, and distinguish a compile failure from an empty observation or output
captured before an evaluation error. Colors are optional; plain output carries
the same information. Module tests report definitions, not program output.

An entry can also list `inputs` for shared support files. Author those files
under `starters/` and list their matching `exercises/` paths in the manifest.
All `.module` files under `exercises/` participate in watch invalidation.
Mirror solution imports under `solutions/` so verification is independent of
both learner edits and starter holes.

For runtime lessons, `expect.events` contains exactly the printed values,
including string quotes. `mode` is `unordered` unless the program establishes
ordering by communication. A multiset retains duplicates. Never turn an
empty observation into success merely because the compiler accepted the
program.

For modules, `expect` contains `Types`, `Exports`, `Terms`, `Equations`, and
`Rewrites`, each a list of the pinned elaborator's rendered definitions.
Include all definitions, not just a matching substring. Review each expected
presentation against the lesson's intended meaning; do not automatically
replace assertions with whatever a new compiler happens to print.

## Writing a koan

- Introduce one main idea in a marked section of the chapter file, with a
  complete program and a small `__` hole. Include a comment explaining the
  requested behavior in plain language.
- Explain every new symbol in the chapter guide before relying on it. Work
  from values and messages; do not assume background in process calculi.
- Give one directional hint and one more specific hint. Preserve native
  diagnostics so learners encounter the real language tool.
- Supply a reference solution, then prove both that it passes and that the
  untouched starter fails using the actual backend. Also try a plausible
  incorrect solution with a different observable result.
- Keep parallel examples deterministic in what they observe. Do not teach
  source order as a scheduling guarantee.
- State whether a lesson executes a process or checks declarations. Do not
  imply that an elaborated theory has been executed by a generated evaluator.

Each chapter guide includes a fenced `rho` or `module` worked example followed
by a hidden `koans-output` or `koans-presentation` JSON comment. The native
test suite runs that example with those expectations. Keep one worked example
per chapter or update the corresponding completeness check deliberately.

## CI and releases

The GitHub Actions workflow builds the pinned tools on Ubuntu 22.04 and
24.04, runs the regression suite, verifies the course with networking disabled,
checks setup idempotence, checks that local answers are ignored by Git, and
checks that no shared course files were changed. Only
download and Cargo caches are restored; installed executables are built in
each job. CI is configured in this repository; publishing the repository to
GitHub is a separate step.

Toolchain changes follow [the upgrade policy](docs/toolchain.md#moving-to-stable-releases).
The two `test_known_limit_*` tests are explicit probes of upstream limitations.
The candidate-order probe permits either observed outcome because its failure
depends on scheduling. Review it through repeated trials when upgrading. If
the limitations improve, update the tests and notes; do not change a language
lesson to teach the limitation as intended behavior.
