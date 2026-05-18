from typing import cast

from L2.constant_folding import constant_folding_term
from L2.constant_propogation import constant_propogation_term
from L2.dead_code_elimination import dead_code_elimination_term, free_vars, is_pure
from L2.optimize import optimize_program, optimize_program_step
from L2.syntax import (
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Immediate,
    Let,
    Load,
    Primitive,
    Program,
    Reference,
    Store,
    Term,
)
from pydantic import ValidationError

# Used copilot to help with writing these tests, gave it my expected input and output and it generated tests that I then modified to be more comprehensive and cover more edge cases.


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


def test_constant_propogation_term_all_cases():
    term = Let(
        bindings=[
            ("x", Immediate(value=1)),
            ("y", Reference(name="x")),
        ],
        body=Begin(
            effects=[
                Apply(target=Reference(name="f"), arguments=[Reference(name="y")]),
                Store(base=Reference(name="arr"), index=0, value=Reference(name="x")),
            ],
            value=Branch(
                operator="<",
                left=Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=2)),
                right=Immediate(value=5),
                consequent=Load(base=Allocate(count=1), index=0),
                otherwise=Abstract(parameters=["x"], body=Reference(name="x")),
            ),
        ),
    )

    expected = Let(
        bindings=[
            ("x", Immediate(value=1)),
            ("y", Reference(name="x")),
        ],
        body=Begin(
            effects=[
                Apply(target=Reference(name="f"), arguments=[Reference(name="x")]),
                Store(base=Reference(name="arr"), index=0, value=Immediate(value=1)),
            ],
            value=Branch(
                operator="<",
                left=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
                right=Immediate(value=5),
                consequent=Load(base=Allocate(count=1), index=0),
                otherwise=Abstract(parameters=["x"], body=Reference(name="x")),
            ),
        ),
    )

    actual = constant_propogation_term(term, context={"f": Reference(name="f")})

    assert actual == expected


def test_constant_folding_plus_cases():
    term = Primitive(
        operator="+",
        left=Primitive(operator="+", left=Immediate(value=2), right=Reference(name="a")),
        right=Primitive(operator="+", left=Immediate(value=3), right=Reference(name="b")),
    )

    expected = Primitive(
        operator="+",
        left=Immediate(value=5),
        right=Primitive(
            operator="+",
            left=Reference(name="a"),
            right=Reference(name="b"),
        ),
    )

    actual = constant_folding_term(term, context={})

    assert actual == expected

    actual_immediate = constant_folding_term(
        Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
        context={},
    )
    assert actual_immediate == Immediate(value=3)

    actual_zero = constant_folding_term(
        Primitive(operator="+", left=Immediate(value=0), right=Reference(name="x")),
        context={},
    )
    assert actual_zero == Reference(name="x")

    actual_normalize = constant_folding_term(
        Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=9)),
        context={},
    )
    assert actual_normalize == Primitive(
        operator="+",
        left=Immediate(value=9),
        right=Reference(name="x"),
    )


def test_constant_folding_minus_and_multiply_cases():
    actual_subtract = constant_folding_term(
        Primitive(operator="-", left=Immediate(value=9), right=Immediate(value=4)),
        context={},
    )
    assert actual_subtract == Immediate(value=5)

    actual_subtract_not_folded = constant_folding_term(
        Primitive(operator="-", left=Reference(name="x"), right=Immediate(value=4)),
        context={},
    )
    assert actual_subtract_not_folded == Primitive(
        operator="-",
        left=Reference(name="x"),
        right=Immediate(value=4),
    )

    actual_multiply = constant_folding_term(
        Primitive(operator="*", left=Immediate(value=3), right=Immediate(value=4)),
        context={},
    )
    assert actual_multiply == Immediate(value=12)

    actual_mul_left_zero = constant_folding_term(
        Primitive(operator="*", left=Immediate(value=0), right=Reference(name="x")),
        context={},
    )
    assert actual_mul_left_zero == Immediate(value=0)

    actual_mul_right_zero = constant_folding_term(
        Primitive(operator="*", left=Reference(name="x"), right=Immediate(value=0)),
        context={},
    )
    assert actual_mul_right_zero == Immediate(value=0)

    actual_mul_left_one = constant_folding_term(
        Primitive(operator="*", left=Immediate(value=1), right=Reference(name="x")),
        context={},
    )
    assert actual_mul_left_one == Reference(name="x")

    actual_mul_right_one = constant_folding_term(
        Primitive(operator="*", left=Reference(name="x"), right=Immediate(value=1)),
        context={},
    )
    assert actual_mul_right_one == Reference(name="x")

    actual_mul_normalize = constant_folding_term(
        Primitive(operator="*", left=Reference(name="x"), right=Immediate(value=7)),
        context={},
    )
    assert actual_mul_normalize == Primitive(
        operator="*",
        left=Immediate(value=7),
        right=Reference(name="x"),
    )

    actual_mul_not_folded = constant_folding_term(
        Primitive(operator="*", left=Reference(name="x"), right=Reference(name="y")),
        context={},
    )
    assert actual_mul_not_folded == Primitive(
        operator="*",
        left=Reference(name="x"),
        right=Reference(name="y"),
    )


def test_constant_folding_non_primitive_cases_and_branches():
    actual_reference_hit = constant_folding_term(Reference(name="x"), context={"x": Immediate(value=4)})
    assert actual_reference_hit == Immediate(value=4)

    actual_reference_miss = constant_folding_term(Reference(name="y"), context={"x": Immediate(value=4)})
    assert actual_reference_miss == Reference(name="y")

    actual_abstract = constant_folding_term(
        Abstract(parameters=["x"], body=Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=1))),
        context={},
    )
    assert actual_abstract == Abstract(
        parameters=["x"],
        body=Primitive(operator="+", left=Immediate(value=1), right=Reference(name="x")),
    )

    actual_apply = constant_folding_term(
        Apply(
            target=Reference(name="f"),
            arguments=[Primitive(operator="+", left=Immediate(value=2), right=Immediate(value=3))],
        ),
        context={},
    )
    assert actual_apply == Apply(target=Reference(name="f"), arguments=[Immediate(value=5)])

    actual_immediate = constant_folding_term(Immediate(value=11), context={})
    assert actual_immediate == Immediate(value=11)

    actual_lt_true = constant_folding_term(
        Branch(
            operator="<",
            left=Immediate(value=1),
            right=Immediate(value=2),
            consequent=Immediate(value=7),
            otherwise=Immediate(value=8),
        ),
        context={},
    )
    assert actual_lt_true == Immediate(value=7)

    actual_lt_false = constant_folding_term(
        Branch(
            operator="<",
            left=Immediate(value=4),
            right=Immediate(value=2),
            consequent=Immediate(value=7),
            otherwise=Immediate(value=8),
        ),
        context={},
    )
    assert actual_lt_false == Immediate(value=8)

    actual_lt_fallback = constant_folding_term(
        Branch(
            operator="<",
            left=Reference(name="x"),
            right=Immediate(value=2),
            consequent=Immediate(value=7),
            otherwise=Immediate(value=8),
        ),
        context={},
    )
    assert actual_lt_fallback == Branch(
        operator="<",
        left=Reference(name="x"),
        right=Immediate(value=2),
        consequent=Immediate(value=7),
        otherwise=Immediate(value=8),
    )

    actual_eq_true = constant_folding_term(
        Branch(
            operator="==",
            left=Immediate(value=3),
            right=Immediate(value=3),
            consequent=Immediate(value=9),
            otherwise=Immediate(value=10),
        ),
        context={},
    )
    assert actual_eq_true == Immediate(value=9)

    actual_eq_false = constant_folding_term(
        Branch(
            operator="==",
            left=Immediate(value=3),
            right=Immediate(value=4),
            consequent=Immediate(value=9),
            otherwise=Immediate(value=10),
        ),
        context={},
    )
    assert actual_eq_false == Immediate(value=10)

    actual_eq_fallback = constant_folding_term(
        Branch(
            operator="==",
            left=Reference(name="x"),
            right=Immediate(value=4),
            consequent=Immediate(value=9),
            otherwise=Immediate(value=10),
        ),
        context={},
    )
    assert actual_eq_fallback == Branch(
        operator="==",
        left=Reference(name="x"),
        right=Immediate(value=4),
        consequent=Immediate(value=9),
        otherwise=Immediate(value=10),
    )

    actual_allocate = constant_folding_term(Allocate(count=3), context={})
    assert actual_allocate == Allocate(count=3)

    actual_load = constant_folding_term(
        Load(base=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)), index=0), context={}
    )
    assert actual_load == Load(base=Immediate(value=3), index=0)

    actual_store = constant_folding_term(
        Store(
            base=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)),
            index=0,
            value=Primitive(operator="+", left=Immediate(value=3), right=Immediate(value=4)),
        ),
        context={},
    )
    assert actual_store == Store(base=Immediate(value=3), index=0, value=Immediate(value=7))

    actual_begin = constant_folding_term(
        Begin(
            effects=[Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2))],
            value=Primitive(operator="+", left=Immediate(value=3), right=Immediate(value=4)),
        ),
        context={},
    )
    assert actual_begin == Begin(effects=[Immediate(value=3)], value=Immediate(value=7))


def test_dead_codeis_pure_andfree_vars_cases():
    assert is_pure(Immediate(value=1)) is True
    assert is_pure(Reference(name="x")) is True
    assert is_pure(Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2))) is True
    assert is_pure(Abstract(parameters=["x"], body=Reference(name="x"))) is True
    assert is_pure(Let(bindings=[("x", Immediate(value=1))], body=Reference(name="x"))) is True
    assert (
        is_pure(
            Branch(
                operator="<",
                left=Immediate(value=1),
                right=Immediate(value=2),
                consequent=Immediate(value=3),
                otherwise=Immediate(value=4),
            )
        )
        is True
    )
    assert is_pure(Load(base=Reference(name="x"), index=0)) is True
    assert is_pure(Begin(effects=[Immediate(value=1)], value=Reference(name="x"))) is True
    assert is_pure(Apply(target=Reference(name="f"), arguments=[])) is False
    assert is_pure(Allocate(count=1)) is False
    assert is_pure(Store(base=Reference(name="x"), index=0, value=Immediate(value=1))) is False

    assert free_vars(Immediate(value=1)) == set()
    assert free_vars(Reference(name="x")) == {"x"}
    assert free_vars(Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y"))) == {"x", "y"}
    assert free_vars(Apply(target=Reference(name="f"), arguments=[Reference(name="x")])) == {"f", "x"}
    assert free_vars(
        Abstract(parameters=["x"], body=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y")))
    ) == {"y"}
    assert free_vars(
        Branch(
            operator="<",
            left=Reference(name="a"),
            right=Reference(name="b"),
            consequent=Reference(name="c"),
            otherwise=Reference(name="d"),
        )
    ) == {"a", "b", "c", "d"}
    assert free_vars(Load(base=Reference(name="arr"), index=0)) == {"arr"}
    assert free_vars(Store(base=Reference(name="arr"), index=0, value=Reference(name="v"))) == {"arr", "v"}
    assert free_vars(Begin(effects=[Reference(name="u")], value=Reference(name="v"))) == {"u", "v"}
    assert free_vars(Allocate(count=1)) == set()
    assert free_vars(
        Let(
            bindings=[
                ("x", Reference(name="a")),
                ("y", Primitive(operator="+", left=Reference(name="x"), right=Reference(name="b"))),
            ],
            body=Primitive(operator="+", left=Reference(name="y"), right=Reference(name="c")),
        )
    ) == {"a", "b", "c", "x"}


def test_dead_code_elimination_term_all_cases():
    term_drop_let = Let(
        bindings=[("x", Immediate(value=1))],
        body=Immediate(value=7),
    )
    expected_drop_let = Immediate(value=7)
    actual_drop_let = dead_code_elimination_term(term_drop_let, context={})
    assert actual_drop_let == expected_drop_let

    term_keep_let = Let(
        bindings=[("x", Store(base=Reference(name="arr"), index=0, value=Immediate(value=1)))],
        body=Immediate(value=7),
    )
    expected_keep_let = Let(
        bindings=[("x", Store(base=Reference(name="arr"), index=0, value=Immediate(value=1)))],
        body=Immediate(value=7),
    )
    actual_keep_let = dead_code_elimination_term(term_keep_let, context={})
    assert actual_keep_let == expected_keep_let

    actual_reference = dead_code_elimination_term(Reference(name="x"), context={})
    assert actual_reference == Reference(name="x")

    actual_abstract = dead_code_elimination_term(
        Abstract(parameters=["x"], body=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2))),
        context={},
    )
    assert actual_abstract == Abstract(
        parameters=["x"], body=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2))
    )

    actual_apply = dead_code_elimination_term(
        Apply(
            target=Reference(name="f"),
            arguments=[Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2))],
        ),
        context={},
    )
    assert actual_apply == Apply(
        target=Reference(name="f"),
        arguments=[Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2))],
    )

    actual_immediate = dead_code_elimination_term(Immediate(value=5), context={})
    assert actual_immediate == Immediate(value=5)

    actual_primitive = dead_code_elimination_term(
        Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=2)),
        context={},
    )
    assert actual_primitive == Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=2))

    actual_branch = dead_code_elimination_term(
        Branch(
            operator="==",
            left=Reference(name="x"),
            right=Immediate(value=2),
            consequent=Immediate(value=1),
            otherwise=Immediate(value=0),
        ),
        context={},
    )
    assert actual_branch == Branch(
        operator="==",
        left=Reference(name="x"),
        right=Immediate(value=2),
        consequent=Immediate(value=1),
        otherwise=Immediate(value=0),
    )

    actual_allocate = dead_code_elimination_term(Allocate(count=2), context={})
    assert actual_allocate == Allocate(count=2)

    actual_load = dead_code_elimination_term(Load(base=Reference(name="arr"), index=0), context={})
    assert actual_load == Load(base=Reference(name="arr"), index=0)

    actual_store = dead_code_elimination_term(
        Store(base=Reference(name="arr"), index=0, value=Immediate(value=7)),
        context={},
    )
    assert actual_store == Store(base=Reference(name="arr"), index=0, value=Immediate(value=7))

    term_begin_drop = Begin(effects=[Immediate(value=1)], value=Reference(name="x"))
    expected_begin_drop = Reference(name="x")
    actual_begin_drop = dead_code_elimination_term(term_begin_drop, context={})
    assert actual_begin_drop == expected_begin_drop

    term_begin_keep = Begin(
        effects=[Immediate(value=1), Store(base=Reference(name="arr"), index=0, value=Immediate(value=9))],
        value=Reference(name="x"),
    )
    expected_begin_keep = Begin(
        effects=[Store(base=Reference(name="arr"), index=0, value=Immediate(value=9))],
        value=Reference(name="x"),
    )
    actual_begin_keep = dead_code_elimination_term(term_begin_keep, context={})
    assert actual_begin_keep == expected_begin_keep


def test_optimize_program_step_and_optimize_program():
    program_change = Program(
        parameters=[],
        body=Let(
            bindings=[
                ("x", Immediate(value=1)),
                ("y", Reference(name="x")),
                ("z", Primitive(operator="+", left=Reference(name="y"), right=Immediate(value=2))),
            ],
            body=Reference(name="z"),
        ),
    )

    expected_step_program = Program(
        parameters=[],
        body=Let(
            bindings=[
                ("x", Immediate(value=1)),
                ("y", Reference(name="x")),
                ("z", Primitive(operator="+", left=Immediate(value=2), right=Reference(name="y"))),
            ],
            body=Reference(name="z"),
        ),
    )

    actual_step_program, changed = optimize_program_step(program_change)

    assert actual_step_program == expected_step_program
    assert changed is True

    program_no_change = Program(
        parameters=["x"],
        body=Reference(name="x"),
    )

    actual_same_program, changed_same = optimize_program_step(program_no_change)

    assert actual_same_program == program_no_change
    assert changed_same is False

    actual_optimize = optimize_program(program_change)

    assert actual_optimize == expected_step_program

    actual_optimize_no_change = optimize_program(program_no_change)

    assert actual_optimize_no_change == program_no_change


def test_dead_code_helper_fallthrough_cases():
    invalid_term = cast(Term, object())

    actualis_pure = is_pure(invalid_term)
    assert actualis_pure is None

    actualfree_vars = free_vars(invalid_term)
    assert actualfree_vars is None


def test_constant_folding_edge_fallthrough_cases():
    plus_invalid = Primitive.model_construct(
        operator="+",
        left=Reference(name="x"),
        right=object(),
    )
    with_validation_error_plus = False
    try:
        constant_folding_term(plus_invalid, context={})
    except ValidationError:
        with_validation_error_plus = True
    assert with_validation_error_plus is True

    minus_invalid = Primitive.model_construct(
        operator="-",
        left=Reference(name="x"),
        right=object(),
    )
    with_validation_error_minus = False
    try:
        constant_folding_term(minus_invalid, context={})
    except ValidationError:
        with_validation_error_minus = True
    assert with_validation_error_minus is True

    multiply_invalid = Primitive.model_construct(
        operator="*",
        left=Reference(name="x"),
        right=object(),
    )
    with_validation_error_multiply = False
    try:
        constant_folding_term(multiply_invalid, context={})
    except ValidationError:
        with_validation_error_multiply = True
    assert with_validation_error_multiply is True
