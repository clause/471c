from collections import Counter
from collections.abc import Mapping
from functools import partial

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
    """
    Perform a lightweight static semantic check over an L3 AST term.

    What it checks:
    - Unbound variable use:
        * Any `Reference(name=...)` must appear in `context`, otherwise raise ValueError.
    - Duplicate bindings / shadowing disallowed:
        * `Let` cannot bind the same identifier twice (and cannot reuse an identifier already in scope).
        * `LetRec` cannot bind the same identifier twice (and cannot reuse an identifier already in scope).
        * `Abstract` cannot have duplicate parameters (and cannot reuse an identifier already in scope).
      (This matches the intended lowering strategy where reusing names may break semantics.)

    What it does NOT check:
    - Types, arity, operator validity, memory bounds, etc.
      It only ensures that variable binding structure is well-formed.

    Traversal strategy:
    - Structural recursion: recursively visits sub-terms to ensure checks apply everywhere.
    - `recur` is a convenience wrapper that reuses the same `context`.
    """
    recur = partial(check_term, context=context)

    match term:
        case Let(bindings=bindings, body=body):
            counts = Counter(name for name, _ in bindings)
            duplicates = {name: count for name, count in counts.items() if count > 1}
            if duplicates:
                raise ValueError(f"duplicate binders: {duplicates}")

            for _, value in bindings:
                recur(value)

            local = dict.fromkeys([name for name, _ in bindings])
            recur(body, context={**context, **local})

        case LetRec(bindings=bindings, body=body):
            counts = Counter(name for name, _ in bindings)
            duplicates = {name: count for name, count in counts.items() if count > 1}
            if duplicates:
                raise ValueError(f"duplicate binders: {duplicates}")

            local = dict.fromkeys([name for name, _ in bindings])

            for name, value in bindings:
                recur(value, context={**context, **local})

            check_term(body, {**context, **local})

        case Reference(name=name):
            if name not in context:
                raise ValueError(f"unknown variable: {name}")

        case Abstract(parameters=parameters, body=body):
            counts = Counter(parameters)
            duplicates = {name for name, count in counts.items() if count > 1}
            if duplicates:
                raise ValueError(f"duplicate parameters: {duplicates}")

            local = dict.fromkeys(parameters, None)
            recur(body, context={**context, **local})

        case Apply(target=target, arguments=arguments):
            recur(target)
            for argument in arguments:
                recur(argument)

        case Immediate(value=_value):
            pass

        case Primitive(operator=_operator, left=left, right=right):
            recur(left)
            recur(right)

        case Branch(operator=_operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            recur(left)
            recur(right)
            recur(consequent)
            recur(otherwise)

        case Allocate(count=_count):
            pass

        case Load(base=base, index=_index):
            recur(base)

        case Store(base=base, index=_index, value=value):
            recur(base)
            recur(value)

        case Begin(effects=effects, value=value):  # pragma: no branch
            for effect in effects:
                recur(effect)
            recur(value)


def check_program(
    program: Program,
) -> None:
    match program:
        case Program(parameters=parameters, body=body):  # pragma: no branch
            counts = Counter(parameters)
            duplicates = {name for name, count in counts.items() if count > 1}
            if duplicates:
                raise ValueError(f"duplicate parameters: {duplicates}")

            local = dict.fromkeys(parameters, None)
            check_term(body, context=local)
