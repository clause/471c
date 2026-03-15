from functools import partial

from .syntax import (
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Immediate,
    Let,
    Load,
    Primitive,
    Reference,
    Store,
    Term,
)
from .util import (
    Context,
    extend_context_with_bindings,
    recur_terms,
)


def constant_propogation_term(
    term: Term,
    context: Context,
) -> Term:
    recur = partial(constant_propogation_term, context=context)

    match term:
        case Let(bindings=bindings, body=body):
            new_bindings, new_context = extend_context_with_bindings(bindings, context, recur)
            return Let(
                bindings=new_bindings,
                body=constant_propogation_term(body, new_context),
            )

        case Reference(name=name):
            if name in context:
                return context[name]
            return term

        case Abstract(parameters=parameters, body=body):
            abstract_context = {name: value for name, value in context.items() if name not in parameters}
            return Abstract(
                parameters=parameters,
                body=constant_propogation_term(body, abstract_context),
            )

        case Apply(target=target, arguments=arguments):
            return Apply(
                target=recur(target),
                arguments=recur_terms(arguments, recur),
            )

        case Immediate(value=_value):
            return term

        case Primitive(operator=operator, left=left, right=right):
            return Primitive(
                operator=operator,
                left=recur(left),
                right=recur(right),
            )

        case Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            return Branch(
                operator=operator,
                left=recur(left),
                right=recur(right),
                consequent=recur(consequent),
                otherwise=recur(otherwise),
            )

        case Allocate(count=count):
            return Allocate(count=count)

        case Load(base=base, index=index):
            return Load(base=recur(base), index=index)

        case Store(base=base, index=index, value=value):
            return Store(base=recur(base), index=index, value=recur(value))

        case Begin(effects=effects, value=value):  # pragma: no branch
            return Begin(
                effects=recur_terms(effects, recur),
                value=recur(value),
            )
