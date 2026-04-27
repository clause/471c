from L0 import syntax as L0
from L1 import syntax as L1
from L1.close import close_program, close_term, free_variables
from util.sequential_name_generator import SequentialNameGenerator


def test_free_variables_copy():
    statement = L1.Copy(
        destination="x",
        source="y",
        then=L1.Halt(value="x"),
    )

    assert free_variables(statement) == {"y"}


def test_free_variables_abstract():
    statement = L1.Abstract(
        destination="f",
        parameters=["x"],
        body=L1.Primitive(
            destination="t",
            operator="+",
            left="x",
            right="z",
            then=L1.Halt(value="t"),
        ),
        then=L1.Halt(value="f"),
    )

    assert free_variables(statement) == {"z"}


def test_free_variables_apply():
    statement = L1.Apply(target="f", arguments=["x", "y"])

    assert free_variables(statement) == {"f", "x", "y"}


def test_free_variables_immediate():
    statement = L1.Immediate(
        destination="x",
        value=0,
        then=L1.Halt(value="x"),
    )

    assert free_variables(statement) == set()


def test_free_variables_primitive():
    statement = L1.Primitive(
        destination="x",
        operator="+",
        left="a",
        right="b",
        then=L1.Halt(value="x"),
    )

    assert free_variables(statement) == {"a", "b"}


def test_free_variables_branch():
    statement = L1.Branch(
        operator="<",
        left="a",
        right="b",
        then=L1.Halt(value="x"),
        otherwise=L1.Halt(value="y"),
    )

    assert free_variables(statement) == {"a", "b", "x", "y"}


def test_free_variables_allocate():
    statement = L1.Allocate(
        destination="p",
        count=1,
        then=L1.Halt(value="p"),
    )

    assert free_variables(statement) == set()


def test_free_variables_load():
    statement = L1.Load(
        destination="x",
        base="p",
        index=0,
        then=L1.Halt(value="x"),
    )

    assert free_variables(statement) == {"p"}


def test_free_variables_store():
    statement = L1.Store(
        base="p",
        index=0,
        value="x",
        then=L1.Halt(value="x"),
    )

    assert free_variables(statement) == {"p", "x"}


def test_free_variables_halt():
    statement = L1.Halt(value="x")

    assert free_variables(statement) == {"x"}


def test_close_term_non_abstract_forms():
    fresh = SequentialNameGenerator()
    procedures: list[L0.Procedure] = []

    statement = L1.Copy(
        destination="x",
        source="y",
        then=L1.Immediate(
            destination="z",
            value=1,
            then=L1.Primitive(
                destination="w",
                operator="+",
                left="x",
                right="z",
                then=L1.Branch(
                    operator="<",
                    left="x",
                    right="w",
                    then=L1.Allocate(
                        destination="p",
                        count=1,
                        then=L1.Load(
                            destination="q",
                            base="p",
                            index=0,
                            then=L1.Store(
                                base="p",
                                index=0,
                                value="q",
                                then=L1.Halt(value="q"),
                            ),
                        ),
                    ),
                    otherwise=L1.Apply(target="f", arguments=["x"]),
                ),
            ),
        ),
    )

    actual = close_term(statement, procedures.append, fresh)

    assert procedures == []
    assert isinstance(actual, L0.Copy)
    assert isinstance(actual.then, L0.Immediate)
    assert isinstance(actual.then.then, L0.Primitive)
    assert isinstance(actual.then.then.then, L0.Branch)
    assert isinstance(actual.then.then.then.then, L0.Allocate)
    assert isinstance(actual.then.then.then.then.then, L0.Load)
    assert isinstance(actual.then.then.then.then.then.then, L0.Store)
    assert isinstance(actual.then.then.then.then.then.then.then, L0.Halt)
    assert isinstance(actual.then.then.then.otherwise, L0.Load)


def test_close_term_abstract_lifts_and_builds_closure():
    fresh = SequentialNameGenerator()
    procedures: list[L0.Procedure] = []

    statement = L1.Abstract(
        destination="f",
        parameters=["x"],
        body=L1.Primitive(
            destination="y",
            operator="+",
            left="x",
            right="z",
            then=L1.Halt(value="y"),
        ),
        then=L1.Halt(value="f"),
    )

    actual = close_term(statement, procedures.append, fresh)

    assert len(procedures) == 1
    lifted = procedures[0]

    assert lifted.name == "proc0"
    assert list(lifted.parameters) == ["x", "env0"]
    assert isinstance(lifted.body, L0.Load)
    assert lifted.body.destination == "z"
    assert lifted.body.base == "env0"
    assert lifted.body.index == 0
    assert isinstance(lifted.body.then, L0.Primitive)
    assert isinstance(actual, L0.Allocate)
    assert actual.destination == "env1"


def test_close_program_wraps_main_procedure():
    fresh = SequentialNameGenerator()
    program = L1.Program(
        parameters=["x"],
        body=L1.Halt(value="x"),
    )

    actual = close_program(program, fresh)

    assert isinstance(actual, L0.Program)
    assert len(actual.procedures) == 1
    assert actual.procedures[0].name == "l0"
    assert list(actual.procedures[0].parameters) == ["x"]
    assert isinstance(actual.procedures[0].body, L0.Halt)


def test_close_program_includes_lifted_procedures_before_main():
    fresh = SequentialNameGenerator()
    program = L1.Program(
        parameters=[],
        body=L1.Abstract(
            destination="f",
            parameters=[],
            body=L1.Halt(value="x"),
            then=L1.Halt(value="f"),
        ),
    )

    actual = close_program(program, fresh)

    assert len(actual.procedures) == 2
    assert actual.procedures[0].name.startswith("proc")
    assert actual.procedures[1].name == "l0"
