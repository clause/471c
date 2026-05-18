# noqa: F841
from collections.abc import Mapping

from L2 import syntax as L2

from . import syntax as L3

type Context = Mapping[L3.Identifier, None]


def eliminate_letrec_term(
    term: L3.Term,
    context: Context,
) -> L2.Term:
    match term:
        case L3.Let(bindings=bindings, body=body):
            return L2.Let(
                bindings=[(name, eliminate_letrec_term(value, context)) for name, value in bindings],
                body=eliminate_letrec_term(body, context),
            )

        case L3.LetRec(bindings=bindings, body=body):
            # Mark all binding names as recursive in the context
            binding_names = [name for name, _ in bindings]
            new_context: Context = {**context, **dict.fromkeys(binding_names)}  # type: ignore

            # Check which bindings need heap allocation based on their values
            # Simple values (Immediate, Allocate) can be stored directly
            # Complex values (everything else) need Allocate + Store
            simple_binding_indices: set[int] = set()
            for i, (_, value) in enumerate(bindings):
                match value:
                    case L3.Immediate() | L3.Allocate():
                        simple_binding_indices.add(i)
                    case _:
                        pass

            # Separate simple and complex bindings
            simple_bindings: list[tuple[str, L2.Term]] = []
            complex_bindings: list[tuple[str, L3.Term]] = []
            complex_binding_names: list[str] = []

            for i, (name, value) in enumerate(bindings):
                if i in simple_binding_indices:
                    transformed_value = eliminate_letrec_term(value, new_context)
                    simple_bindings.append((name, transformed_value))
                else:
                    complex_bindings.append((name, value))
                    complex_binding_names.append(name)

            # Create stores for complex bindings
            stores: list[L2.Term] = []
            for name, value in complex_bindings:
                transformed_value = eliminate_letrec_term(value, new_context)
                stores.append(
                    L2.Store(
                        base=L2.Reference(name=name),
                        index=0,
                        value=transformed_value,
                    )
                )

            # Transform the body
            transformed_body = eliminate_letrec_term(body, new_context)

            # Build the result
            all_bindings = simple_bindings + [(name, L2.Allocate(count=1)) for name in complex_binding_names]

            if stores:
                return L2.Let(
                    bindings=all_bindings,
                    body=L2.Begin(
                        effects=stores,
                        value=transformed_body,
                    ),
                )
            else:
                return L2.Let(
                    bindings=all_bindings,
                    body=transformed_body,
                )

        case L3.Reference(name=name):
            # if name is a recursive variable -> (Load (Reference name)))
            # else (Reference name)
            if name in context:
                return L2.Load(base=L2.Reference(name=name), index=0)
            else:
                return L2.Reference(name=name)

        case L3.Abstract(parameters=parameters, body=body):
            return L2.Abstract(parameters=parameters, body=eliminate_letrec_term(body, context))

        case L3.Apply(target=target, arguments=arguments):
            return L2.Apply(
                target=eliminate_letrec_term(target, context),
                arguments=[eliminate_letrec_term(argument, context) for argument in arguments],
            )

        case L3.Immediate(value=value):
            return L2.Immediate(value=value)

        case L3.Primitive(operator=operator, left=left, right=right):
            return L2.Primitive(
                operator=operator,
                left=eliminate_letrec_term(left, context),
                right=eliminate_letrec_term(right, context),
            )

        case L3.Branch(operator=operator, left=left, right=right, consequent=consequent, otherwise=otherwise):
            return L2.Branch(
                operator=operator,
                left=eliminate_letrec_term(left, context),
                right=eliminate_letrec_term(right, context),
                consequent=eliminate_letrec_term(consequent, context),
                otherwise=eliminate_letrec_term(otherwise, context),
            )

        case L3.Allocate(count=count):
            return L2.Allocate(count=count)

        case L3.Load(base=base, index=index):
            return L2.Load(
                base=eliminate_letrec_term(base, context),
                index=index,
            )

        case L3.Store(base=base, index=index, value=value):
            return L2.Store(
                base=eliminate_letrec_term(base, context),
                index=index,
                value=eliminate_letrec_term(value, context),
            )

        case L3.Begin(effects=effects, value=value):  # pragma: no branch
            return L2.Begin(
                effects=[eliminate_letrec_term(effect, context) for effect in effects],
                value=eliminate_letrec_term(value, context),
            )


def eliminate_letrec_program(
    program: L3.Program,
) -> L2.Program:
    match program:
        case L3.Program(parameters=parameters, body=body):  # pragma: no branch
            return L2.Program(
                parameters=parameters,
                body=eliminate_letrec_term(body, {}),
            )
