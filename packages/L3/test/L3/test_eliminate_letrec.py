from L2 import syntax as L2
from L3 import syntax as L3
from L3.eliminate_letrec import Context, eliminate_letrec_program, eliminate_letrec_term

# ── Existing tests ────────────────────────────────────────────────────────────


@pytest.mark.skip
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
    program = L3.Program(parameters=[], body=L3.Immediate(value=0))
    expected = L2.Program(parameters=[], body=L2.Immediate(value=0))
    assert eliminate_letrec_program(program) == expected


# ── LetRec ────────────────────────────────────────────────────────────────────


def test_letrec_basic():
    """A self-recursive function: letrec f = (lambda () f) in f"""
    term = L3.LetRec(
        bindings=[("f", L3.Abstract(parameters=[], body=L3.Reference(name="f")))],
        body=L3.Reference(name="f"),
    )
    expected = L2.Let(
        bindings=[("f", L2.Allocate(count=1))],
        body=L2.Begin(
            effects=[
                L2.Store(
                    base=L2.Reference(name="f"),
                    index=0,
                    value=L2.Abstract(
                        parameters=[],
                        body=L2.Load(base=L2.Reference(name="f"), index=0),
                    ),
                )
            ],
            value=L2.Load(base=L2.Reference(name="f"), index=0),
        ),
    )
    assert eliminate_letrec_term(term, {}) == expected


def test_letrec_mutual_recursion():
    """Mutually recursive: letrec f = (lambda () g), g = (lambda () f) in f"""
    term = L3.LetRec(
        bindings=[
            ("f", L3.Abstract(parameters=[], body=L3.Reference(name="g"))),
            ("g", L3.Abstract(parameters=[], body=L3.Reference(name="f"))),
        ],
        body=L3.Reference(name="f"),
    )
    result = eliminate_letrec_term(term, {})
    # Both f and g should be allocated and their bodies should load from boxes
    assert isinstance(result, L2.Let)
    assert len(result.bindings) == 2
    assert result.bindings[0] == ("f", L2.Allocate(count=1))
    assert result.bindings[1] == ("g", L2.Allocate(count=1))


# ── Reference ─────────────────────────────────────────────────────────────────


def test_reference_not_in_context():
    """Plain reference outside of letrec scope passes through unchanged."""
    term = L3.Reference(name="x")
    assert eliminate_letrec_term(term, {}) == L2.Reference(name="x")


def test_reference_in_context():
    """Reference to a letrec-bound name becomes a Load."""
    term = L3.Reference(name="x")
    assert eliminate_letrec_term(term, {"x": None}) == L2.Load(base=L2.Reference(name="x"), index=0)


# ── Abstract ──────────────────────────────────────────────────────────────────


def test_abstract():
    term = L3.Abstract(parameters=["x"], body=L3.Reference(name="x"))
    expected = L2.Abstract(parameters=["x"], body=L2.Reference(name="x"))
    assert eliminate_letrec_term(term, {}) == expected


# ── Apply ─────────────────────────────────────────────────────────────────────


def test_apply():
    term = L3.Apply(
        target=L3.Reference(name="f"),
        arguments=[L3.Immediate(value=1), L3.Immediate(value=2)],
    )
    expected = L2.Apply(
        target=L2.Reference(name="f"),
        arguments=[L2.Immediate(value=1), L2.Immediate(value=2)],
    )
    assert eliminate_letrec_term(term, {}) == expected


# ── Immediate ─────────────────────────────────────────────────────────────────


def test_immediate():
    term = L3.Immediate(value=42)
    assert eliminate_letrec_term(term, {}) == L2.Immediate(value=42)


# ── Primitive ─────────────────────────────────────────────────────────────────


def test_primitive():
    term = L3.Primitive(
        operator="+",
        left=L3.Immediate(value=1),
        right=L3.Immediate(value=2),
    )
    expected = L2.Primitive(
        operator="+",
        left=L2.Immediate(value=1),
        right=L2.Immediate(value=2),
    )
    assert eliminate_letrec_term(term, {}) == expected


# ── Branch ────────────────────────────────────────────────────────────────────


def test_branch():
    term = L3.Branch(
        operator="<",
        left=L3.Immediate(value=1),
        right=L3.Immediate(value=2),
        consequent=L3.Immediate(value=10),
        otherwise=L3.Immediate(value=20),
    )
    expected = L2.Branch(
        operator="<",
        left=L2.Immediate(value=1),
        right=L2.Immediate(value=2),
        consequent=L2.Immediate(value=10),
        otherwise=L2.Immediate(value=20),
    )
    assert eliminate_letrec_term(term, {}) == expected


# ── Allocate ──────────────────────────────────────────────────────────────────


def test_allocate():
    term = L3.Allocate(count=3)
    assert eliminate_letrec_term(term, {}) == L2.Allocate(count=3)


# ── Load ──────────────────────────────────────────────────────────────────────


def test_load():
    term = L3.Load(base=L3.Reference(name="arr"), index=2)
    expected = L2.Load(base=L2.Reference(name="arr"), index=2)
    assert eliminate_letrec_term(term, {}) == expected


# ── Store ─────────────────────────────────────────────────────────────────────


def test_store():
    term = L3.Store(
        base=L3.Reference(name="arr"),
        index=0,
        value=L3.Immediate(value=99),
    )
    expected = L2.Store(
        base=L2.Reference(name="arr"),
        index=0,
        value=L2.Immediate(value=99),
    )
    assert eliminate_letrec_term(term, {}) == expected


# ── Begin ─────────────────────────────────────────────────────────────────────


def test_begin():
    term = L3.Begin(
        effects=[
            L3.Store(
                base=L3.Reference(name="arr"),
                index=0,
                value=L3.Immediate(value=1),
            )
        ],
        value=L3.Immediate(value=0),
    )
    expected = L2.Begin(
        effects=[
            L2.Store(
                base=L2.Reference(name="arr"),
                index=0,
                value=L2.Immediate(value=1),
            )
        ],
        value=L2.Immediate(value=0),
    )
    assert eliminate_letrec_term(term, {}) == expected


# ── Program with parameters ───────────────────────────────────────────────────


def test_eliminate_letrec_program_with_params():
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
