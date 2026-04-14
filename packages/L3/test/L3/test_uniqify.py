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

# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------


def test_uniqify_term_reference():
    term = Reference(name="x")

    context: Context = {"x": "y"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh=fresh)

    expected = Reference(name="y")

    assert actual == expected


# ---------------------------------------------------------------------------
# Immediate
# ---------------------------------------------------------------------------


def test_uniqify_immediate():
    term = Immediate(value=42)

    context: Context = dict[str, str]()
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Immediate(value=42)

    assert actual == expected


# ---------------------------------------------------------------------------
# Let
# ---------------------------------------------------------------------------


def test_uniqify_term_let():
    """
    Binding values are evaluated in the *outer* context (parallel semantics).
    The body sees all newly introduced fresh names.
    """
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
            ("y0", Reference(name="y")),  # "x" in value resolves to outer "y", not "x0"
        ],
        body=Apply(
            target=Reference(name="x0"),
            arguments=[
                Reference(name="y0"),
            ],
        ),
    )

    assert actual == expected


# ---------------------------------------------------------------------------
# LetRec
# ---------------------------------------------------------------------------


def test_uniqify_term_letrec():
    """
    All bound names are in scope for all binding values and the body
    (mutually recursive semantics).
    """
    term = LetRec(
        bindings=[
            ("f", Abstract(parameters=["x"], body=Apply(target=Reference(name="g"), arguments=[Reference(name="x")]))),
            ("g", Abstract(parameters=["x"], body=Apply(target=Reference(name="f"), arguments=[Reference(name="x")]))),
        ],
        body=Apply(target=Reference(name="f"), arguments=[Immediate(value=0)]),
    )

    context: Context = {}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    # fresh assigns: f→f0, g→g1, then x inside f→x2, x inside g→x3
    expected = LetRec(
        bindings=[
            (
                "f0",
                Abstract(
                    parameters=["x2"],
                    body=Apply(target=Reference(name="g1"), arguments=[Reference(name="x2")]),
                ),
            ),
            (
                "g1",
                Abstract(
                    parameters=["x3"],
                    body=Apply(target=Reference(name="f0"), arguments=[Reference(name="x3")]),
                ),
            ),
        ],
        body=Apply(target=Reference(name="f0"), arguments=[Immediate(value=0)]),
    )

    assert actual == expected


# ---------------------------------------------------------------------------
# Abstract
# ---------------------------------------------------------------------------


def test_uniqify_term_abstract():
    """Parameters get fresh names; body is evaluated in extended context."""
    term = Abstract(
        parameters=["a", "b"],
        body=Primitive(operator="+", left=Reference(name="a"), right=Reference(name="b")),
    )

    context: Context = {}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Abstract(
        parameters=["a0", "b1"],
        body=Primitive(operator="+", left=Reference(name="a0"), right=Reference(name="b1")),
    )

    assert actual == expected


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------


def test_uniqify_term_apply():
    term = Apply(
        target=Reference(name="f"),
        arguments=[Reference(name="x"), Immediate(value=1)],
    )

    context: Context = {"f": "f0", "x": "x0"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Apply(
        target=Reference(name="f0"),
        arguments=[Reference(name="x0"), Immediate(value=1)],
    )

    assert actual == expected


# ---------------------------------------------------------------------------
# Primitive
# ---------------------------------------------------------------------------


def test_uniqify_term_primitive():
    term = Primitive(
        operator="*",
        left=Reference(name="a"),
        right=Reference(name="b"),
    )

    context: Context = {"a": "a0", "b": "b0"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Primitive(operator="*", left=Reference(name="a0"), right=Reference(name="b0"))

    assert actual == expected


# ---------------------------------------------------------------------------
# Branch
# ---------------------------------------------------------------------------


def test_uniqify_term_branch():
    term = Branch(
        operator="<",
        left=Reference(name="x"),
        right=Immediate(value=0),
        consequent=Reference(name="a"),
        otherwise=Reference(name="b"),
    )

    context: Context = {"x": "x0", "a": "a0", "b": "b0"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Branch(
        operator="<",
        left=Reference(name="x0"),
        right=Immediate(value=0),
        consequent=Reference(name="a0"),
        otherwise=Reference(name="b0"),
    )

    assert actual == expected


# ---------------------------------------------------------------------------
# Allocate
# ---------------------------------------------------------------------------


def test_uniqify_term_allocate():
    term = Allocate()

    context: Context = {}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    assert actual == Allocate()


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------


def test_uniqify_term_load():
    term = Load(base=Reference(name="arr"), index=Reference(name="i"))

    context: Context = {"arr": "arr0", "i": "i0"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Load(base=Reference(name="arr0"), index=Reference(name="i0"))

    assert actual == expected


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


def test_uniqify_term_store():
    term = Store(
        base=Reference(name="arr"),
        index=Reference(name="i"),
        value=Reference(name="v"),
    )

    context: Context = {"arr": "arr0", "i": "i0", "v": "v0"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Store(
        base=Reference(name="arr0"),
        index=Reference(name="i0"),
        value=Reference(name="v0"),
    )

    assert actual == expected


# ---------------------------------------------------------------------------
# Begin
# ---------------------------------------------------------------------------


def test_uniqify_term_begin():
    term = Begin(
        effects=[
            Store(base=Reference(name="arr"), index=Immediate(value=0), value=Reference(name="x")),
        ],
        value=Reference(name="x"),
    )

    context: Context = {"arr": "arr0", "x": "x0"}
    fresh = SequentialNameGenerator()
    actual = uniqify_term(term, context, fresh)

    expected = Begin(
        effects=[
            Store(base=Reference(name="arr0"), index=Immediate(value=0), value=Reference(name="x0")),
        ],
        value=Reference(name="x0"),
    )

    assert actual == expected


# ---------------------------------------------------------------------------
# uniqify_program
# ---------------------------------------------------------------------------


def test_uniqify_program():
    """Top-level parameters get fresh names; body is evaluated in that context."""
    program = Program(
        parameters=["x", "y"],
        body=Primitive(operator="+", left=Reference(name="x"), right=Reference(name="y")),
    )

    fresh, result = uniqify_program(program)

    expected = Program(
        parameters=["x0", "y1"],
        body=Primitive(operator="+", left=Reference(name="x0"), right=Reference(name="y1")),
    )

    assert result == expected
