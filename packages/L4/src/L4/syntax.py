from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, Field

type Identifier = Annotated[str, Field(min_length=1)]
type Label = Annotated[str, Field(min_length=1)]
type Nat = Annotated[int, Field(ge=0)]


class Program(BaseModel, frozen=True):
    tag: Literal["program"] = "program"
    parameters: Sequence[Identifier]
    body: Term


type Type = Annotated[
    Arrow | Int | Bool | Trivial | Product,
    Field(discriminator="tag"),
]


class Arrow(BaseModel, frozen=True):
    tag: Literal["arrow"] = "arrow"
    domain: Type
    codomain: Type


class Int(BaseModel, frozen=True):
    tag: Literal["int"] = "int"


class Bool(BaseModel, frozen=True):
    tag: Literal["bool"] = "bool"


class Trivial(BaseModel, frozen=True):
    tag: Literal["trivial"] = "trivial"


class Product(BaseModel, frozen=True):
    tag: Literal["product"] = "product"
    components: Sequence[Type]


type Term = Annotated[
    # Lambda
    Reference
    | Abstraction
    | Application
    # Bool
    | Boolean
    | If
    | And
    # Int
    | Immediate
    | Primitive
    | Branch
    # Trivial
    | Sole
    # Product
    | Tuple
    | TupleGet
    | Join
    | Project,
    Field(discriminator="tag"),
]


class Reference(BaseModel, frozen=True):
    tag: Literal["reference"] = "reference"
    name: Identifier


class Abstraction(BaseModel, frozen=True):
    tag: Literal["abstraction"] = "abstraction"
    parameter: Identifier
    domain: Type
    body: Term


class Application(BaseModel, frozen=True):
    tag: Literal["application"] = "application"
    target: Term
    argument: Term


class Boolean(BaseModel, frozen=True):
    tag: Literal["boolean"] = "boolean"
    value: bool


class If(BaseModel, frozen=True):
    tag: Literal["if"] = "if"
    test: Term
    consequent: Term
    otherwise: Term


class And(BaseModel, frozen=True):
    tag: Literal["and"] = "and"
    left: Term
    right: Term


class Immediate(BaseModel, frozen=True):
    tag: Literal["immediate"] = "immediate"
    value: int


class Primitive(BaseModel, frozen=True):
    tag: Literal["primitive"] = "primitive"
    operator: Literal["+", "-", "*"]
    left: Term
    right: Term


class Branch(BaseModel, frozen=True):
    tag: Literal["branch"] = "branch"
    operator: Literal["<", "=="]
    left: Term
    right: Term
    motive: Type
    consequent: Term
    otherwise: Term


class Sole(BaseModel, frozen=True):
    tag: Literal["sole"] = "sole"


class Successor(BaseModel, frozen=True):
    tag: Literal["successor"] = "successor"
    target: Term


class Tuple(BaseModel, frozen=True):
    tag: Literal["tuple"] = "tuple"
    components: Sequence[Term]


class TupleGet(BaseModel, frozen=True):
    tag: Literal["tuple_get"] = "tuple_get"
    target: Term
    index: Nat


class Join(BaseModel, frozen=True):
    tag: Literal["join"] = "join"
    components: Sequence[Term]


class Project(BaseModel, frozen=True):
    tag: Literal["project"] = "project"
    target: Term
    index: Annotated[int, Field(ge=0)]
