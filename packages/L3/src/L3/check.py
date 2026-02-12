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
            binding_identifiers = {identifier: None for (identifier, _) in bindings}
            context = {**context, **binding_identifiers}
            for _, term in bindings:
                recur(term, context=context)
            recur(body, context=context)

        case LetRec(bindings=bindings, body=body):
            new_context = decorate_context_for_lecrec(term, context=context)
            for _, term in bindings:
                recur(term, context=new_context)
            recur(body, context=new_context)

        case Reference(name=name):
            if name not in context:
                raise ValueError()

        case Abstract(parameters=parameters, body=body):
            local = {parameter: None for parameter in parameters}
            recur(body, context={**context, **local})

        case Apply(target=target, arguments=arguments):
            recur(target)
            for argument in arguments:
                recur(argument)

        case Immediate(value=value):
            pass

        case Primitive(operator=_operator, left=left, right=right):
            recur(left)
            recur(right)

        case Branch(operator=_operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            recur(left)
            recur(right)
            recur(consequent)
            recur(otherwise)

        case Allocate():
            pass

        case Load(base=base):
            recur(base)

        case Store(base=base, value=value):
            recur(base)
            recur(value)

        case Begin(effects=effects, value=value):  # pragma: no branch
            for effect in effects:
                recur(effect)
            recur(value)


def decorate_context_for_lecrec(
    term: Term,
    context: Context,
) -> Context:
    match term:
        case Let(bindings=bindings, body=body):
            new_context = {**context}
            for identifier, t in bindings:
                new_context = {**new_context, **{identifier: None}}
                new_context = {**new_context, **decorate_context_for_lecrec(t, context=context)}
            return {**new_context, **decorate_context_for_lecrec(body, context=context)}

        case LetRec(bindings=bindings, body=body):
            new_context = {**context}
            for identifier, t in bindings:
                new_context = {**new_context, **{identifier: None}}
                new_context = {**new_context, **decorate_context_for_lecrec(t, context=context)}
            return {**new_context, **decorate_context_for_lecrec(body, context=context)}

        case Reference():
            pass

        case Abstract(parameters=parameters, body=body):
            new_context = {**context, **{parameter: None for parameter in parameters}}
            return {**new_context, **decorate_context_for_lecrec(body, context=context)}

        case Apply(target=target, arguments=arguments):
            new_context = {**context, **decorate_context_for_lecrec(target, context=context)}
            for argument in arguments:
                new_context = {**new_context, **decorate_context_for_lecrec(argument, context=context)}
            return new_context

        case Immediate(value=value):
            pass

        case Primitive(operator=_operator, left=left, right=right):
            return {
                **context,
                **decorate_context_for_lecrec(left, context=context),
                **decorate_context_for_lecrec(right, context=context),
            }

        case Branch(operator=_operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            new_context = {
                **context,
                **decorate_context_for_lecrec(left, context=context),
                **decorate_context_for_lecrec(right, context=context),
            }
            return {
                **new_context,
                **decorate_context_for_lecrec(consequent, context=context),
                **decorate_context_for_lecrec(otherwise, context=context),
            }

        case Allocate():
            pass

        case Load(base=base):
            return {**context, **decorate_context_for_lecrec(base, context=context)}

        case Store(base=base, value=value):
            return {
                **context,
                **decorate_context_for_lecrec(base, context=context),
                **decorate_context_for_lecrec(value, context=context),
            }

        case Begin(effects=effects, value=value):  # pragma: no branch
            new_context = {**context}
            for effect in effects:
                new_context = {**new_context, **decorate_context_for_lecrec(effect, context=context)}
            return {**new_context, **decorate_context_for_lecrec(value, context=context)}

    return context
