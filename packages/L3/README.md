Within syntax.py

The general class for the program is labeled with a tage of "l3" to identify that this is part of l3
It contains the program sequence itself as the paremeters and the body is made of the many terms later defined. It is able to have variables defined within its origin

Term is a list of all the classes we have bunching them together to allow for the programs use

Let has a tag to identify it and works to define the things within its body 
things must first be identified before they can later be used as they need memory set aside for them
The body is a term as it can contain more things within it

Letrec works similarly to the previous let however things can be defined at any point due to its recursive nature allowing variables to be defined within their own definition. This aspect is what allows them to self reference and recurse. It's used in recursive functions.

Reference is a direct thing that states the variable or place in memory we are pulling from. It is a leaf ending branches if properly implemented

Abstract is used to define a function within the program with parameters and a body that is the function itself

Apply actually runs the function that abstract defines taking the inputs that abstract requires optimally

Immediate is an integer value of some kind rather than a variable memory location

Primitive allows for adjustment of values through basic math of addition, subtraction and multiplication by seeing the operator and then having a left and right term that it applies the operators to

Branch allows for if else statements within the code by using operators of < and == checking the terms and the resulting "consequent" of if the result is true. otherwise contains the "else" of the if else and can be chained together if need be.

Allocate is what actually creates memory space for the various variables made by let and letrec

Load on the otherhand pulls from a block of memory "loading" things into the program for use

Store puts information into the listed allocated memory space allowing for a value to be input.

Begin groups the loads and stores together putting them into a proper group order "sequencing" them

