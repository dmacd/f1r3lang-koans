# 05 · Patterns and choices

Work through the six sections of [koans.rho](koans.rho) in order.
After `./setup`, edit your local copy at `exercises/05_patterns/koans.rho`.

Patterns describe the shape of a value. A literal pattern accepts that exact
value; a variable pattern names it; `_` accepts it without creating a binding.
`match` tries branches in source order and runs the first matching body.

```rho
new stdout(`rho:io:stdout`) in {
  match [6, 7, 8] {
    [] => { stdout!(0) }
    [head ...tail] => { stdout!(head + tail.length()) }
  }
}
```
<!-- koans-output: {"mode":"unordered","events":["8"]} -->

This prints `8`. The input is not empty, so the second branch binds `head`
to `6` and `tail` to `[7, 8]`. The `...` marker binds the remaining list,
including an empty list when there is just one element.

A tuple pattern `(x, y)` binds the two positions of a tuple. Pattern
conjunction `x /\ Int` both binds `x` and requires an ordinary integer.
`"41"` is a string and will not match that integer pattern. A final wildcard
branch provides a fallback when earlier patterns fail.

Use `if (condition) { ... } else { ... }` to select a process using a Boolean
expression. Numbers are not implicitly true or false. A comparison such as
`3 < 4` gives a Boolean suitable for the condition.

After each pass, ask: **which branch matches, and what did its pattern bind?**

[Next: contracts](../06_contracts/README.md) · [Course](../../README.md)
