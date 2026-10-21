# 10 · Equations and rewrites

Work through the six sections of [koans.module](koans.module) in order.
After `./setup`, edit your local copy at `exercises/10_rules/koans.module`.

A theory can declare relationships between term shapes. An equation (`==`)
states an identity; a rewrite (`~>`) gives a directed transformation and has
a name. Both use constructor labels rather than their concrete spellings.

```module
Module Unwrap {
  Theory T() {
    Types { Value; }
    Terms {
      Atom . |- "a" : Value;
      Wrap . x:Value |- "wrap" x : Value;
    }
    Rewrites { Unwrap : (Wrap x) ~> x; }
  }
  theory T()
}
```
<!-- koans-presentation: {"Types":["Value"],"Exports":[],"Terms":["Atom .  |- \"a\" : Value;","Wrap . x:Value |- \"wrap\" x : Value;"],"Equations":[],"Rewrites":["Unwrap : (Wrap x) ~> x;"]} -->

The presentation contains the rule `Unwrap : (Wrap x) ~> x;`. It describes
removing a wrapper. The elaborator retains this rule; it does not execute an
evaluator for the declared language.

Constructor applications use prefix form: `(Add x y)`. A constructor with no
arguments is written `(Zero)` when used inside a law. The variables in these
laws stand for terms. For example, `(Add x (Zero)) == x` says that adding the
zero constructor on the right is equivalent to the original term.

`(Add x y) == (Add y x)` describes commutativity, the fact that swapping
arguments preserves meaning. A directed `DropZero` rewrite instead selects
an orientation for simplification. Writing an equation does not by itself
choose a terminating evaluation strategy.

Builder blocks are processed in order. Declare constructors in `Terms`
before referencing them in `Equations` or `Rewrites`. The reference
elaborator checks references and structural requirements; it does not prove
that arbitrary equations are mathematically sound or that rewrites terminate.

After each pass, ask: **is this a symmetric identity or a directed step,
and which declared constructor labels does it use?**

[Next: reuse](../11_reuse/README.md) · [Course](../../README.md)
