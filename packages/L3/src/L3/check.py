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
            ctx: dict[Identifier, None] = dict(context)
            for name, value in bindings:
                check_term(value, ctx)
                if name in ctx:
                    raise ValueError(f"duplicate binding (shadowing not allowed): {name!r}")
                ctx[name] = None
            check_term(body, ctx)

        case LetRec(bindings=bindings, body=body):
            ctx: dict[Identifier, None] = dict(context)
            for name, _value in bindings:
                if name in ctx:
                    raise ValueError(f"duplicate binding (shadowing not allowed): {name!r}")
                ctx[name] = None
            for _name, value in bindings:
                check_term(value, ctx)
            check_term(body, ctx)

        case Reference(name=name):
            if name not in context:
                raise ValueError(f"unbound identifier: {name!r}")

        case Abstract(parameters=parameters, body=body):
            # parameters introduce new bindings; disallow duplicates / shadowing
            ctx: dict[Identifier, None] = dict(context)
            for p in parameters:
                if p in ctx:
                    raise ValueError(f"duplicate binding (shadowing not allowed): {p!r}")
                ctx[p] = None
            check_term(body, ctx)

        case Apply(target=target, arguments=arguments):
            recur(target)
            for arg in arguments:
                recur(arg)

        case Immediate():
            # integer literal is always ok
            return

        case Primitive(left=left, right=right):
            recur(left)
            recur(right)

        case Branch(left=left, right=right, consequent=consequent, otherwise=otherwise):
            recur(left)
            recur(right)
            recur(consequent)
            recur(otherwise)

        case Allocate():
            # count is Nat (validated by pydantic)
            return

        case Load(base=base):
            recur(base)

        case Store(base=base, value=value):
            recur(base)
            recur(value)

        case Begin(effects=effects, value=value):  # pragma: no branch
            for eff in effects:
                recur(eff)
            recur(value)
