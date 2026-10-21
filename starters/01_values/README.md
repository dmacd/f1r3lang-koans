# 01 · Values and observations

Work through the six sections of [koans.rho](koans.rho) in order.
After `./setup`, edit your local copy at `exercises/01_values/koans.rho`.

A koan is a small program with a missing piece. Fill the `__`, save, and let
`./koans` show what happened. You can usually solve a koan in more than one
way. Try to explain the result before moving on.

Here is a complete program:

```rho
new stdout(`rho:io:stdout`) in {
  stdout!(9 + 4)
}
```
<!-- koans-output: {"mode":"unordered","events":["13"]} -->

It prints `13`. `stdout` is a channel connected to the built-in output service
by the surrounding `new` declaration. `!(...)` sends something to that
channel. The braces hold the program that can use this name. For now, keep
that wrapper and experiment with what is inside the parentheses.

`42` is an integer, `"hello"` is a string, and `true` and `false` are Booleans.
`+` adds numbers. `==` tests equality and `!=` tests inequality; both produce
a Boolean. The tool prints strings with quotation marks, so `"42"` differs
from `42` in both meaning and the runner's observations.

Comments begin with `//`. The identifier `__` is deliberately undefined,
which is why the first koan produces a compiler error. Replace it with a
literal or expression. A single `_` will later mean something different: a
pattern that ignores a value.

Work down the six sections in [koans.rho](koans.rho), keeping the same editor
tab open. The runner starts at the beginning and guides you to the first
unfinished section.
After a pass, ask: **what value did the program send to stdout?**

[Next: expressions and collections](../02_expressions/README.md) · [Course](../../README.md)
