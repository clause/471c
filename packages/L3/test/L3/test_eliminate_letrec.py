from L2 import syntax as L2
from L3 import syntax as L3
from L3.eliminate_letrec import Context, eliminate_letrec_program, eliminate_letrec_term


def test_check_term_let():
    term = L3.Let(
        bindings=[
            ("x", L3.Immediate(value=0)),
        ],
        body=L3.Reference(name="x"),
    )

    context: Context = {}

    expected = L2.Let(
        bindings=[
            ("x", L2.Immediate(value=0)),
        ],
        body=L2.Reference(name="x"),
    )

    actual = eliminate_letrec_term(term, context)

    assert actual == expected


def test_eliminate_letrec_program():
    program = L3.Program(
        parameters=[],
        body=L3.Immediate(value=0),
    )

    expected = L2.Program(
        parameters=[],
        body=L2.Immediate(value=0),
    )

    actual = eliminate_letrec_program(program)

    assert actual == expected


def test_eliminate_letrec_reference_recursive():
    term = L3.LetRec(
        bindings=[("x", L3.Immediate(value=0))],
        body=L3.Reference(name="x"),
    )
    expected = L2.Let(
        bindings=[("x", L2.Immediate(value=0))],
        body=L2.Load(base=L2.Reference(name="x"), index=0),
    )
    actual = eliminate_letrec_term(term, context={})
    assert actual == expected


def test_eliminate_letrec_reference_non_recursive():
    term = L3.Reference(name="x")

    context: Context = {}

    expected = L2.Reference(name="x")

    actual = eliminate_letrec_term(term, context)

    assert actual == expected


def test_eliminate_letrec_body_uses_recursive_binding():
    term = L3.LetRec(
        bindings=[("x", L3.Immediate(value=1))],
        body=L3.Reference(name="x"),
    )

    expected = L2.Let(
        bindings=[("x", L2.Immediate(value=1))],
        body=L2.Load(base=L2.Reference(name="x"), index=0),
    )

    actual = eliminate_letrec_term(term, context={})

    assert actual == expected


def test_eliminate_letrec_abstract_apply():
    term = L3.Apply(
        target=L3.Abstract(parameters=["x"], body=L3.Reference(name="x")),
        arguments=[L3.Immediate(value=1)],
    )

    expected = L2.Apply(
        target=L2.Abstract(parameters=["x"], body=L2.Reference(name="x")),
        arguments=[L2.Immediate(value=1)],
    )

    actual = eliminate_letrec_term(term, context={})

    assert actual == expected


def test_eliminate_letrec_primitive_branch():
    term = L3.Branch(
        operator="<",
        left=L3.Primitive(
            operator="+",
            left=L3.Immediate(value=1),
            right=L3.Immediate(value=2),
        ),
        right=L3.Immediate(value=4),
        consequent=L3.Immediate(value=5),
        otherwise=L3.Immediate(value=6),
    )

    expected = L2.Branch(
        operator="<",
        left=L2.Primitive(
            operator="+",
            left=L2.Immediate(value=1),
            right=L2.Immediate(value=2),
        ),
        right=L2.Immediate(value=4),
        consequent=L2.Immediate(value=5),
        otherwise=L2.Immediate(value=6),
    )

    actual = eliminate_letrec_term(term, context={})

    assert actual == expected


def test_eliminate_letrec_nested_primitives():
    term = L3.Primitive(
        operator="+",
        left=L3.Primitive(
            operator="+",
            left=L3.Immediate(value=1),
            right=L3.Immediate(value=2),
        ),
        right=L3.Immediate(value=3),
    )
    expected = L2.Primitive(
        operator="+",
        left=L2.Primitive(
            operator="+",
            left=L2.Immediate(value=1),
            right=L2.Immediate(value=2),
        ),
        right=L2.Immediate(value=3),
    )
    actual = eliminate_letrec_term(term, context={})
    assert actual == expected


def test_eliminate_letrec_branch_equals():
    term = L3.Branch(
        operator="==",
        left=L3.Immediate(value=1),
        right=L3.Immediate(value=1),
        consequent=L3.Immediate(value=7),
        otherwise=L3.Immediate(value=8),
    )

    expected = L2.Branch(
        operator="==",
        left=L2.Immediate(value=1),
        right=L2.Immediate(value=1),
        consequent=L2.Immediate(value=7),
        otherwise=L2.Immediate(value=8),
    )

    actual = eliminate_letrec_term(term, context={})

    assert actual == expected


def test_eliminate_letrec_memory_and_begin():
    term = L3.Begin(
        effects=[
            L3.Store(
                base=L3.Reference(name="b"),
                index=0,
                value=L3.Immediate(value=2),
            ),
        ],
        value=L3.Load(
            base=L3.Allocate(count=1),
            index=0,
        ),
    )

    expected = L2.Begin(
        effects=[
            L2.Store(
                base=L2.Reference(name="b"),
                index=0,
                value=L2.Immediate(value=2),
            )
        ],
        value=L2.Load(
            base=L2.Allocate(count=1),
            index=0,
        ),
    )

    actual = eliminate_letrec_term(term, context={})

    assert actual == expected


def test_eliminate_letrec_allocate_and_load():
    term = L3.Load(
        base=L3.Allocate(count=1),
        index=0,
    )

    expected = L2.Load(
        base=L2.Allocate(count=1),
        index=0,
    )

    actual = eliminate_letrec_term(term, context={})

    assert actual == expected


def test_eliminate_letrec_store():
    term = L3.Store(
        base=L3.Allocate(count=1),
        index=0,
        value=L3.Immediate(value=42),
    )

    expected = L2.Store(
        base=L2.Allocate(count=1),
        index=0,
        value=L2.Immediate(value=42),
    )

    actual = eliminate_letrec_term(term, context={})

    assert actual == expected
