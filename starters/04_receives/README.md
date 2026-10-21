# 04 · Receives and reflection

Work through the six sections of [koans.rho](koans.rho) in order.
After `./setup`, edit your local copy at `exercises/04_receives/koans.rho`.

`for (@value <- inbox) { ... }` consumes one matching message and binds its
payload as `value`. A receive without `@`, such as `for (name <- inbox)`,
binds a name quoting the payload. Use `*name` to recover that process.

```rho
new inbox, stdout(`rho:io:stdout`) in {
  inbox!(11) |
  for (quoted <- inbox) { stdout!(*quoted + 1) }
}
```
<!-- koans-output: {"mode":"unordered","events":["12"]} -->

This prints `12`. Quoting (`@P`) turns a process into a name; dereferencing
(`*name`) turns a name back into a process. The name pattern `quoted` is
automatically bound to a quote of the received value. There is no need to
add another `@` to the send's integer argument.

The same mechanism allows a message to carry executable code. Sending
`stdout!(9)` as a payload does not run that payload immediately. A receiver
can bind it as a name and dereference it to activate the send. This is the
“reflection” in the chapter title.

A request can also carry a reply channel. A sender with a fresh `reply` name
passes `*reply` as a message argument; a name pattern such as `ret` receives
it and can send an answer with `ret!(answer)`. This makes the return route an
explicit part of the message.

Pay attention to argument count. `pair!((3, 4))` sends one tuple; `pair!(3, 4)`
sends two arguments. Their receiving patterns are `@(x, y)` and `@x, @y`
respectively. Matching the wrong shape leaves the receive waiting.

After each pass, ask: **is each binding a process value or a name, and where
is the reply supposed to go?**

[Next: patterns](../05_patterns/README.md) · [Course](../../README.md)
