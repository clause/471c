from collections.abc import Callable
from functools import partial

from L3 import syntax as L3
from util.sequential_name_generator import SequentialNameGenerator

from . import syntax as L4

type FreshFunc = Callable[[str], str]


def elaborate_term(term: L4.Term, fresh: FreshFunc) -> L3.Term:
    recur = partial(elaborate_term, fresh=fresh)

    match term:
        case L4.Reference(name=name):
            return L3.Reference(name=name)

        case L4.Abstraction(parameter=parameter, domain=_domain, body=body):
            return L3.Abstract(
                parameters=[parameter],
                body=recur(body),
            )

        case L4.Application(target=target, argument=argument):
            return L3.Apply(
                target=recur(target),
                arguments=[recur(argument)],
            )

        case L4.Boolean(value=value):
            return L3.Immediate(value=1 if value else 0)

        case L4.If(test=test, consequent=consequent, otherwise=otherwise):
            test_name = fresh("if")
            return L3.Let(
                bindings=[(test_name, recur(test))],
                body=L3.Branch(
                    operator="==",
                    left=L3.Reference(name=test_name),
                    right=L3.Immediate(value=1),
                    consequent=recur(consequent),
                    otherwise=recur(otherwise),
                ),
            )

        case L4.And(left=left, right=right):
            left_name = fresh("and")
            return L3.Let(
                bindings=[(left_name, recur(left))],
                body=L3.Branch(
                    operator="==",
                    left=L3.Reference(name=left_name),
                    right=L3.Immediate(value=1),
                    consequent=recur(right),
                    otherwise=L3.Immediate(value=0),
                ),
            )

        case L4.Immediate(value=value):
            return L3.Immediate(value=value)

        case L4.Primitive(operator=operator, left=left, right=right):
            return L3.Primitive(
                operator=operator,
                left=recur(left),
                right=recur(right),
            )

        case L4.Branch(
            operator=operator, left=left, right=right, motive=_motive, consequent=consequent, otherwise=otherwise
        ):
            return L3.Branch(
                operator=operator,
                left=recur(left),
                right=recur(right),
                consequent=recur(consequent),
                otherwise=recur(otherwise),
            )

        case L4.Sole():
            return L3.Immediate(value=0)

        case L4.Tuple(components=components):
            tuple_name = fresh("tuple")
            return L3.Let(
                bindings=[(tuple_name, L3.Allocate(count=len(components)))],
                body=L3.Begin(
                    effects=[
                        L3.Store(
                            base=L3.Reference(name=tuple_name),
                            index=index,
                            value=recur(component),
                        )
                        for index, component in enumerate(components)
                    ],
                    value=L3.Reference(name=tuple_name),
                ),
            )

        case L4.TupleGet(target=target, index=index):
            tuple_name = fresh("tuple")
            return L3.Let(
                bindings=[(tuple_name, recur(target))],
                body=L3.Load(
                    base=L3.Reference(name=tuple_name),
                    index=index,
                ),
            )

        case L4.Join(components=components):
            return recur(L4.Tuple(components=components))

        case L4.Project(target=target, index=index):
            return recur(L4.TupleGet(target=target, index=index))

        case _:
            raise ValueError(f"unknown term for L4 elaboration: {term}")


def elaborate_program(program: L4.Program, fresh: FreshFunc | None = None) -> L3.Program:
    fresh = fresh or SequentialNameGenerator()

    match program:
        case L4.Program(parameters=parameters, body=body):
            return L3.Program(
                parameters=parameters,
                body=elaborate_term(body, fresh),
            )

        case _:
            raise ValueError(f"unknown program for L4 elaboration: {program}")
