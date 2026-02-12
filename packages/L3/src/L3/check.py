from collections.abc import Mapping
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
    LetRec,
    Load,
    Primitive,
    Reference,
    Store,
    Term,
)

type Context = Mapping[Identifier, None]


def check_term(
    term: Term,
    context: Context,
) -> None:
    """
    Perform a lightweight static semantic check over an L3 AST term.

    What it checks:
    - Unbound variable use:
        * Any `Reference(name=...)` must appear in `context`, otherwise raise ValueError.
    - Duplicate bindings / shadowing disallowed:
        * `Let` cannot bind the same identifier twice (and cannot reuse an identifier already in scope).
        * `LetRec` cannot bind the same identifier twice (and cannot reuse an identifier already in scope).
        * `Abstract` cannot have duplicate parameters (and cannot reuse an identifier already in scope).
      (This matches the intended lowering strategy where reusing names may break semantics.)

    What it does NOT check:
    - Types, arity, operator validity, memory bounds, etc.
      It only ensures that variable binding structure is well-formed.

    Traversal strategy:
    - Structural recursion: recursively visits sub-terms to ensure checks apply everywhere.
    - `recur` is a convenience wrapper that reuses the same `context`.
    """
    recur = partial(check_term, context=context)

    match term:
        case Let(bindings=bindings, body=body):
            # Let introduces new bindings sequentially:
            # - Each RHS is checked under the context extended by previous bindings in the same let.
            ctx: dict[Identifier, None] = dict(context)
            for name, value in bindings:
                check_term(value, ctx)
                if name in ctx:
                    raise ValueError(f"duplicate binding (shadowing not allowed): {name!r}")
                ctx[name] = None
            check_term(body, ctx)

        case LetRec(bindings=bindings, body=body):
            # LetRec supports recursion:
            # - First pre-bind all names (so functions can refer to each other),
            # - Then check each RHS in the extended context.
            ctx: dict[Identifier, None] = dict(context)
            for name, _value in bindings:
                if name in ctx:
                    raise ValueError(f"duplicate binding (shadowing not allowed): {name!r}")
                ctx[name] = None

            for _name, value in bindings:
                check_term(value, ctx)

            check_term(body, ctx)

        case Reference(name=name):
            # A reference is valid only if the identifier is already bound in `context`.
            if name not in context:
                raise ValueError(f"unbound identifier: {name!r}")

        case Abstract(parameters=parameters, body=body):
            # Abstract (lambda) introduces parameter bindings.
            # This checker disallows duplicates/shadowing for simplicity and to match lowering assumptions.
            ctx: dict[Identifier, None] = dict(context)
            for p in parameters:
                if p in ctx:
                    raise ValueError(f"duplicate binding (shadowing not allowed): {p!r}")
                ctx[p] = None
            check_term(body, ctx)

        case Apply(target=target, arguments=arguments):
            # Check the function position and then all argument terms.
            recur(target)
            for arg in arguments:
                recur(arg)

        case Immediate():
            # Literal immediates (e.g., integers) have no binding constraints.
            return

        case Primitive(left=left, right=right):
            # Primitive operations recursively check their operands.
            recur(left)
            recur(right)

        case Branch(left=left, right=right, consequent=consequent, otherwise=otherwise):
            # Branch checks its condition operands and both result branches.
            recur(left)
            recur(right)
            recur(consequent)
            recur(otherwise)

        case Allocate():
            # Allocation count is assumed validated elsewhere; nothing to bind-check.
            return

        case Load(base=base):
            # Loading from memory: base term must be semantically valid.
            recur(base)

        case Store(base=base, value=value):
            # Storing to memory: both base and stored value must be semantically valid.
            recur(base)
            recur(value)

        case Begin(effects=effects, value=value):  # pragma: no branch
            # Begin sequences effect terms then returns value term.
            for eff in effects:
                recur(eff)
            recur(value)
