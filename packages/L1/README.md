L3

The L3 Compiler is an expression based language with named variables, functions, arithmetic, conditionals, and explicit heap operations. There is an Identifier that names variables and functions as well as a Program that contains parameters and a single term body. A term is a unioned type of all avalible constructs.

Bindings and variables let and letrec bind different identifiers to terms; and then reference reads a bound name. Unlike let, letrec supports self-reference for recursive definitions.

For functions, there  is an abstract that defines the function with a list of parameters and a body. Apply is used to invoke a function with given arguments. 

For values and control we have immediate, primative, and branch. Immediate is an integer literal and primitive applies the +, -, or * operator to a left and right term. Branch is then able to be used to evaluate < or == and selects consequent or otherwise since the langage does not support boolean values. 

The last thing that L3 supports is memory and sequencing. Allocate reserves a block of memory, while load reads from the memory and store writes to memory. There is also begin which sequences terms before producing a final value. 