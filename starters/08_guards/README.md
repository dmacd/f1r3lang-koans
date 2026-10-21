# 08 · Guards

Work through the six sections of [koans.rho](koans.rho) in order.
After `./setup`, edit your local copy at `exercises/08_guards/koans.rho`.

A guard adds a Boolean condition to pattern matching. A receive's `where`
condition must pass before it consumes the candidate messages. A failed
guard leaves the messages available. A `match` case with a false guard falls
through to later cases.

```rho
new price, budget, stdout(`rho:io:stdout`) in {
  price!(4) | budget!(9) |
  for (@cost <- price & @limit <- budget where cost < limit) {
    stdout!(limit - cost)
  }
}
```
<!-- koans-output: {"mode":"unordered","events":["5"]} -->

This prints `5`. The join supplies both bindings to the guard. A successful
guard allows the two messages to be consumed together. If the comparison
were false, the body would not run and neither message should be consumed
by this join.

The koans build from one guarded receive to message preservation, a join
condition, match fallthrough, separately guarded receipt groups, and tuple
patterns. In the sequential-group example each guard uses its own group's
binding; the final body uses both. The last koan puts its two candidate jobs
on separate channels.

## Limits of this pinned prerelease

Our executable checks found that a rejected candidate on a channel can stop
the runtime from choosing a later eligible message already on that channel.
They also found that a receive guard referring to an outer receive's binding
can produce no result even when the comparison should be true. These are
runtime limitations, not rules that make those comparisons logically false.

The course uses examples that work with the pinned tools. For experiments
with queues or nested guards, read the [reproduction notes](../../docs/toolchain.md#observed-limitations).
The maintainer checks retain these cases for review when upgrading; the
candidate-order probe permits either observed outcome. Guards use pure
Boolean expressions here; side effects in conditions are outside this course.

After each pass, ask: **what does the pattern accept, what does the guard
require, and what remains available when that guard fails?**

[Next: modules and declarations](../09_declarations/README.md) · [Course](../../README.md)
