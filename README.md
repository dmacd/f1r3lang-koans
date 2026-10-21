# f1r3lang Koans

Learn f1r3lang by fixing small programs, one at a time. There are **72 koans in
12 chapter files**, starting with values and ending with a tiny language assembled
from reusable theories. Some programming experience helps; no Rholang,
process calculus, blockchain, or SQL knowledge is assumed.

Inspired by the edit–run–reflect loop of the
[Clojure Koans](https://github.com/functional-koans/clojure-koans).

## Start

From this directory, on **Ubuntu 22.04 or 24.04, x86_64 with AES instructions**:

```sh
./setup
./koans
```

Setup installs missing Ubuntu build packages through `apt` (using `sudo` when
needed), then downloads and builds the pinned language tools in `.toolchain/`.
Allow several minutes, internet access, roughly 5 GB of free disk, and 4 GB of
RAM for the first build. It uses two build jobs by default; `./setup --jobs 1`
uses less memory. No existing Rust installation is needed or changed.

After setup, the course runs **offline**, with no account, node, server, Docker,
Python packages, or external services. Setup can be rerun safely; it preserves
your exercise files and reuses downloads and builds.

Setup copies the unsolved chapters from `starters/` into `exercises/`, your
local workspace. **`exercises/` is ignored by Git**, so your answers stay local
when you commit and push the project. Existing files are never overwritten;
both setup and the runner create only missing files. Course contributions go
in `starters/`; work through the koans in `exercises/`.

## Work through a koan

1. Open the chapter file shown by `./koans`, beginning with
   `exercises/01_values/koans.rho`. It contains all six
   koans for that chapter, so keep the same editor tab open as you progress.
2. Read its short explanation and replace `__` with code. Keep the surrounding
   program, and aim to understand why your change works.
3. Save. In a terminal, the runner watches your files, checks them in course
   order, and stops at the first failure. It shows the **last passing test**
   and the **current failing test**, including what each expected and produced.
   A passing koan takes you to the next section in the same file. Open a new
   file when you reach the next chapter.
4. Read the linked chapter notes if the syntax is unfamiliar. Use
   `./koans --hint` for a stronger hint. Ctrl-C exits the watcher.

The first failure looks like this (paths and compiler wording may be longer):

```text
0/72 koans complete

FAIL 01.01: A first observation
Current test · Values and observations

What this tests
stdout!(value) prints a value. Make this program print the Boolean value true.
...

Assert stdout matches (in any order; repeated values count)
Expected stdout
   1 | true
Actual stdout
  (not run: compilation failed)

Source
exercises/01_values/koans.rho:11
>  11 |   stdout!(__)

COMPILER: The language tool exited with status 1.
Native diagnostics · stderr
...
Top level free variables are not allowed: __ at SourceSpan { ... }

Hints
Hint: A Boolean literal is written without quotation marks.
Chapter notes: exercises/01_values/README.md
```

After you fix a koan, its green **PASS** section shows the expected and actual
output above the next red **FAIL** section. It stays visible while you work on
the next test. Reused results are marked **cached; source unchanged**.

Every koan has an assertion: runtime tests compare the values printed to
`stdout`, and module tests compare the compiled definitions. The report always
shows the assertion, even when the source fails to compile. Output lines retain
their quotation marks; `(nothing printed)` and `(blank line)` are distinct.
Mismatches identify missing or unexpected values, including duplicates, or the
first differing line when order matters. Output captured before a runtime error
or timeout is shown separately from the original tool diagnostics.

`__` is an intentional hole, not special language syntax. The real compiler
usually rejects it. An assertion failure means your code ran, but the observed
values or resulting definitions differ from the koan's expectations. A program
that compiles but produces no answer still fails.

Keep the `// koan: 01.01` section markers (`-- koan:` in module chapters).
Each section is checked independently: unfinished code later in the file
cannot block the current koan. Error locations refer to lines in the chapter
file you are editing. Run chapter files through `./koans`.

The runner accepts alternative solutions with the right observable behavior;
it does not compare your source with an answer string. Parallel output is
usually compared without imposing an order, but every value and repetition
must match. Acknowledgment exercises explicitly check order.

```sh
./koans --once          # run once; useful in an editor or a script
./koans --once --hint   # run once with all hints for the current failure
./koans --timeout 20    # change the maximum seconds per exercise
./koans --color never   # plain text with the same sections and feedback
./koans --color always  # force colors in an editor terminal that needs it
./koans --help
```

Colors are automatic when output is a terminal. Piped output stays plain;
`NO_COLOR=1 ./koans` also disables automatic colors. Explicit `--color` options
override automatic detection. Green means pass, red means fail, cyan labels
sections, and yellow marks hints; the text labels remain clear without color.

Noninteractive input also selects one-shot mode. Exit statuses are `0` for all
passing, `1` for a failing koan, `2` for setup/configuration errors, and `130`
for Ctrl-C. Progress lives in your edited files; restarting checks them again.
Git does not back up these local answers; copy `exercises/` if you want a backup.
Reference answers are in `solutions/` when you need to compare approaches.

## Course map

Each chapter file contains six koans. Its guide explains the new concepts and
includes a worked example. These links show the shared starters; edit their
copies under `exercises/` after setup.

| Starter chapter | Guide | Learn |
| --- | --- | --- |
| [01 · Values](starters/01_values/koans.rho) | [Notes](starters/01_values/README.md) | Observe values, arithmetic, equality |
| [02 · Expressions](starters/02_expressions/koans.rho) | [Notes](starters/02_expressions/README.md) | Strings, lists, maps, sets, numeric types |
| [03 · Channels](starters/03_channels/koans.rho) | [Notes](starters/03_channels/README.md) | Fresh names, sends, parallel processes |
| [04 · Receives](starters/04_receives/koans.rho) | [Notes](starters/04_receives/README.md) | Bindings, quoting, executable messages, reply channels |
| [05 · Patterns](starters/05_patterns/koans.rho) | [Notes](starters/05_patterns/README.md) | Destructuring, wildcards, types, choices |
| [06 · Contracts](starters/06_contracts/koans.rho) | [Notes](starters/06_contracts/README.md) | Persistent services, recursion, service factories |
| [07 · Coordination](starters/07_coordination/koans.rho) | [Notes](starters/07_coordination/README.md) | Joins, sequential receives, peeking, state, acknowledgments |
| [08 · Guards](starters/08_guards/koans.rho) | [Notes](starters/08_guards/README.md) | Conditional receives and guarded matching |
| [09 · Declarations](starters/09_declarations/koans.module) | [Notes](starters/09_declarations/README.md) | Modules, theories, categories, constructors |
| [10 · Rules](starters/10_rules/koans.module) | [Notes](starters/10_rules/README.md) | Equations and directed rewrites |
| [11 · Reuse](starters/11_reuse/koans.module) | [Notes](starters/11_reuse/README.md) | Theory parameters, exports, replacements, local imports |
| [12 · Composition](starters/12_composition/koans.module) | [Notes](starters/12_composition/README.md) | Sharing, join, meet, difference, a complete small theory |

## Which language tools?

Chapters 01–08 execute `.rho` programs with the upstream `rholang-cli`
interpreter. The tool retains that historical name. Chapters 09–12 compile
`.module` declarations with the upstream `mettail-elab` reference elaborator
and check the resulting categories, constructors, equations, and rewrites.
**The declaration chapters do not execute programs in the languages they
describe.** That integration is not available in these pinned tools.

The newer features currently require two explicit stability exceptions:

- The runtime is the published **`v0.4.46-canary.3999` prerelease**, pinned to
  commit `616e0c5fdbb7a501987f69d55586f8a69824f8a1`, for executable `where` guards.
- The reference elaborator is **unreleased**, pinned to commit
  `9c57a82b9ceaf798b361918369056312a33b051c`. It is built independently from the
  rest of that feature branch.

Nothing follows a moving branch or automatically installs “latest.” Source
archives, Rust components, and protoc have SHA-256 checksums; Cargo dependency
locks are included. [Toolchain decisions](docs/toolchain.md) explain the
exceptions, observed limitations, and the path to stable releases. The
[lock file](toolchain.lock.json) is the exact installation specification.

See the [glossary](docs/glossary.md),
[troubleshooting guide](docs/troubleshooting.md), and
[contributor guide](CONTRIBUTING.md) for more detail.

Original course materials and runner: [MIT license](LICENSE). Upstream language
tools retain their own licenses; see [attribution](NOTICE.md).
