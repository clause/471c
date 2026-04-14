from collections.abc import Callable, Mapping
from functools import partial

from util.sequential_name_generator import SequentialNameGenerator

from .syntax import (
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
    Term,
)

type Context = Mapping[str, str]


def uniqify_term(
    term: Term,
    context: Context,
    fresh: Callable[[str], str],
) -> Term:
    _term = partial(uniqify_term, context=context, fresh=fresh)

    match term:
        case Let(bindings=bindings, body=body):
            # Parallel let: all binding values are evaluated in the *current* context,
            # then the body is evaluated in the extended context with the fresh names.
            new_names = {name: fresh(name) for name, _ in bindings}
            new_bindings = [(new_names[name], _term(value)) for name, value in bindings]
            new_context = {**context, **new_names}
            new_body = uniqify_term(body, new_context, fresh)
            return Let(bindings=new_bindings, body=new_body)

        case LetRec(bindings=bindings, body=body):
            # Mutually recursive: all bound names are in scope for all values and body.
            new_names = {name: fresh(name) for name, _ in bindings}
            new_context = {**context, **new_names}
            _new_term = partial(uniqify_term, context=new_context, fresh=fresh)
            new_bindings = [(new_names[name], _new_term(value)) for name, value in bindings]
            new_body = _new_term(body)
            return LetRec(bindings=new_bindings, body=new_body)

        case Reference(name=name):
            return Reference(name=context[name])

        case Abstract(parameters=parameters, body=body):
            new_names = {param: fresh(param) for param in parameters}
            new_context = {**context, **new_names}
            new_body = uniqify_term(body, new_context, fresh)
            return Abstract(
                parameters=[new_names[p] for p in parameters],
                body=new_body,
            )

        case Apply(target=target, arguments=arguments):
            return Apply(
                target=_term(target),
                arguments=[_term(arg) for arg in arguments],
            )

        case Immediate():
            return term

        case Primitive(operator=operator, left=left, right=right):
            return Primitive(operator=operator, left=_term(left), right=_term(right))

        case Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            return Branch(
                operator=operator,
                left=_term(left),
                right=_term(right),
                consequent=_term(consequent),
                otherwise=_term(otherwise),
            )

        case Allocate():
            return term

        case Load(base=base, index=index):
            return Load(base=_term(base), index=_term(index))

        case Store(base=base, index=index, value=value):
            return Store(base=_term(base), index=_term(index), value=_term(value))

        case Begin(effects=effects, value=value):  # pragma: no branch
            return Begin(effects=[_term(e) for e in effects], value=_term(value))


def uniqify_program(
    program: Program,
) -> tuple[Callable[[str], str], Program]:
    fresh = SequentialNameGenerator()

    _term = partial(uniqify_term, fresh=fresh)

    match program:
        case Program(parameters=parameters, body=body):  # pragma: no branch
            local = {parameter: fresh(parameter) for parameter in parameters}
            return (
                fresh,
                Program(
                    parameters=[local[parameter] for parameter in parameters],
                    body=_term(body, local),
                ),
            )
