# A small vocabulary

| Word | Meaning in this course |
| --- | --- |
| Value | Data such as an integer, string, Boolean, tuple, or list. |
| Process | A piece of a running program: a send, a receive, a parallel combination, or even an inactive value. |
| Name / channel | An address used to send and receive messages. `new` creates fresh, private names. |
| Send | `inbox!(7)` makes the value `7` available on `inbox`. It does not wait for a reply. |
| Receive | `for (@x <- inbox) { ... }` waits for a matching message, binds its value, and runs the body. |
| Consume | Remove a message as part of a successful receive. |
| Quote | `@P` turns a process `P` into a name. Quoting does not run the process. |
| Dereference | `*name` turns a name back into its quoted process. That process can then run. |
| Binding | A local identifier for a received value, matched part, or new name. |
| Pattern | A description of the shape a value must have, possibly binding some parts. |
| Wildcard | `_` accepts a value without binding a variable. `__` is the course's editable hole. |
| Parallel composition | `P \| Q` allows both processes to run. Textual order does not promise execution order. |
| Contract | A persistent service that can receive multiple requests. |
| Join receive | A receive requiring messages on all its channels before consuming them together. |
| Guard | A Boolean `where` condition that must succeed along with a pattern. |
| Acknowledgment | A message reporting completion, used to order later work. |
| Module | A `.module` package containing theory declarations and an entry expression. |
| Theory | A reusable description of a language's categories, syntax, and rules. |
| Category | A kind of syntax, such as `Expr`, declared in `Types`. |
| Constructor | A labeled way to build a term from arguments, declared in `Terms`. |
| Context | Before `\|-`, the names and categories of a constructor's arguments. In runner messages, “context” also means explanatory prose. |
| Equation | A symmetric law, written `==`, describing two term shapes as equivalent. |
| Rewrite | A named, directed transformation, written `~>`. |
| Presentation | The elaborator's flattened result: categories, exports, constructors, equations, and rewrites. |
| Elaboration | Resolve references, check declarations, and combine theories into a presentation. |
| Shared origin | An identity inherited from the same theory instance, even when reached through different branches. |
| DDL | “Domain definition language”: the `.module` declarations in the final four chapters. |
| Rholang | The language family underlying the runtime syntax; no separate course in it is needed here. |
| Process calculus | A mathematical way to describe interacting processes. This course teaches through programs without requiring that mathematics. |

Symbols have different meanings in different files. In `.rho`, `==` computes
a Boolean; in a `.module` `Equations` block it declares a law. A `.rho` `new`
creates a channel; calling a `.module` theory creates declaration identities.
These concepts are related, but one operation does not invoke the other tool.
