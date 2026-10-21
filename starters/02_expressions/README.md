# 02 · Expressions and collections

Work through the six sections of [koans.rho](koans.rho) in order.
After `./setup`, edit your local copy at `exercises/02_expressions/koans.rho`.

An expression computes a value. Parentheses select which operation happens
first: `(2 + 3) * 4` is `20`. Methods use a dot, as in `list.nth(0)`.

```rho
new stdout(`rho:io:stdout`) in {
  stdout!([4, 8, 12].nth(0) + 1)
}
```
<!-- koans-output: {"mode":"unordered","events":["5"]} -->

This prints `5`: index zero selects `4`, then the addition produces `5`.
The collection operations used here are:

| Expression | Meaning |
| --- | --- |
| `"fire" ++ "fly"` | Concatenate two strings |
| `[10, 20, 30].nth(1)` | Select the second list element |
| `[10, 20].length()` | Count list elements |
| `{"red": 3, "blue": 9}.get("red")` | Look up a map key |
| `Set(1, 2).add(3)` | Produce a new set containing one more distinct element |
| `Set(1, 2).size()` | Count distinct set elements |

These operations produce values; adding to a set does not modify some shared
object behind the scenes. A repeated set member contributes nothing new.

Ordinary integer literals are signed 64-bit values. An `n` suffix selects an
arbitrary-precision integer: `100n`. Numeric types matter. Adding `100n` and
`25n` is valid; mixing `100n` and `25` is an error, even though both represent
whole numbers. The last koan introduces this distinction without requiring
knowledge of other numeric formats.

After each pass, ask: **what type and value does each subexpression produce?**

[Next: channels](../03_channels/README.md) · [Course](../../README.md)
