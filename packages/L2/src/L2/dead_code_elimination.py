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
    Load,
    Primitive,
    Reference,
    Store,
    Term,
)
from .util import (
    Context,
    recur_terms,
)


def is_pure(term: Term) -> bool:
    match term:
        case Immediate():
            return True

        case Reference():
            return True

        case Primitive(left=left, right=right):
            return is_pure(left) and is_pure(right)

        case Abstract(body=body):
            return is_pure(body)

        case Let(bindings=bindings, body=body):
            return all(is_pure(value) for _, value in bindings) and is_pure(body)

        case Branch(left=left, right=right, consequent=consequent, otherwise=otherwise):
            return is_pure(left) and is_pure(right) and is_pure(consequent) and is_pure(otherwise)

        case Load(base=base):
            return is_pure(base)

        case Begin(effects=effects, value=value):
            return all(is_pure(effect) for effect in effects) and is_pure(value)

        case Apply():
            return False

        case Allocate():
            return False

        case Store():
            return False


def free_vars(term: Term) -> set[Identifier]:
    match term:
        case Immediate():
            return set()

        case Reference(name=name):
            return {name}

        case Primitive(left=left, right=right):
            return free_vars(left) | free_vars(right)

        case Apply(target=target, arguments=arguments):
            result = free_vars(target)
            for argument in arguments:
                result |= free_vars(argument)
            return result

        case Abstract(parameters=parameters, body=body):
            return free_vars(body) - set(parameters)

        case Branch(left=left, right=right, consequent=consequent, otherwise=otherwise):
            return free_vars(left) | free_vars(right) | free_vars(consequent) | free_vars(otherwise)

        case Load(base=base):
            return free_vars(base)

        case Store(base=base, value=value):
            return free_vars(base) | free_vars(value)

        case Begin(effects=effects, value=value):
            result = free_vars(value)
            for effect in effects:
                result |= free_vars(effect)
            return result

        case Allocate():
            return set()

        case Let(bindings=bindings, body=body):
            names = [name for name, _ in bindings]
            result = free_vars(body) - set(names)
            for _, value in bindings:
                result |= free_vars(value)
            return result


def dead_code_elimination_term(
    term: Term,
    context: Context,
) -> Term:
    recur = partial(dead_code_elimination_term, context=context)

    match term:
        case Let(bindings=bindings, body=body):
            new_values = [(name, recur(value)) for name, value in bindings]
            new_body = recur(body)

            live = free_vars(new_body)
            kept_reversed: list[tuple[Identifier, Term]] = []

            for name, value in reversed(new_values):
                if name in live or not is_pure(value):
                    kept_reversed.append((name, value))
                    live.discard(name)
                    live |= free_vars(value)

            kept = list(reversed(kept_reversed))
            if len(kept) == 0:
                return new_body

            return Let(bindings=kept, body=new_body)

        case Reference(name=_name):
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
            new_effects = [recur(effect) for effect in effects]
            kept_effects = [effect for effect in new_effects if not is_pure(effect)]
            new_value = recur(value)

            if len(kept_effects) == 0:
                return new_value

            return Begin(effects=kept_effects, value=new_value)
