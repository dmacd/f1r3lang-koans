# Toolchain decisions and upgrade policy

Reviewed on 2026-10-20. The course needs executable `where` guards and the
`Module`/`Theory` declaration language. A single stable release covering both
was not available. These exceptions are explicit so future maintainers can
remove them without redesigning the course.

## Exact components

| Component | Pin | Reason |
| --- | --- | --- |
| Runtime | [`v0.4.46-canary.3999`](https://github.com/F1R3FLY-io/f1r3node-rust/releases/tag/v0.4.46-canary.3999), commit `616e0c5fdbb7a501987f69d55586f8a69824f8a1` | Published prerelease containing receive and match guards |
| Runtime parser | `527af8afb37f6cad470516fe316076f120b9c353` in [upstream Cargo.toml](https://github.com/F1R3FLY-io/f1r3node-rust/blob/616e0c5fdbb7a501987f69d55586f8a69824f8a1/Cargo.toml) | Upstream's exact parser dependency |
| Reference elaborator | [`module-syntax/mettail-elab` at `9c57a82b9ceaf798b361918369056312a33b051c`](https://github.com/F1R3FLY-io/f1r3node-rust/tree/9c57a82b9ceaf798b361918369056312a33b051c/module-syntax/mettail-elab) | Unreleased Module/Theory implementation |
| Rust | [`nightly-2026-02-09`](https://github.com/F1R3FLY-io/f1r3node-rust/blob/616e0c5fdbb7a501987f69d55586f8a69824f8a1/rust-toolchain.toml) | Dated toolchain required by upstream |
| protoc | [`29.3`](https://github.com/protocolbuffers/protobuf/releases/tag/v29.3) | Stable protobuf compiler used during the native build |

The newest numbered non-prerelease software release found was
[`v0.4.16`](https://github.com/F1R3FLY-io/f1r3node-rust/releases/tag/v0.4.16).
It does not provide the guard and module feature set needed here. GitHub's
“latest release” endpoint also includes evidence bundles that are explicitly
not software releases, so setup never resolves that endpoint dynamically.

The distributed `f1r3node` binary is a node/client tool; it does not provide
this course's standalone evaluation command. Setup builds `rholang-cli`
directly. The elaborator has its own Cargo workspace and no external crate
dependencies. Building just that crate avoids the feature branch's
unavailable local parser overrides and unfinished node integration. We do
not patch either implementation.

## What is reproducible

[`toolchain.lock.json`](../toolchain.lock.json) records full source commits,
download URLs, archive checksums, Rust components, and protoc. Both Cargo
locks are committed under `toolchain/`; builds use `--locked`. The parser's
Git revision and crates.io package checksums are captured by the runtime
lock. Setup installs Rust directly under `.toolchain/rust`, without rustup,
changing PATH in shell startup files, or replacing a user's compiler.

Downloads are verified before extraction and cached only after successful
verification. Install completion is recorded only after both tools pass real
smoke tests. `.toolchain/installed.json` records the lock hash, built binary
hashes, and Cargo lock hashes. The runner checks the lock and binary hashes
before using them. Its watch cache also includes section bytes, manifest data,
local module/support files, and tool identity.

Ubuntu's C compiler, OpenSSL, and other system build packages come from the
supported distribution repositories. They are not frozen by this lock, and
native binaries are not promised to be bit-for-bit identical across systems.
The lock freezes the language sources and Rust dependency resolution. A
future upstream asset deletion could still prevent an uncached setup; retain
the verified download cache for long-term installations.

## Backend boundary

Each chapter collects six independent koans separated by comment markers.
The runner sends only the selected section to the tool, padding preceding
lines with blanks to preserve native line and column numbers. Diagnostic file
paths are mapped back to the chapter. A temporary path layout preserves local
imports without writing generated programs into the learner's directories.

Runtime lessons send observations to stdout. The adapter removes only the
pinned CLI's cost footer and its known progress message. It compares either
an ordered list or a multiset, preserving multiplicity. It recognizes the
runtime-error section even when the CLI exits zero. Every evaluation gets a
new temporary storage path; a waiting receive with no observations fails.

Declaration lessons compare all five sections of the elaborated presentation.
Order between declarations is ignored; exact definitions and duplicate
counts matter. This verifies composition and compiler checks, not execution
of generated-language expressions. The
[upstream implementation plan](https://github.com/F1R3FLY-io/f1r3node-rust/blob/9c57a82b9ceaf798b361918369056312a33b051c/module-syntax/documentation/mettail-ddl-and-modules-2026-08-19.md)
describes the remaining generated-backend and logic integration.

Unexpected output formats are runner errors requiring an adapter review.
Native stderr and failure stdout are retained. No compiler simulation,
regex-based language evaluator, or answer-text comparison is used.

## Observed limitations

These were reproduced using the exact runtime above, not inferred from the
language's intended semantics:

- [Multiple candidates on one channel](../tests/fixtures/guard_multiple_candidates.rho):
  sending `-3` and `7` with a receive guarded by `x > 0` sometimes produced no
  output and sometimes printed `7`. With just `7`, it prints `7`. The guarded
  receive does not reliably search
  past a rejected candidate already on the channel.
- [An outer binding in a later guard](../tests/fixtures/guard_outer_binding.rho):
  receiving `x = 2`, then `y = 5` with `where y > x`, produced no output.
  Replacing the second guard with `y > 0` prints `7` from the final `x + y`
  body. The failure also reproduces with explicitly nested receives.

The `test_known_limit_*` native tests characterize this observed behavior;
they are not assertions of the desired language semantics. The candidate-order
probe accepts either observed outcome so it cannot make CI depend on scheduling.
The outer-binding check expects the reproduced failure and flags a change.
Review both fixtures when upgrading, including repeated trials of candidate
selection. The learner's solutions do not rely on these cases.

The reference elaborator also permits a theory difference to remove a
category while leaving constructors that refer to it. Koan 12.05 restores
the shared category with a join. Do not infer a complete generated language
type checker or termination proof from a successful elaboration.

## Moving to stable releases

1. Prefer a stable numbered software release that executes the guard corpus
   and includes the standalone interpreter. Prefer a stable integrated
   elaborator as soon as one can pass the declaration corpus.
2. Update full revisions, download checksums, dated compiler requirements,
   and Cargo locks together. Do not introduce a moving branch or `latest`.
3. Run setup from an empty cache on both supported Ubuntu versions. Check
   all 72 solutions, all 72 untouched starters, all guide examples, native
   diagnostic regressions, and offline operation.
4. Review the known-limit fixtures. Fixes should expand the course's supported
   examples; regressions must not be hidden by weakening expectations.
5. If upstream connects declarations to an evaluator, add real generated
   program executions before changing the README's scope claim.

Possible later work includes ARM/macOS builds and published, checksummed
standalone binaries. Neither is required to run this version of the course.
