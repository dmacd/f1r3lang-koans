# 06 · Contracts and recursion

Work through the six sections of [koans.rho](koans.rho) in order.
After `./setup`, edit your local copy at `exercises/06_contracts/koans.rho`.

An ordinary receive is used once. A persistent receive, written `<=`, stays
available for more messages. A `contract` is a convenient declaration of a
persistent service on a channel.

```rho
new square, answer, stdout(`rho:io:stdout`) in {
  contract square(@n, ret) = { ret!(n * n) } |
  square!(4, *answer) |
  for (@result <- answer) { stdout!(result) }
}
```
<!-- koans-output: {"mode":"unordered","events":["16"]} -->

This prints `16`. The service waits for an integer and a reply channel,
computes the square, and sends it back. The request and answer travel as
messages; an ordinary function-call return is not implicit.

A contract can send another request to itself. That is recursion. A countdown
must eventually reach a stopping case; a list sum recurses on a shorter
tail. For the sum, each call creates a private reply channel, waits for the
tail sum, and adds the head before responding to its own caller.

`stdout!(n) | count!(n - 1)` enables printing and the next recursive call in
parallel. It does not guarantee that the larger number prints first. The
countdown koan therefore checks the collection of observed numbers.

The final koan creates a service inside another service. A fresh inner
channel keeps the new service private until the factory sends its name to
the caller. The inner body can still use the outer parameter, which is how
an adder remembers its chosen amount.

After each pass, ask: **what stays available for another request, and what
makes recursion finish?**

[Next: coordination and state](../07_coordination/README.md) · [Course](../../README.md)
