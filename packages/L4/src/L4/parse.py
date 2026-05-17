from collections.abc import Sequence
from typing import Literal, cast
from pathlib import Path

from lark import Lark, Token, Transformer
from lark.visitors import v_args  # pyright: ignore[reportUnknownVariableType]

from .syntax import (
    Abstraction,
    And,
    Application,
    Identifier,
    If,
    Immediate,
    Int,
    Join,
    Primitive,
    Program,
    Project,
    Reference,
    Sole,
    Term,
    Tuple,
    TupleGet,
)


class AstTransformer(Transformer[Token, Program | Term]):
    @v_args(inline=True)
    def program(
        self,
        _program: Token,
        parameters: Sequence[Identifier],
        body: Term,
    ) -> Program:
        return Program(parameters=parameters, body=body)

    def parameters(self, parameters: Sequence[Token]) -> Sequence[Identifier]:
        return [str(parameter) for parameter in parameters]

    @v_args(inline=True)
    def term(self, term: Term) -> Term:
        return term

    @v_args(inline=True)
    def let(self, _let: Token, bindings: Sequence[tuple[Identifier, Term]], body: Term) -> Term:
        from .syntax import Let

        return Let(bindings=bindings, body=body)

    def bindings(self, bindings: Sequence[tuple[Identifier, Term]]) -> Sequence[tuple[Identifier, Term]]:
        return bindings

    @v_args(inline=True)
    def binding(self, name: Token, value: Term) -> tuple[Identifier, Term]:
        return str(name), value

    @v_args(inline=True)
    def reference(self, name: Token) -> Term:
        return Reference(name=str(name))

    @v_args(inline=True)
    def abstract(self, _lambda: Token, parameters: Sequence[Identifier], body: Term) -> Term:
        if len(parameters) != 1:
            raise ValueError("lambda expects exactly one parameter")

        return Abstraction(parameter=parameters[0], domain=Int(), body=body)

    def apply(self, args: Sequence[Term]) -> Term:
        terms = list(args)
        if len(terms) == 0:
            raise ValueError("application requires at least one term")

        target = terms[0]
        for argument in terms[1:]:
            target = Application(target=target, argument=argument)

        return target

    @v_args(inline=True)
    def immediate(self, value: Token) -> Term:
        return Immediate(value=int(value))

    @v_args(inline=True)
    def primitive(self, operator: Token, left: Term, right: Term) -> Term:
        op = cast(Literal["+", "-", "*"], str(operator))
        return Primitive(operator=op, left=left, right=right)

    @v_args(inline=True)
    def if_expr(self, _if: Token, test: Term, consequent: Term, otherwise: Term) -> Term:
        return If(test=test, consequent=consequent, otherwise=otherwise)

    @v_args(inline=True)
    def and_expr(self, _and: Token, left: Term, right: Term) -> Term:
        return And(left=left, right=right)

    @v_args(inline=True)
    def sole_expr(self, _sole: Token) -> Term:
        return Sole()

    def tuple_expr(self, components: Sequence[Term]) -> Term:
        return Tuple(components=components)

    @v_args(inline=True)
    def tuple_get_expr(self, _tuple_get: Token, target: Term, index: Immediate) -> Term:
        return TupleGet(target=target, index=index.value)

    def join_expr(self, components: Sequence[Term]) -> Term:
        return Join(components=components)

    @v_args(inline=True)
    def project_expr(self, _project: Token, target: Term, index: Immediate) -> Term:
        return Project(target=target, index=index.value)


def parse_term(source: str) -> Term:
    grammar = Path(__file__).with_name("L4.lark").read_text()
    parser = Lark(grammar, start="term")
    tree = parser.parse(source)  # pyright: ignore[reportUnknownMemberType]
    return AstTransformer().transform(tree)  # pyright: ignore[reportReturnType]


def parse_program(source: str) -> Program:
    grammar = Path(__file__).with_name("L4.lark").read_text()
    parser = Lark(grammar, start="program")
    tree = parser.parse(source)  # pyright: ignore[reportUnknownMemberType]
    return AstTransformer().transform(tree)  # pyright: ignore[reportReturnType]
