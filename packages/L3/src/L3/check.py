from collections.abc import Mapping
from functools import partial
from typing import Counter

from .syntax import (
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Identifier,
    Immediate,
    Let,
    LetRec,
    Load,
    Primitive,
    Program,
    Reference,
    Store,
    Term,
)

type Context = Mapping[Identifier, None]


def check_term(
    term: Term,
    context: Context,
) -> None:
    recur = partial(check_term, context=context)  # noqa: F841

    match term:
        case Let(bindings=bindings, body=body):
            counts = Counter(name for name, _ in bindings)
            duplicates = {name: count for name, count in counts.items() if count > 1}
            if duplicates:
                raise ValueError(f"Duplicate bindings: {duplicates}")

            for _, value in bindings:
                recur(value)

            local = dict.fromkeys([name for name, _ in bindings])
            recur(body, context={**context, **local})

        case LetRec(bindings=bindings, body=body):
            counts = Counter(name for name, _ in bindings)
            duplicates = {name: count for name, count in counts.items() if count > 1}
            if duplicates:
                raise ValueError(f"Duplicate bindings: {duplicates}")

            local = dict.fromkeys([name for name, _ in bindings])

            for name, value in bindings:
                recur(value, context={**context, **local})

            check_term(body, context={**context, **local})

        case Reference(name=name):  # Leaf
            if name not in context:
                raise ValueError(f"Unbound variable: {name}")

        case Abstract(parameters=parameters, body=body):  # Done
            counts = Counter(parameters)
            duplicates = {name for name, count in counts.items() if count > 1}
            if duplicates:
                raise ValueError(f"Duplicate parameters: {duplicates}")
            local = dict.fromkeys(parameters, None)
            check_term(body, context=local)

        case Apply(target=target, arguments=arguments):  # Done
            recur(target)
            for argument in arguments:
                recur(argument)

        case Immediate(value=_value):  # Leaf
            pass

        case Primitive(operator=_operator, left=left, right=right):  # Should be done
            recur(left)
            recur(right)

        case Branch(operator=_operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            recur(left)
            recur(right)
            recur(consequent)
            recur(otherwise)

        case Allocate(count=_count):
            pass  # No need to check count, as it is a non-negative integer by construction

        case Load(base=base, index=_index):
            recur(base)  # No need to check index, as it is a non-negative integer by construction

        case Store(base=base, index=_index, value=value):
            recur(base)  # No need to check index, as it is a non-negative integer by construction
            recur(value)

        case Begin(effects=effects, value=value):  # pragma: no branch
            for effect in effects:
                recur(effect)
            recur(value)


def check_program(program: Program) -> None:
    match program:
        case Program(parameters=parameters, body=body):  # pragma: no branch
            counts = Counter(parameters)
            duplicates = {name for name, count in counts.items() if count > 1}
            if duplicates:
                raise ValueError(f"Duplicate parameters: {duplicates}")
            local = dict.fromkeys(parameters, None)
            check_term(body, context=local)
