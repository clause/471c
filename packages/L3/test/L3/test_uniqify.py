from L3.syntax import (
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Immediate,
    Let,
    LetRec,
    Load,
    Primitive,
    Program,
    Reference,
    Store,
)
from L3.uniqify import Context, uniqify_program, uniqify_term
from util.sequential_name_generator import SequentialNameGenerator


def test_uniqify_term_reference():
    term = Reference(name="x")

    context: Context = {"x": "y"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh=fresh)

    expected = Reference(name="y")

    assert actual == expected


def test_uniqify_term_reference_not_in_context():
    term = Reference(name="x")

    context: Context = {}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh=fresh)

    expected = Reference(name="x")

    assert actual == expected


def test_uniqify_immediate():
    term = Immediate(value=42)

    context: Context = dict[str, str]()
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Immediate(value=42)

    assert actual == expected


def test_uniqify_term_let():
    term = Let(
        bindings=[
            ("x", Immediate(value=1)),
            ("y", Reference(name="x")),
        ],
        body=Apply(
            target=Reference(name="x"),
            arguments=[
                Reference(name="y"),
            ],
        ),
    )

    context: Context = {"x": "y"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Let(
        bindings=[
            ("x0", Immediate(value=1)),
            ("y0", Reference(name="y")),
        ],
        body=Apply(
            target=Reference(name="x0"),
            arguments=[
                Reference(name="y0"),
            ],
        ),
    )

    assert actual == expected


def test_uniqify_term_letrec_and_abstract_and_apply():
    term = LetRec(
        bindings=[
            (
                "f",
                Abstract(
                    parameters=["x"],
                    body=Apply(
                        target=Reference(name="f"),
                        arguments=[Reference(name="x")],
                    ),
                ),
            ),
            ("y", Reference(name="f")),
        ],
        body=Reference(name="y"),
    )

    context: Context = {"f": "outer_f"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = LetRec(
        bindings=[
            (
                "f0",
                Abstract(
                    parameters=["x0"],
                    body=Apply(
                        target=Reference(name="f0"),
                        arguments=[Reference(name="x0")],
                    ),
                ),
            ),
            ("y0", Reference(name="f0")),
        ],
        body=Reference(name="y0"),
    )

    assert actual == expected


def test_uniqify_term_memory_and_control_forms():
    term = Begin(
        effects=[
            Store(
                base=Reference(name="ptr"),
                index=0,
                value=Primitive(
                    operator="+",
                    left=Reference(name="a"),
                    right=Reference(name="b"),
                ),
            )
        ],
        value=Branch(
            operator="<",
            left=Reference(name="a"),
            right=Immediate(value=0),
            consequent=Allocate(count=1),
            otherwise=Load(base=Reference(name="ptr"), index=1),
        ),
    )

    context: Context = {"a": "a1", "b": "b1", "ptr": "p1"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Begin(
        effects=[
            Store(
                base=Reference(name="p1"),
                index=0,
                value=Primitive(
                    operator="+",
                    left=Reference(name="a1"),
                    right=Reference(name="b1"),
                ),
            )
        ],
        value=Branch(
            operator="<",
            left=Reference(name="a1"),
            right=Immediate(value=0),
            consequent=Allocate(count=1),
            otherwise=Load(base=Reference(name="p1"), index=1),
        ),
    )

    assert actual == expected


def test_uniqify_program():
    program = Program(
        parameters=["x", "y"],
        body=Primitive(
            operator="+",
            left=Reference(name="x"),
            right=Reference(name="y"),
        ),
    )

    _, actual = uniqify_program(program)

    expected = Program(
        parameters=["x0", "y0"],
        body=Primitive(
            operator="+",
            left=Reference(name="x0"),
            right=Reference(name="y0"),
        ),
    )

    assert actual == expected
