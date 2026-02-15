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


def test_let() -> None:
    term = Let(
        bindings=[("x", Immediate(value=1))],
        body=Reference(name="x"),
    )

    match term:
        case Let():
            check_term(term, context={})


def test_letrec() -> None:
    term = LetRec(
        bindings=[("f", Abstract(parameters=["x"], body=Reference(name="x")))],
        body=Apply(
            target=Reference(name="f"),
            arguments=[Immediate(value=0)],
        ),
    )

    match term:
        case LetRec():
            check_term(term, context={})


def test_reference_bound() -> None:
    term = Reference(name="x")

    match term:
        case Reference():
            check_term(term, context={"x": None})


def test_abstract() -> None:
    term = Abstract(
        parameters=["x"],
        body=Reference(name="x"),
    )

    match term:
        case Abstract():
            check_term(term, context={})


def test_apply() -> None:
    term = Apply(
        target=Abstract(parameters=["x"], body=Reference(name="x")),
        arguments=[Immediate(value=1)],
    )

    match term:
        case Apply():
            check_term(term, context={})


def test_immediate() -> None:
    term = Immediate(value=0)

    match term:
        case Immediate():
            check_term(term, context={})


def test_primitive() -> None:
    term = Primitive(
        operator="+",
        left=Immediate(value=1),
        right=Immediate(value=2),
    )

    match term:
        case Primitive():
            check_term(term, context={})


def test_branch() -> None:
    term = Branch(
        operator="<",
        left=Immediate(value=1),
        right=Immediate(value=2),
        consequent=Immediate(value=1),
        otherwise=Immediate(value=2),
    )

    match term:
        case Branch():
            check_term(term, context={})


def test_allocate() -> None:
    term = Allocate(count=3)

    match term:
        case Allocate():
            check_term(term, context={})


def test_load() -> None:
    term = Load(
        base=Allocate(count=1),
        index=0,
    )

    match term:
        case Load():
            check_term(term, context={})


def test_store() -> None:
    term = Store(
        base=Allocate(count=1),
        index=0,
        value=Immediate(value=7),
    )

    match term:
        case Store():
            check_term(term, context={})


def test_begin() -> None:
    term = Begin(
        effects=[Immediate(value=0), Immediate(value=1)],
        value=Immediate(value=2),
    )

    match term:
        case Begin():  # pragma: no branch
            check_term(term, context={})


def test_reference_unbound_raises() -> None:
    term = Reference(name="x")

    match term:
        case Reference():
            with pytest.raises(ValueError):
                check_term(term, context={})


def test_let_duplicate_binding_raises() -> None:
    term = Let(
        bindings=[("x", Immediate(value=1)), ("x", Immediate(value=2))],
        body=Reference(name="x"),
    )

    match term:
        case Let():
            with pytest.raises(ValueError):
                check_term(term, context={})


def test_letrec_duplicate_binding_raises() -> None:
    term = LetRec(
        bindings=[("f", Immediate(value=0)), ("f", Immediate(value=1))],
        body=Immediate(value=0),
    )

    match term:
        case LetRec():
            with pytest.raises(ValueError):
                check_term(term, context={})


def test_abstract_duplicate_param_raises() -> None:
    term = Abstract(
        parameters=["x", "x"],
        body=Reference(name="x"),
    )

    match term:
        case Abstract():
            with pytest.raises(ValueError):
                check_term(term, context={})
