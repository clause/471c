Level 3, at the highest level, seems to most closely resemble the origin language.

To start, it has the widest range of functions available to it, with syntax.py supporting 14 different operations.

The next important function is to_python.py, which operates by taking a program and outputting an ast-translated version of that program. It has two helper functions defined to do this, the "lower level" one being to_ast_term, and the higher level one being to_ast_program. 

To_ast_term takes an input in the form of a term object, and outputs an ast expression, and utilizes the many defined operations in syntax in order to find the correct case and return the correct translated expression.

To_ast_program takes input in the form of a program object and returns a string, which is intended to be the inputed module unparsed. The body of the module is put through to_ast_term as a helper function, which then informs the body contents with the provided ast expression.