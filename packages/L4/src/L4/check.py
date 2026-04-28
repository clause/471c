from collections.abc import Mapping
from functools import partial

from .syntax import (
    Abstraction,
    And,
    Application,
    Arrow,
    Bool,
    Boolean,
    Branch,
    Identifier,
    If,
    Immediate,
    Int,
    Join,
    Primitive,
    Product,
    Program,
    Project,
    Reference,
    Sole,
    Term,
    Trivial,
    Tuple,
    TupleGet,
    Type,
)


def equivalent(
    t1: Type,
    t2: Type,
) -> bool:
    recur = partial(equivalent)

    match t1, t2:
        case Arrow(domain=d1, codomain=c1), Arrow(domain=d2, codomain=c2):
            return (
                recur(d1, d2)  # domain
                and recur(c1, c2)  # codomain
            )

        case Int(), Int():
            return True

        case Bool(), Bool():
            return True

        case Trivial(), Trivial():
            return True

        case Product(components=cs1), Product(components=cs2):
            return (
                len(cs1) == len(cs2)  #
                and all(recur(c1, c2) for c1, c2 in zip(cs1, cs2))  #
            )

        case _:
            return False


def check_term(
    term: Term,
    expected: Type,
    gamma: Mapping[Identifier, Type],
) -> Type:
    infer = partial(infer_term, gamma=gamma)

    actual = infer(term)
    if not equivalent(actual, expected):
        raise ValueError()

    return actual


def infer_term(
    term: Term,
    gamma: Mapping[Identifier, Type],
) -> Type:
    _infer = partial(infer_term, gamma=gamma)
    _check = partial(check_term, gamma=gamma)

    match term:
        case Reference(name=name):
            match gamma.get(name):
                case None:
                    raise ValueError(f"unknown variable: {name}")

                case type:
                    return type

        case Abstraction(parameter=parameter, domain=domain, body=body):
            return Arrow(
                domain=domain,
                codomain=_infer(body, gamma={**gamma, parameter: domain}),
            )

        case Application(target=target, argument=argument):
            match _infer(target):
                case Arrow(domain=domain, codomain=codomain):
                    _check(argument, domain)
                    return codomain

                case target_type:
                    raise ValueError(f"expected {target} to be {Arrow} not {target_type}")

        case Immediate():
            return Int()

        case Boolean():
            return Bool()

        case Primitive(operator=operator, left=left, right=right):
            match operator:
                case "+" | "-" | "*":
                    _check(left, Int())
                    _check(right, Int())
                    return Int()

        case Branch(
            operator=operator, left=left, right=right, motive=motive, consequent=consequent, otherwise=otherwise
        ):
            match operator:
                case "<" | "==":
                    _check(left, Int())
                    _check(right, Int())
                    _check(consequent, motive)
                    _check(otherwise, motive)
                    return motive

        case If(test=test, consequent=consequent, otherwise=otherwise):
            _check(test, Bool())
            consequent_type = _infer(consequent)
            otherwise_type = _infer(otherwise)
            if not equivalent(consequent_type, otherwise_type):
                raise ValueError(f"branches have different types: {consequent_type} and {otherwise_type}")
            return consequent_type

        case And(left=left, right=right):
            _check(left, Bool())
            _check(right, Bool())
            return Bool()

        case Sole():
            return Trivial()

        case Tuple(components=components):
            return Product(components=[_infer(component) for component in components])

        case TupleGet(target=target, index=index):
            match _infer(target):
                case Product(components=components):
                    if index not in range(len(components)):
                        raise ValueError(f"invalid index: {index} in {components}")
                    return components[index]

                case target_type:
                    raise ValueError(f"expected {target} to be {Product} not {target_type}")

        case Join(components=components):
            return Product(components=[_infer(component) for component in components])

        case Project(target=target, index=index):
            match _infer(target):
                case Product(components=components):
                    if index not in range(len(components)):
                        raise ValueError(f"invalid index: {index} in {components}")

                    return components[index]

                case target_type:
                    raise ValueError(f"expected {target} to be {Product} not {target_type}")


def check_program(
    program: Program,
) -> None:
    match program:
        case Program(parameters=parameters, body=body):  # pragma: no branch
            check_term(body, Int(), dict.fromkeys(parameters, Int()))
