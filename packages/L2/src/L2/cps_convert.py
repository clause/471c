from collections.abc import Callable, Sequence
from functools import partial

from L1 import syntax as L1

from L2 import syntax as L2


def cps_convert_term(
    term: L2.Term,
    k: Callable[[L1.Identifier], L1.Statement],
    fresh: Callable[[str], str],
) -> L1.Statement:
    _term = partial(cps_convert_term, fresh=fresh)
    _terms = partial(cps_convert_terms, fresh=fresh)

    match term:
        case L2.Let(bindings=bindings, body=body):

            def sequence_bindings(bs):
                if not bs:
                    return _term(body, k)
                (name, term_), *rest = bs
                return _term(
                    term_,
                    lambda v, n=name, r=rest: L1.Copy(
                        destination=n,
                        source=v,
                        then=sequence_bindings(r),
                    ),
                )

            return sequence_bindings(bindings)

        case L2.Reference(name=name):
            return k(name)

        case L2.Abstract(parameters=parameters, body=body):
            t = fresh("t")
            kp = fresh("k")
            return L1.Abstract(
                destination=t,
                parameters=[*parameters, kp],
                body=_term(body, lambda v, kp=kp: L1.Apply(target=kp, arguments=[v])),
                then=k(t),
            )

        case L2.Apply(target=target, arguments=arguments):
            kp = fresh("k")
            t = fresh("t")

            def after_target(tgt, kp=kp, t=t):
                def after_args(args, kp=kp, t=t, tgt=tgt):
                    return L1.Abstract(
                        destination=kp,
                        parameters=[t],
                        body=k(t),
                        then=L1.Apply(target=tgt, arguments=[*args, kp]),
                    )

                return _terms(arguments, after_args)

            return _term(target, after_target)

        case L2.Immediate(value=value):
            t = fresh("t")
            return L1.Immediate(destination=t, value=value, then=k(t))

        case L2.Primitive(operator=operator, left=left, right=right):

            def after_left(l, op=operator, r=right):
                def after_right(rv, op=op, l=l):
                    t = fresh("t")
                    return L1.Primitive(destination=t, operator=op, left=l, right=rv, then=k(t))

                return _term(r, after_right)

            return _term(left, after_left)

        case L2.Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            j = fresh("j")
            t = fresh("t")

            def after_left(l, op=operator, r=right, cons=consequent, other=otherwise, j=j, t=t):
                def after_right(rv, op=op, l=l, cons=cons, other=other, j=j, t=t):
                    def after_cons(c, op=op, l=l, rv=rv, other=other, j=j, t=t):
                        def after_other(o, op=op, l=l, rv=rv, c=c, j=j, t=t):
                            return L1.Abstract(
                                destination=j,
                                parameters=[t],
                                body=k(t),
                                then=L1.Branch(
                                    operator=op,
                                    left=l,
                                    right=rv,
                                    then=L1.Apply(target=j, arguments=[c]),
                                    otherwise=L1.Apply(target=j, arguments=[o]),
                                ),
                            )

                        return _term(other, after_other)

                    return _term(cons, after_cons)

                return _term(r, after_right)

            return _term(left, after_left)

        case L2.Allocate(count=count):
            t = fresh("t")
            return L1.Allocate(destination=t, count=count, then=k(t))

        case L2.Load(base=base, index=index):

            def after_base(b, idx=index):
                t = fresh("t")
                return L1.Load(destination=t, base=b, index=idx, then=k(t))

            return _term(base, after_base)

        case L2.Store(base=base, index=index, value=value):

            def after_base(b, idx=index, val=value):
                def after_value(v, b=b, idx=idx):
                    t = fresh("t")
                    return L1.Store(
                        base=b,
                        index=idx,
                        value=v,
                        then=L1.Immediate(destination=t, value=0, then=k(t)),
                    )

                return _term(val, after_value)

            return _term(base, after_base)

        case L2.Begin(effects=effects, value=value):  # pragma: no branch

            def sequence_effects(effs):
                if not effs:
                    return _term(value, k)
                first, *rest = effs
                return _term(first, lambda _, r=rest: sequence_effects(r))

            return sequence_effects(effects)


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
