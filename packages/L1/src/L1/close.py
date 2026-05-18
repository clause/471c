from functools import partial
from typing import Callable

from L0 import syntax as L0

from . import syntax as L1


def free_variables(statement: L1.Statement) -> set[L1.Identifier]:
    match statement:
        case L1.Copy(destination=destination, source=source, then=then):
            return ({source} | free_variables(then)) - {destination}
        case L1.Abstract(destination=destination, parameters=parameters, body=body, then=then):
            return (free_variables(body) - set(parameters) | free_variables(then)) - {destination}
        case L1.Apply(target=target, arguments=arguments):
            return {target} | set(arguments)
        case L1.Immediate(destination=destination, then=then):
            return free_variables(then) - {destination}
        case L1.Primitive(destination=destination, left=left, right=right, then=then):
            return ({left, right} | free_variables(then)) - {destination}
        case L1.Branch(left=left, right=right, then=then, otherwise=otherwise):
            return {left, right} | free_variables(then) | free_variables(otherwise)
        case L1.Allocate(destination=destination, then=then):
            return free_variables(then) - {destination}
        case L1.Load(destination=destination, base=base, then=then):
            return {base} | free_variables(then) - {destination}
        case L1.Store(base=base, value=value, then=then):
            return {base, value} | free_variables(then)
        case L1.Halt(value=value):
            return {value}
        case _:  # pragma: no cover
            return set()


def close_term(
    statement: L1.Statement,
    lift: Callable[[L0.Procedure], None],
    fresh: Callable[[str], str],
) -> L0.Statement:
    recur = partial(close_term, lift=lift, fresh=fresh)  # noqa: F841

    match statement:
        case L1.Copy(destination=destination, source=source, then=then):
            return L0.Copy(
                destination=destination,
                source=source,
                then=recur(then),
            )

        case L1.Abstract(destination=destination, parameters=parameters, body=body, then=then):
            # 1. Close the abstract / lift to top level
            name = fresh("proc")
            env_p = fresh("env")

            fvs = list(free_variables(body) - set(parameters))

            result = recur(body)
            for i, fv in enumerate(fvs):
                result = L0.Load(
                    destination=fv,
                    base=env_p,
                    index=i,
                    then=result,
                )

            lift(
                L0.Procedure(
                    name=name,
                    parameters=[*parameters, env_p],
                    body=result,
                )
            )

            # 2. Create the closure (tuple of code and environment)
            env = fresh("env")
            code = fresh("code")
            result = L0.Address(
                destination=code,
                name=name,
                then=L0.Allocate(
                    destination=destination,
                    count=2,
                    then=L0.Store(
                        base=destination,
                        index=0,
                        value=code,
                        then=L0.Store(
                            base=destination,
                            index=1,
                            value=env,
                            then=recur(then),
                        ),
                    ),
                ),
            )

            for i, fv in enumerate(fvs):
                result = L0.Store(
                    base=env,
                    index=i,
                    value=fv,
                    then=result,
                )

            return L0.Allocate(
                destination=env,
                count=len(fvs),
                then=result,
            )

        case L1.Apply(target=target, arguments=arguments):
            # 1. Seperate code and environment from the closure
            # 2. Call the code with the argument and environment
            code = fresh("code")
            env = fresh("env")
            return L0.Load(
                destination=code,
                base=target,
                index=0,
                then=L0.Load(
                    destination=env,
                    base=target,
                    index=1,
                    then=L0.Call(
                        target=code,
                        arguments=[*arguments, env],
                    ),
                ),
            )

        case L1.Immediate(destination=destination, value=value, then=then):
            return L0.Immediate(
                destination=destination,
                value=value,
                then=recur(then),
            )

        case L1.Primitive(destination=destination, left=left, right=right, operator=operator, then=then):
            return L0.Primitive(
                destination=destination,
                left=left,
                right=right,
                operator=operator,
                then=recur(then),
            )

        case L1.Branch(left=left, right=right, operator=operator, then=then, otherwise=otherwise):
            return L0.Branch(
                left=left,
                right=right,
                operator=operator,
                then=recur(then),
                otherwise=recur(otherwise),
            )

        case L1.Allocate(destination=destination, count=count, then=then):
            return L0.Allocate(
                destination=destination,
                count=count,
                then=recur(then),
            )

        case L1.Load(destination=destination, base=base, index=index, then=then):
            return L0.Load(
                destination=destination,
                base=base,
                index=index,
                then=recur(then),
            )

        case L1.Store(base=base, index=index, value=value, then=then):
            return L0.Store(
                base=base,
                index=index,
                value=value,
                then=recur(then),
            )

        case L1.Halt(value=value):  # pragma: no branch
            return L0.Halt(value=value)


def close_program(program: L1.Program, fresh: Callable[[str], str]) -> L0.Program:
    match program:
        case L1.Program(parameters=parameters, body=body):  # pragma: no branch
            procedures = list[L0.Procedure]()

            body = close_term(
                body,
                procedures.append,
                fresh,
            )
            return L0.Program(
                procedures=[
                    *procedures,
                    L0.Procedure(
                        name="l0",
                        parameters=parameters,
                        body=body,
                    ),
                ],
            )
