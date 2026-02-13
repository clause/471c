At the lowest level availabe, L0 differs from L1 in the removal of Abstract, the addition of Address and Procedure, aswell as changing Apply to instead be identified as Call. Along with this is the new helper function to_ast_procedure.

Abstract and Apply were responsible for encoding and returning an AST node in its encoded form, and for loading an AST into a target destination by utilizing a function respectively.

Address has been implemented, which goes further in differentiating between destination and value, unlike apply which had still identified both as a single entity. To compliment this, Apply has been changed to Call, further abstracting its purpose and more emphasizing its general usage as a function call on an array of targets.

Procedure is introduced as a new identifier, along with a helper function in to_python, which is in turn used by to_ast_program. Procedure's goal seems to be to store functions and tag them as such, likely in order to phase out certain higher level functions that can instead be stored under the umbrella of the procedure tag.