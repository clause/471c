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


def _normalize_commutative_immediate_left(
    operator: str,
    left: Term,
    right: Term,
) -> Primitive:
    return Primitive(
        operator=operator,  # type: ignore[arg-type]
        left=right,
        right=left,
    )


def constant_folding_term(
    term: Term,
    context: Context,
) -> Term:
    recur = partial(constant_folding_term, context=context)  # noqa: F841

    match term:
        case Let(bindings=bindings, body=body):
            new_bindings, new_context = extend_context_with_bindings(bindings, context, recur)
            return Let(
                bindings=new_bindings,
                body=constant_folding_term(body, new_context),
            )

        case Reference(name=name):
            if name in context:
                return context[name]
            return term

        case Abstract(parameters=parameters, body=body):
            return Abstract(parameters=parameters, body=recur(body))

        case Apply(target=target, arguments=arguments):
            return Apply(
                target=recur(target),
                arguments=recur_terms(arguments, recur),
            )

        case Immediate(value=_value):
            return term

        case Primitive(operator=operator, left=left, right=right):
            match operator:
                case "+":
                    match recur(left), recur(right):
                        case Immediate(value=i1), Immediate(value=i2):
                            return Immediate(value=i1 + i2)

                        case Immediate(value=0), right:
                            return right

                        case [
                            Primitive(operator="+", left=Immediate(value=i1), right=left),
                            Primitive(operator="+", left=Immediate(value=i2), right=right),
                        ]:
                            return Primitive(
                                operator="+",
                                left=Immediate(value=i1 + i2),
                                right=Primitive(
                                    operator="+",
                                    left=left,
                                    right=right,
                                ),
                            )

                        case left, Immediate() as right:
                            return _normalize_commutative_immediate_left("+", left, right)

                        case left, right:
                            return Primitive(
                                operator="+",
                                left=left,
                                right=right,
                            )

                case "-":
                    match recur(left), recur(right):
                        case Immediate(value=i1), Immediate(value=i2):
                            return Immediate(value=i1 - i2)

                        case left, right:
                            return Primitive(operator="-", left=left, right=right)

                case "*":
                    match recur(left), recur(right):
                        case Immediate(value=i1), Immediate(value=i2):
                            return Immediate(value=i1 * i2)

                        case Immediate(value=0), _:
                            return Immediate(value=0)

                        case _, Immediate(value=0):
                            return Immediate(value=0)

                        case Immediate(value=1), right:
                            return right

                        case left, Immediate(value=1):
                            return left

                        case left, Immediate() as right:
                            return _normalize_commutative_immediate_left("*", left, right)

                        case left, right:
                            return Primitive(operator="*", left=left, right=right)

        case Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            folded_left = recur(left)
            folded_right = recur(right)
            folded_consequent = recur(consequent)
            folded_otherwise = recur(otherwise)
            match operator:
                case "<":
                    match folded_left, folded_right:
                        case Immediate(value=i1), Immediate(value=i2):
                            return folded_consequent if i1 < i2 else folded_otherwise
                        case _:
                            pass
                case "==":
                    match folded_left, folded_right:
                        case Immediate(value=i1), Immediate(value=i2):
                            return folded_consequent if i1 == i2 else folded_otherwise
                        case _:
                            pass
            return Branch(
                operator=operator,
                left=folded_left,
                right=folded_right,
                consequent=folded_consequent,
                otherwise=folded_otherwise,
            )

        case Allocate(count=count):
            return Allocate(count=count)

        case Load(base=base, index=index):
            return Load(base=recur(base), index=index)

        case Store(base=base, index=index, value=value):
            return Store(base=recur(base), index=index, value=recur(value))

        case Begin(effects=effects, value=value):  # pragma: no branch
            return Begin(effects=recur_terms(effects, recur), value=recur(value))
