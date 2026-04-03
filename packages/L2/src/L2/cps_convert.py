from collections.abc import Callable, Sequence
from functools import partial

from L1 import syntax as L1

from L2 import syntax as L2


def cps_convert_term(
    term: L2.Term,
    m: Callable[[L1.Identifier], L1.Statement],
    fresh: Callable[[str], str],
) -> L1.Statement:
    _term = partial(cps_convert_term, fresh=fresh)
    _terms = partial(cps_convert_terms, fresh=fresh)

    match term:
        case L2.Let(bindings=bindings, body=body):
            result = _term(body, m)

            for name, value in reversed(bindings):
                result = _term(value, lambda value: L1.Copy(destination=name, source=value, then=result))

            return result

        case L2.Reference(name=name):
            return m(name)

        case L2.Abstract(parameters=parameters, body=body):
            tmp = fresh("t")
            k = fresh("k")
            L1.Abstract(
                destination=tmp,
                parameters=[*parameters, k],
                body=_term(body, lambda body: L1.Apply(target=k, arguments=[body])),
                then=m(tmp),
            )

        case L2.Apply(target=target, arguments=arguments):
            k = fresh("k")
            tmp = fresh("t")
            return L1.Abstract(
                destination=k,
                parameters=[tmp],
                body=m(tmp),
                then=_term(
                    target,
                    lambda target: _terms(
                        arguments,
                        lambda arguments: L1.Apply(target=target, arguments=[*arguments, k]),
                    ),
                ),
            )

        case L2.Immediate(value=value):
            tmp = fresh("t")
            return L1.Immediate(destination=tmp, value=value, then=m(tmp))

        case L2.Primitive(operator=operator, left=left, right=right):
            tmp = fresh("t")
            return _term(
                left,
                lambda left: _term(
                    right,
                    lambda right: L1.Primitive(destination=tmp, operator=operator, left=left, right=right, then=m(tmp)),
                ),
            )

        case L2.Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            return _term(
                left,
                lambda left: _term(
                    right,
                    lambda right: L1.Branch(
                        operator=operator,
                        left=left,
                        right=right,
                        then=_term(consequent, lambda consequent: L1.Apply()),
                        otherwise=_term(otherwise, m),
                    ),
                ),
            )

        case L2.Allocate(count=count):
            tmp = fresh("t")
            return L1.Allocate(destination=tmp, count=count, then=m(tmp))

        case L2.Load(base=base, index=index):
            tmp = fresh("t")
            return _term(
                base,
                lambda base: L1.Load(destination=tmp, base=base, index=index, then=m(tmp)),
            )

        # Should double check this
        case L2.Store(base=base, index=index, value=value):
            tmp = fresh("t")
            return _term(
                base,
                lambda base: _term(
                    value,
                    lambda value: L1.Store(
                        base=base, index=index, value=value, then=L1.Immediate(destination=tmp, value=0, then=m(tmp))
                    ),
                ),
            )

        case L2.Begin(effects=effects, value=value):  # pragma: no branch
            return _terms(
                effects,
                lambda effects: _term(
                    value,
                    lambda value: m(value),
                ),
            )


def cps_convert_terms(
    terms: Sequence[L2.Term],
    k: Callable[[Sequence[L1.Identifier]], L1.Statement],
    fresh: Callable[[str], str],
) -> L1.Statement:
    _term = partial(cps_convert_term, fresh=fresh)
    _terms = partial(cps_convert_terms, fresh=fresh)

    match terms:
        case []:
            return k([])

        case [first, *rest]:
            return _term(first, lambda first: _terms(rest, lambda rest: k([first, *rest])))

        case _:  # pragma: no cover
            raise ValueError(terms)


def cps_convert_program(
    program: L2.Program,
    fresh: Callable[[str], str],
) -> L1.Program:
    _term = partial(cps_convert_term, fresh=fresh)

    match program:
        case L2.Program(parameters=parameters, body=body):  # pragma: no branch
            return L1.Program(
                parameters=parameters,
                body=_term(body, lambda value: L1.Halt(value=value)),
            )
