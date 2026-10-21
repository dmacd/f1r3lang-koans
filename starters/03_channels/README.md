# 03 · Names, sends, and parallel composition

Work through the six sections of [koans.rho](koans.rho) in order.
After `./setup`, edit your local copy at `exercises/03_channels/koans.rho`.

Programs communicate through channels. `new mailbox in { ... }` gives the
body a fresh channel name. `mailbox!(9)` sends a message to it. The message
can wait until a matching receiver becomes available.

```rho
new mailbox, stdout(`rho:io:stdout`) in {
  mailbox!(9) |
  for (@value <- mailbox) { stdout!(value) }
}
```
<!-- koans-output: {"mode":"unordered","events":["9"]} -->

This prints `9`. The vertical bar `|` composes two processes in parallel.
The send and receive can work together; the receiver's body runs when it
gets a matching message. The next chapter explains the `@value` pattern.

Parallel composition promises no general left-to-right order. Two independent
prints may appear in either order. A send is an action, not a function that
returns the receiver's answer.

Names created by separate `new` bindings are distinct even if their programs
look alike. Only code holding the same name can use that channel. A quoted
value such as `@"score"` can also name a channel; quoting the same string
elsewhere produces the same channel address. This shared address behaves
differently from a fresh name. `*name` exposes the process value a name
quotes; chapter 04 develops that relationship.

`Nil` is the inactive process. `P | Nil` leaves the actions of `P` unchanged.
Likewise, an unused message is not automatically printed. It remains
available on its channel until something consumes it or the isolated koan
evaluation ends.

After each pass, ask: **which names must be the same for communication to occur?**

[Next: receives and reflection](../04_receives/README.md) · [Course](../../README.md)
