# 07 · Coordination and state

Work through the six sections of [koans.rho](koans.rho) in order.
After `./setup`, edit your local copy at `exercises/07_coordination/koans.rho`.

A join receive waits for messages on several channels and consumes the
matching group together. Separate its bindings with `&`:

```rho
new left, right, stdout(`rho:io:stdout`) in {
  left!(6) | right!(7) |
  for (@x <- left & @y <- right) { stdout!(x * y) }
}
```
<!-- koans-output: {"mode":"unordered","events":["42"]} -->

This prints `42` once both inputs are available. A join is one receive with
several requirements; `|` instead connects entire processes in parallel.

A semicolon between receipt groups means they occur sequentially. An earlier
group may provide the name of a channel used by the next one. These groups
do not consume all their messages atomically as a single join does.

The peek arrow `<<-` reads a matching message without removing it. The peek
koan follows that read with a consuming receive of the same value. The
one-shot consuming arrow remains `<-`; the persistent receiver arrow is `<=`.

State can be represented as a message holding a value on a private channel.
An update takes that message, computes a new value, and sends a replacement.
Two updates cannot both own the same single message at once. Each must wait
for a value to become available. This coordinates updates without a shared
variable assignment.

Acknowledgments coordinate observations. `stdoutAck` prints its first
argument and then signals the supplied acknowledgment channel. Waiting for
that signal establishes a specific print order. Similarly, the last koan
waits for two update acknowledgments before reading the final cell value.

After each pass, ask: **which messages must exist before the next action
can run, and which messages are consumed together?**

[Next: guards](../08_guards/README.md) · [Course](../../README.md)
