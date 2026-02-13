L1 is the next step down from L2, and as a result has some immediately visible absences of some prior functions, but also some new ones in place of the removals. 

In terms of what's been taken away, Begin, Let, Reference, and Term were removed. However, in their place, Copy, Halt, and Statement were implemented.

On top of this, there are new functions introduced directly into to_python.py, them being load and store.

To elaborate on the changes, the removals mean that, without a replacement, the usual method for beginning a loop, for assigning a variable, for calling a variable, and for identifying one part of an expression are now no longer in use.

The additions, though, fill some of the necessary functions in a way that simplifies them. Copy takes the work of Let and Reference, both allowing the assigning of a value to an address space and referencing an existing one depending on what is needed, while at the same time utilizing the new load and store functions written directly into to_python. 

Statement has also allowed the ability to distinguish between an identifier and the actual value itself. This effect can be felt in to_ast_program, where in line 159 the body only needs to call to_ast_statement, whereas in the equivalent line for L2, it had required an additional call to ast.Return to be properly formatted

!! uv run l3
!! uv run l3 packages/l3/examples/fact.json
