# Attribution

The learning loop is inspired by the
[Clojure Koans](https://github.com/functional-koans/clojure-koans). These lessons
and the Python runner were written for this project; no Clojure exercise code
is included.

The language implementations are from
[F1R3FLY-io/f1r3node-rust](https://github.com/F1R3FLY-io/f1r3node-rust), including
the `rholang-cli` runtime and `module-syntax/mettail-elab` reference elaborator.
Setup downloads their original source archives into the ignored `.toolchain/`
directory, preserving their license files. Rust, protoc, and transitive
dependencies likewise retain their respective licenses. The MIT license for
this course does not replace upstream licenses.

The runtime dependency lock is reproduced from the pinned upstream source;
the elaborator lock records its standalone, dependency-free crate. Exact
origins and hashes are recorded in `toolchain.lock.json`.
