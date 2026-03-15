from L2.optimize import optimize_program
from L2.syntax import (
    Immediate,
    Primitive,
    Program,
)


def test_optimize_program():
    program = Program(
        parameters=[],
        body=Primitive(
            operator="+",
            left=Immediate(value=1),
            right=Immediate(value=1),
        ),
    )

    expected = Program(
        parameters=[],
        body=Immediate(value=2),
    )

    actual = optimize_program(program)

    assert actual == expected


def test_optimize_program_no_optimization():
    program = Program(
        parameters=[],
        body=Primitive(
            operator="+",
            left=Immediate(value=1),
            right=Immediate(value=2),
        ),
    )

    expected = program

    actual = optimize_program(program)

    assert actual == expected


def test_optimize_program_nested():
    program = Program(
        parameters=[],
        body=Primitive(
            operator="+",
            left=Primitive(
                operator="+",
                left=Immediate(value=1),
                right=Immediate(value=1),
            ),
            right=Immediate(value=1),
        ),
    )

    expected = Program(
        parameters=[],
        body=Primitive(
            operator="+",
            left=Immediate(value=2),
            right=Immediate(value=1),
        ),
    )

    actual = optimize_program(program)

    assert actual == expected


def test_optimize_program_no_optimization_nested():
    program = Program(
        parameters=[],
        body=Primitive(
            operator="+",
            left=Primitive(
                operator="+",
                left=Immediate(value=1),
                right=Immediate(value=2),
            ),
            right=Immediate(value=1),
        ),
    )

    expected = program

    actual = optimize_program(program)

    assert actual == expected
