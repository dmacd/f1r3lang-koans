# 09 · Modules and declarations

Work through the six sections of [koans.module](koans.module) in order.
After `./setup`, edit your local copy at `exercises/09_declarations/koans.module`.

The final four chapters describe little languages. Their `.module` files go
through a reference elaborator, which checks declarations and prints a
**presentation**: the categories, constructors, equations, and rewrites
assembled by the module. The runner compares those definitions. These
chapters do not run programs in a newly declared language.

```module
Module Shapes {
  Theory T() {
    Types { Shape; }
    Terms { Dot . |- "dot" : Shape; }
    Exports { Shape; }
  }
  theory T()
}
```
<!-- koans-presentation: {"Types":["Shape"],"Exports":["Shape"],"Terms":["Dot .  |- \"dot\" : Shape;"],"Equations":[],"Rewrites":[]} -->

This declares one category `Shape` and a constructor `Dot` whose concrete
spelling is `dot`. `Theory T()` introduces a reusable definition; the
lowercase `theory T()` at the end chooses the entry expression to elaborate.
Calling a theory uses parentheses even when it takes no arguments.

A `Terms` declaration has four parts:

```text
Wrap . x:Shape |- "wrap" "(" x ")" : Shape;
label  context   concrete syntax       result category
```

The label identifies the constructor. The context declares its input names
and categories. Each argument must occur exactly once in the concrete syntax.
Quoted pieces are literal tokens; an unquoted argument name stands for that
input. The category after the colon is the result. An empty context before
`|-` makes a constructor with no arguments, like `Dot`.

`Types` declares categories, not runtime integer or string values. A category
must exist before a constructor uses it. Constructor labels must be distinct
in the final presentation. `Exports` marks categories for reuse; chapter 11
also renames them.

Module comments use `--` or `{- ... -}`. Capitalization matters: `Module`,
`Theory`, `Types`, and `Terms` are declaration keywords; the entry keyword
`theory` is lowercase. `Empty` is reserved by this grammar.

After each pass, ask: **what shapes of terms does this theory describe?**

[Next: equations and rewrites](../10_rules/README.md) · [Course](../../README.md)
