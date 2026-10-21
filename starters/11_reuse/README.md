# 11 · Parameters and reuse

Work through the six sections of [koans.module](koans.module) in order.
After `./setup`, edit your local copy at `exercises/11_reuse/koans.module`.

A theory can accept another theory as a parameter and extend the supplied
presentation. This makes the common definitions and their identities
explicit.

```module
Module Decorations {
  Theory Base() { Types { Shape; } Exports { Shape; } }
  Theory Decorated(b: Base) {
    b Terms { Box . x:Shape |- "box" x : Shape; }
  }
  theory Decorated(Base())
}
```
<!-- koans-presentation: {"Types":["Shape"],"Exports":["Shape"],"Terms":["Box . x:Shape |- \"box\" x : Shape;"],"Equations":[],"Rewrites":[]} -->

`b: Base` names the parameter and its theory type. The body starts with `b`,
so it extends that supplied presentation with `Box`. The result contains
`Shape`, its export, and the new constructor.

Exports can rename a category: `Exports { Value => Expr; }` changes the
public spelling and updates constructor references. A replacement instead
adapts an existing constructor's label and syntax. For example, replacing
`Zero` with `Nothing` also updates inherited laws that reference it. The
original and replacement are not two unrelated constructors in the result.

Two import forms used here are:

```text
import "support/base.module" as lib
import Base from "support/base.module"
```

The first exposes `lib.Base()`; the second exposes `Base()` directly. Imports
resolve relative to the file containing them. Both koans use the bundled
`support/base.module`; there are no remote imports or downloads during
evaluation. The watcher also notices edits to these support files.

Keep constructors and categories distinct when reading errors. A label such
as `Zero` identifies a constructor; `Value` names the category it returns.
Renaming one kind of declaration does not use the other kind's syntax.

After each pass, ask: **what presentation is being supplied, and which
names or definitions does this extension adapt?**

[Next: sharing and composition](../12_composition/README.md) · [Course](../../README.md)
