# 12 · Sharing and composition

Work through the six sections of [koans.module](koans.module) in order.
After `./setup`, edit your local copy at `exercises/12_composition/koans.module`.

Two calls to a theory can introduce different declaration identities even
when the resulting names look the same. To build extensions over a shared
base, construct the base once and pass that same instance to both branches.

```module
Module TwoShapes {
  Theory Base() { Types { Shape; } Exports { Shape; } }
  Theory Round(b: Base) { b Terms { Circle . |- "circle" : Shape; } }
  Theory Angular(b: Base) { b Terms { Square . |- "square" : Shape; } }
  theory let b = Base() in (Round(b) \/ Angular(b))
}
```
<!-- koans-presentation: {"Types":["Shape"],"Exports":["Shape"],"Terms":["Circle .  |- \"circle\" : Shape;","Square .  |- \"square\" : Shape;"],"Equations":[],"Rewrites":[]} -->

This produces one `Shape` category and both constructors. `let` binds the
single base instance. Replacing either use of `b` with a fresh `Base()`
creates an independent origin; equal spelling alone does not establish
sharing and can produce a name conflict.

The theory composition operators are:

| Operator | Effect |
| --- | --- |
| `\/` | Join the declarations from both sides, retaining shared origins once |
| `/\` | Meet: keep the origins shared by both presentations |
| `\` | Difference: remove origins present in the right-hand presentation |

For `Round(b) /\ Angular(b)`, only the shared base remains. In a diamond,
two branches inherit the same constructor through the same intermediate
instance; joining them retains that constructor once.

Difference acts on categories as well as constructors. The difference koan
removes an inherited fragment and then rejoins the original base category,
so the remaining `Extra` constructor still has its category. Simply
subtracting everything in the base can otherwise leave an incomplete
presentation in this reference implementation.

The final koan shares an `Expr` category, joins zero and addition syntax,
and adds a directed simplification rule. Its result is a checked language
description. Executing terms in that generated language is a future
integration step beyond the available reference elaborator.

After the last pass, try explaining how the same idea—explicitly sharing an
identity—appeared in channel communication and in theory composition. The
tools are different, but carefully tracking what is shared helps in both.

[Course](../../README.md) · [Toolchain and future upgrades](../../docs/toolchain.md)
