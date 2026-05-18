from collections.abc import Sequence
from pathlib import Path
from typing import Literal, cast

from lark import Lark, Token, Transformer
from lark.visitors import v_args  # pyright: ignore[reportUnknownVariableType]

from .syntax import (
    Abstraction,
    And,
    Application,
    Arrow,
    Bool,
    Boolean,
    Box,
    BoxRead,
    BoxWrite,
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

    # --- Types ---

    @v_args(inline=True)
    def int_type(self) -> Type:
        return Int()

    @v_args(inline=True)
    def bool_type(self) -> Type:
        return Bool()

    @v_args(inline=True)
    def trivial_type(self) -> Type:
        return Trivial()

    @v_args(inline=True)
    def arrow_type(self, domain: Type, codomain: Type) -> Type:
        return Arrow(domain=domain, codomain=codomain)

    def product_type(self, args: Sequence[Type]) -> Type:
        return Product(components=[component for component in args])

    @v_args(inline=True)
    def box_type(self, content: Type) -> Type:
        return Box(content=content)

    # --- Terms ---

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
    def abstract(self, _lambda: Token, parameter: Token, _colon: Token, domain: Type, body: Term) -> Term:
        # domain is now parsed from the type annotation, e.g. (λ x : Int body)
        return Abstraction(parameter=str(parameter), domain=domain, body=body)

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
    def boolean(self, value: Token) -> Term:
        # Lark gives us the token "true" or "false" as a string
        return Boolean(value=str(value) == "true")

    @v_args(inline=True)
    def primitive(self, operator: Token, left: Term, right: Term) -> Term:
        op = cast(Literal["+", "-", "*"], str(operator))
        return Primitive(operator=op, left=left, right=right)

    @v_args(inline=True)
    def branch(
        self,
        _if: Token,
        operator: Token,
        left: Term,
        right: Term,
        motive: Type,
        consequent: Term,
        otherwise: Term,
    ) -> Term:
        # Branch: (if (< left right) motive consequent otherwise)
        op = cast(Literal["<", "=="], str(operator))
        return Branch(
            operator=op,
            left=left,
            right=right,
            motive=motive,
            consequent=consequent,
            otherwise=otherwise,
        )

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

    @v_args(inline=True)
    def box_write_expr(self, _box_write: Token, target: Term, value: Term) -> Term:
        return BoxWrite(target=target, value=value)

    @v_args(inline=True)
    def box_read_expr(self, _box_read: Token, target: Term) -> Term:
        return BoxRead(target=target)


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
