# When a koan gets stuck

## The compiler mentions `__` or a free variable

Replace the hole with code, then save. An unquoted word is a variable, so use
double quotes if you mean a string. Native error text is kept intact beneath
the runner's explanation. `SourcePos { line: N, col: M }` identifies a location
in the chapter file; the runner also shows nearby source lines. Error positions
stay accurate as you add or remove lines in earlier sections.

## The runner reports a missing or duplicate koan marker

Keep each `// koan: ID` line (`-- koan: ID` for modules) once in its chapter
file. These comments divide the independent exercises. Restore a deleted
marker or remove an accidentally duplicated one, then save; the watcher
will resume. Edit the code inside a section while retaining its marker.

## It compiles but nothing prints

Check that the sender and receiver use the same channel, that the number of
arguments agrees, that the pattern matches, and that any guard is true. A tuple
is one argument: `c!((1, 2))` differs from `c!(1, 2)`. A pending receive can be
a valid, finished evaluation with no observation; the runner calls this
`NO-OUTPUT` rather than silently passing it.

## The output is almost right

Quotes matter: `7` and `"7"` are different values. Extra or repeated prints
count as observations. Parallel composition does not guarantee print order;
the runner states whether a particular expectation is ordered or unordered.
For `.module` failures, compare the indicated presentation section. A theory
can elaborate successfully and still declare the wrong language.

Read **Expected stdout** and **Actual stdout** in the current test's report.
Missing and unexpected values are counted; ordered tests identify the first
different line. `(nothing printed)` means an empty observation, while
`(blank line)` is an actual output line. **PASS** shows the previous test's
result, and **FAIL** marks the test to edit. A cached pass shows its previously
observed output; unchanged earlier tests are not executed again on every save.

## Terminal colors are hard to read or missing

Use `./koans --color never` for plain text, or `./koans --color always` if your
editor terminal supports colors but is not detected automatically. `NO_COLOR=1`
and `TERM=dumb` disable automatic coloring, as does piping output to a file or
another command. The PASS/FAIL labels and output sections work without color.

## A timeout or runtime error

A timeout stops the tool and its child processes. Look for recursion that
does not approach a base case, or messages that recreate each other forever.
Use `./koans --timeout 20` if a slower machine needs longer. Division by zero,
invalid operations, and similar failures are displayed as native runtime
errors even when the upstream CLI exits successfully.

## A guard behaves unexpectedly

The pinned prerelease has known limitations with selecting among multiple
messages on one channel and with references to outer bindings from receive
guards. The course examples avoid depending on those cases. Read
[the guard chapter](../starters/08_guards/README.md) and the
[reproduction notes](toolchain.md#observed-limitations) before extending them.

## Setup was interrupted, or a tool needs setup

Rerun `./setup`. Verified downloads and completed build work are reused.
Incomplete downloads are never installed. A lock-file change or changed
binary requires setup again. Your `exercises/` files are independent of the
installation cache.

If an old or corrupted build cache prevents recovery, rename `.toolchain/`
and rerun setup. Keep the renamed cache until the fresh install works. For
builds killed by the operating system, try `./setup --jobs 1` and make sure
there is enough free RAM and disk. Setup's package-install step needs access
to Ubuntu repositories; its source-build step needs GitHub, crates.io, and
static.rust-lang.org. Network access is only needed for initial installation
or an uncached toolchain update.

## A file save is not noticed

Interactive `./koans` polls every quarter second and allows a short pause for
editor saves to finish. Keep `.rho`, `.module`, and local import files under
`exercises/`. The watcher checks changed bytes, so an editor's timestamp
precision does not matter. A missing file or temporarily invalid manifest
can be corrected while it keeps watching. Noninteractive stdin selects
one-shot mode; run the command in a terminal to keep watching.

## I want to start again

Copy individual sections from the matching file in `starters/` after saving
any work you want to keep. Your `exercises/` answers are ignored by Git, so
`git restore` cannot restore them.
A chapter file holds six answers, so restoring the whole file resets all
six. For a completely fresh attempt, move `exercises/` to a backup location
outside this repository and run `./koans`; it creates new copies of the
starters. Setup and the runner only create missing files and never replace
existing answers.
