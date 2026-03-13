from collections.abc import Callable, Mapping
from functools import partial

from util.sequential_name_generator import SequentialNameGenerator

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

type Context = Mapping[Identifier, Identifier]


def uniqify_term(
    term: Term,
    context: Context,
    fresh: Callable[[str], str],
) -> Term:
    _term = partial(uniqify_term, context=context, fresh=fresh)

    match term:
        case Let(bindings=bindings, body=body):
            new_bindings: list[tuple[Identifier, Term]] = []
            new_context = context
            for name, value in bindings:
                new_name = fresh(name)
                new_bindings.append((new_name, _term(value)))
                new_context = {**new_context, name: new_name}

            return Let(
                bindings=new_bindings,
                body=_term(body, new_context),
            )

        case LetRec(bindings=bindings, body=body):
            new_bindings: list[tuple[Identifier, Term]] = []
            new_context = context
            for name, value in bindings:
                new_name = fresh(name)
                new_bindings.append((new_name, value))
                new_context = {**new_context, name: new_name}

            return LetRec(
                bindings=[(new_name, _term(value)) for new_name, value in new_bindings],
                body=_term(body, new_context),
            )

        case Reference(name=name):
            if name in context:
                return Reference(name=context[name])
            return term

        case Abstract(parameters=parameters, body=body):
            new_parameters = [fresh(parameter) for parameter in parameters]
            new_context = {
                **context,
                **{parameter: new_parameter for parameter, new_parameter in zip(parameters, new_parameters)},
            }
            return Abstract(
                parameters=new_parameters,
                body=_term(body, new_context),
            )

        case Apply(target=target, arguments=arguments):
            return Apply(
                target=_term(target),
                arguments=[_term(argument) for argument in arguments],
            )

        case Immediate():
            return term

        case Primitive(operator=operator, left=left, right=right):
            return Primitive(
                operator=operator,
                left=_term(left),
                right=_term(right),
            )

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
            return Load(
                base=_term(base),
                index=index,
            )

        case Store(base=base, index=index, value=value):
            return Store(
                base=_term(base),
                index=index,
                value=_term(value),
            )

        case Begin(effects=effects, value=value):  # pragma: no branch
            return Begin(
                effects=[_term(effect) for effect in effects],
                value=_term(value),
            )


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
