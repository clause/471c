from .constant_folding import constant_folding_term
from .constant_propogation import constant_propogation_term
from .dead_code_elimination import dead_code_elimination_term
from .syntax import Program


def optimize_program_step(
    program: Program,
) -> tuple[Program, bool]:
    propagated = Program(
        parameters=program.parameters,
        body=constant_propogation_term(program.body, {}),
    )
    folded = Program(
        parameters=propagated.parameters,
        body=constant_folding_term(propagated.body, {}),
    )
    eliminated = Program(
        parameters=folded.parameters,
        body=dead_code_elimination_term(folded.body, {}),
    )
    return eliminated, eliminated != program


def optimize_program(
    program: Program,
) -> Program:
    current = program
    while True:
        current, changed = optimize_program_step(current)
        if not changed:
            return current
