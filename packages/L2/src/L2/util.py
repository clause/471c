from collections.abc import Callable, Sequence

from .syntax import (
    Identifier,
    Immediate,
    Primitive,
    Reference,
    Term,
)

type Context = dict[Identifier, Term]


def recur_terms(
    terms: Sequence[Term],
    recur: Callable[[Term], Term],
) -> list[Term]:
    return [recur(term) for term in terms]


def extend_context_with_bindings(
    bindings: Sequence[tuple[Identifier, Term]],
    context: Context,
    recur: Callable[[Term], Term],
) -> tuple[list[tuple[Identifier, Term]], Context]:
    new_bindings: list[tuple[Identifier, Term]] = []
    new_context = dict(context)
    for name, value in bindings:
        result = recur(value)
        new_bindings.append((name, result))
        if isinstance(result, Immediate | Reference):
            new_context[name] = result
    return new_bindings, new_context


def normalize_commutative_immediate_left(
    operator: str,
    left: Term,
    right: Term,
) -> Primitive:
    return Primitive(
        operator=operator,  # type: ignore[arg-type]
        left=right,
        right=left,
    )
