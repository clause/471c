from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import BaseModel, Field

type Identifier = Annotated[str, Field(min_length=1)]
# type Label = Annotated[str, Field(min_length=1)]
# idk why this is here so I've commented it out
type Nat = Annotated[int, Field(ge=0)]


class Program(BaseModel, frozen=True):
    tag: Literal["program"] = "program"
    parameters: Sequence[Identifier]
    body: Term


type Type = Annotated[
    Arrow | Int | Bool | Trivial | Product,
    Field(discriminator="tag"),
]


class Arrow(BaseModel, frozen=True):  # Arrow type used to represent function types, e.g. int -> int
    tag: Literal["arrow"] = "arrow"
    domain: Type
    codomain: Type


class Int(BaseModel, frozen=True):  # Int, its an integer dude. Immutable
    tag: Literal["int"] = "int"


class Bool(BaseModel, frozen=True):  # Bool, Truthiness Immutable
    tag: Literal["bool"] = "bool"


class Trivial(BaseModel, frozen=True):
    tag: Literal["trivial"] = "trivial"


# commented out for now as it is unneeded


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


class Boolean(BaseModel, frozen=True):  # the expression of booleans
    tag: Literal["boolean"] = "boolean"
    value: bool


class If(BaseModel, frozen=True):  # lacks a motive
    tag: Literal["if"] = "if"
    test: Term
    consequent: Term
    otherwise: Term


class And(BaseModel, frozen=True):  #
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
    left: Term  # any term currently, may want to make it unable to accept say a tuple
    right: Term  # because of this need to check the matter of
    motive: Type  # Expected return type of the branch
    consequent: Term
    otherwise: Term


class Sole(BaseModel, frozen=True):
    tag: Literal["sole"] = "sole"


# class Successor(BaseModel, frozen=True):
#     tag: Literal["successor"] = "successor"
#     target: Term
# I have no idea what this is or what it is for but am not removing it in case its important


class Tuple(BaseModel, frozen=True):  # tuples should be 2 types grouped together yea?
    tag: Literal["tuple"] = "tuple"
    components: Sequence[Term]


class TupleGet(BaseModel, frozen=True):  # grabs from the tuple returning the type(s) within?
    tag: Literal["tuple_get"] = "tuple_get"
    target: Term
    index: Nat


class Join(BaseModel, frozen=True):  # Or is join the literal
    tag: Literal["join"] = "join"
    components: Sequence[Term]


class Project(BaseModel, frozen=True):
    tag: Literal["project"] = "project"
    target: Term
    index: Annotated[int, Field(ge=0)]
