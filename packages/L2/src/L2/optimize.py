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
    Program,
    Reference,
    Store,
    Term,
)

type Env = dict[str, Term]


def free_variables(term: Term) -> set[str]:
    match term:
        case Reference(name=name):
            return {name}
        case Immediate() | Allocate():
            return set()
        case Let(bindings=bindings, body=body):
            bound = {name for name, _ in bindings}
            result = free_variables(body) - bound
            for _, value in bindings:
                result |= free_variables(value)
            return result
        case Abstract(parameters=parameters, body=body):
            return free_variables(body) - set(parameters)
        case Apply(target=target, arguments=arguments):
            result = free_variables(target)
            for arg in arguments:
                result |= free_variables(arg)
            return result
        case Primitive(left=left, right=right):
            return free_variables(left) | free_variables(right)
        case Branch(left=left, right=right, consequent=consequent, otherwise=otherwise):
            return free_variables(left) | free_variables(right) | free_variables(consequent) | free_variables(otherwise)
        case Load(base=base):
            return free_variables(base)
        case Store(base=base, value=value):
            return free_variables(base) | free_variables(value)
        case Begin(effects=effects, value=value):
            result = free_variables(value)
            for effect in effects:
                result |= free_variables(effect)
            return result


def is_pure(term: Term) -> bool:
    match term:
        case Immediate() | Reference() | Abstract():
            return True
        case Primitive(left=left, right=right):
            return is_pure(left) and is_pure(right)
        case Branch(left=left, right=right, consequent=consequent, otherwise=otherwise):
            return is_pure(left) and is_pure(right) and is_pure(consequent) and is_pure(otherwise)
        case Let(bindings=bindings, body=body):
            return all(is_pure(v) for _, v in bindings) and is_pure(body)
        case Apply() | Allocate() | Load() | Store() | Begin():
            return False


def optimize_term(term: Term, env: Env) -> Term:
    match term:
        case Reference(name=name):
            return env.get(name, term)

        case Immediate() | Allocate():
            return term

        case Let(bindings=bindings, body=body):
            new_bindings: list[tuple[Identifier, Term]] = []
            new_env = dict(env)
            for name, value in bindings:
                opt_value = optimize_term(value, new_env)
                if isinstance(opt_value, (Immediate, Reference)):
                    # Constant: propagate into subsequent bindings and body
                    new_env[name] = opt_value
                else:
                    # Non-constant: keep as binding; shadow any outer constant for this name
                    new_bindings.append((name, opt_value))
                    new_env.pop(name, None)

            opt_body = optimize_term(body, new_env)

            # Dead code elimination: drop unused bindings whose values are pure
            final_bindings: list[tuple[Identifier, Term]] = []
            for i, (name, value) in enumerate(new_bindings):
                after_free = free_variables(opt_body)
                for _, later_value in new_bindings[i + 1 :]:
                    after_free |= free_variables(later_value)
                if name in after_free or not is_pure(value):
                    final_bindings.append((name, value))

            if not final_bindings:
                return opt_body
            return Let(bindings=final_bindings, body=opt_body)

        case Abstract(parameters=parameters, body=body):
            inner_env = {k: v for k, v in env.items() if k not in set(parameters)}
            return Abstract(
                parameters=parameters,
                body=optimize_term(body, inner_env),
            )

        case Apply(target=target, arguments=arguments):
            return Apply(
                target=optimize_term(target, env),
                arguments=[optimize_term(arg, env) for arg in arguments],
            )

        case Primitive(operator=op, left=left, right=right):
            opt_left = optimize_term(left, env)
            opt_right = optimize_term(right, env)
            if isinstance(opt_left, Immediate) and isinstance(opt_right, Immediate):
                match op:
                    case "+":
                        return Immediate(value=opt_left.value + opt_right.value)
                    case "-":
                        return Immediate(value=opt_left.value - opt_right.value)
                    case "*":
                        return Immediate(value=opt_left.value * opt_right.value)
            return Primitive(operator=op, left=opt_left, right=opt_right)

        case Branch(operator=op, left=left, right=right, consequent=consequent, otherwise=otherwise):
            opt_left = optimize_term(left, env)
            opt_right = optimize_term(right, env)
            opt_consequent = optimize_term(consequent, env)
            opt_otherwise = optimize_term(otherwise, env)
            if isinstance(opt_left, Immediate) and isinstance(opt_right, Immediate):
                match op:
                    case "<":
                        condition = opt_left.value < opt_right.value
                    case "==":
                        condition = opt_left.value == opt_right.value
                return opt_consequent if condition else opt_otherwise
            return Branch(
                operator=op,
                left=opt_left,
                right=opt_right,
                consequent=opt_consequent,
                otherwise=opt_otherwise,
            )

        case Load(base=base, index=index):
            return Load(base=optimize_term(base, env), index=index)

        case Store(base=base, index=index, value=value):
            return Store(
                base=optimize_term(base, env),
                index=index,
                value=optimize_term(value, env),
            )

        case Begin(effects=effects, value=value):
            return Begin(
                effects=[optimize_term(e, env) for e in effects],
                value=optimize_term(value, env),
            )


def optimize_program(program: Program) -> Program:
    body = program.body
    while True:
        optimized = optimize_term(body, {})
        if optimized == body:
            break
        body = optimized
    return Program(parameters=program.parameters, body=body)
