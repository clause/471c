import pytest

from L3.check import check_term
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
    Reference,
    Store,
)


@pytest.mark.parametrize(
    "term, ctx",
    [
        # Let: let x = 1 in x
        (
            Let(bindings=[("x", Immediate(value=1))], body=Reference(name="x")),
            {},
        ),
        # LetRec: letrec f = (lambda (x) x) in f 0
        (
            LetRec(
                bindings=[("f", Abstract(parameters=["x"], body=Reference(name="x")))],
                body=Apply(target=Reference(name="f"), arguments=[Immediate(value=0)]),
            ),
            {},
        ),
        # Reference (bound)
        (Reference(name="x"), {"x": None}),
        # Abstract
        (Abstract(parameters=["x"], body=Reference(name="x")), {}),
        # Apply: ((lambda (x) x) 1)
        (
            Apply(
                target=Abstract(parameters=["x"], body=Reference(name="x")),
                arguments=[Immediate(value=1)],
            ),
            {},
        ),
        # Immediate
        (Immediate(value=0), {}),
        # Primitive
        (Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=2)), {}),
        # Branch
        (
            Branch(
                operator="<",
                left=Immediate(value=1),
                right=Immediate(value=2),
                consequent=Immediate(value=1),
                otherwise=Immediate(value=2),
            ),
            {},
        ),
        # Allocate
        (Allocate(count=3), {}),
        # Load
        (Load(base=Allocate(count=1), index=0), {}),
        # Store
        (Store(base=Allocate(count=1), index=0, value=Immediate(value=7)), {}),
        # Begin
        (Begin(effects=[Immediate(value=0), Immediate(value=1)], value=Immediate(value=2)), {}),
    ],
    ids=[
        "Let",
        "LetRec",
        "Reference_bound",
        "Abstract",
        "Apply",
        "Immediate",
        "Primitive",
        "Branch",
        "Allocate",
        "Load",
        "Store",
        "Begin",
    ],
)


def test_check_term_hits_all_cases(term, ctx):
    """
    Execute `check_term` on one representative AST node per syntax variant.

    - This single parametrized test is the main "coverage booster".
    - It ensures every `case ...:` arm in `check_term` is executed at least once.
    - The constructed terms are intentionally "well-formed" so they should pass semantic checking.
    """
    check_term(term, ctx)


def test_reference_unbound_raises():
    """
    Cover the error path for `Reference` when the identifier is NOT present in the context.

    This specifically drives the `Reference(...)` case into its `raise ValueError` branch,
    improving branch coverage.
    """
    with pytest.raises(ValueError):
        check_term(Reference(name="x"), {})


def test_let_duplicate_binding_raises():
    """
    Cover the error path for `Let` with duplicate bindings.

    The AST binds the same variable name twice in the same `let`.
    `check_term` should raise (since shadowing/duplicate binding is disallowed in this checker).
    """
    t = Let(
        bindings=[("x", Immediate(value=1)), ("x", Immediate(value=2))],
        body=Reference(name="x"),
    )
    with pytest.raises(ValueError):
        check_term(t, {})


def test_letrec_duplicate_binding_raises():
    """
    Cover the error path for `LetRec` with duplicate function bindings.

    The AST binds the same name twice in the same `letrec`, which should be rejected.
    """
    t = LetRec(
        bindings=[("f", Immediate(value=0)), ("f", Immediate(value=1))],
        body=Immediate(value=0),
    )
    with pytest.raises(ValueError):
        check_term(t, {})


def test_abstract_duplicate_param_raises():
    """
    Cover the error path for `Abstract` (lambda) with duplicate parameters.

    The parameter list contains the same identifier twice, which should be rejected.
    """
    t = Abstract(parameters=["x", "x"], body=Reference(name="x"))
    with pytest.raises(ValueError):
        check_term(t, {})