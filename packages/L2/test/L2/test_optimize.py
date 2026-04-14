from L2.optimize import optimize_program
from L2.syntax import (
    Abstract,
    Allocate,
    Apply,
    Begin,
    Branch,
    Immediate,
    Let,
    Load,
    Primitive,
    Program,
    Reference,
    Store,
)


def make_program(body, parameters=None):
    return Program(parameters=parameters or [], body=body)


def test_optimize_program():
    program = make_program(Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=1)))
    assert optimize_program(program) == make_program(Immediate(value=2))


def test_constant_fold_subtract():
    program = make_program(Primitive(operator="-", left=Immediate(value=5), right=Immediate(value=3)))
    assert optimize_program(program) == make_program(Immediate(value=2))


def test_constant_fold_multiply():
    program = make_program(Primitive(operator="*", left=Immediate(value=3), right=Immediate(value=4)))
    assert optimize_program(program) == make_program(Immediate(value=12))


def test_no_fold_primitive_non_immediate():
    program = make_program(
        Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=1)),
        parameters=["x"],
    )
    assert optimize_program(program) == program


def test_constant_fold_branch_lt_true():
    program = make_program(
        Branch(
            operator="<",
            left=Immediate(value=1),
            right=Immediate(value=2),
            consequent=Immediate(value=1),
            otherwise=Immediate(value=0),
        )
    )
    assert optimize_program(program) == make_program(Immediate(value=1))


def test_constant_fold_branch_lt_false():
    program = make_program(
        Branch(
            operator="<",
            left=Immediate(value=2),
            right=Immediate(value=1),
            consequent=Immediate(value=1),
            otherwise=Immediate(value=0),
        )
    )
    assert optimize_program(program) == make_program(Immediate(value=0))


def test_constant_fold_branch_eq_true():
    program = make_program(
        Branch(
            operator="==",
            left=Immediate(value=1),
            right=Immediate(value=1),
            consequent=Immediate(value=1),
            otherwise=Immediate(value=0),
        )
    )
    assert optimize_program(program) == make_program(Immediate(value=1))


def test_constant_fold_branch_eq_false():
    program = make_program(
        Branch(
            operator="==",
            left=Immediate(value=1),
            right=Immediate(value=2),
            consequent=Immediate(value=1),
            otherwise=Immediate(value=0),
        )
    )
    assert optimize_program(program) == make_program(Immediate(value=0))


def test_no_fold_branch_non_immediate():
    program = make_program(
        Branch(
            operator="<",
            left=Reference(name="x"),
            right=Immediate(value=1),
            consequent=Immediate(value=1),
            otherwise=Immediate(value=0),
        ),
        parameters=["x"],
    )
    assert optimize_program(program) == program


def test_const_prop_immediate():
    program = make_program(Let(bindings=[("x", Immediate(value=1))], body=Reference(name="x")))
    assert optimize_program(program) == make_program(Immediate(value=1))


def test_const_prop_reference():
    program = make_program(
        Let(bindings=[("x", Reference(name="y"))], body=Reference(name="x")),
        parameters=["y"],
    )
    assert optimize_program(program) == make_program(Reference(name="y"), parameters=["y"])


def test_const_prop_chain():
    program = make_program(
        Let(
            bindings=[
                ("x", Immediate(value=1)),
                ("y", Primitive(operator="+", left=Reference(name="x"), right=Reference(name="x"))),
            ],
            body=Reference(name="y"),
        )
    )
    assert optimize_program(program) == make_program(Immediate(value=2))


def test_dce_unused_immediate():
    program = make_program(Let(bindings=[("x", Immediate(value=1))], body=Immediate(value=0)))
    assert optimize_program(program) == make_program(Immediate(value=0))


def test_dce_impure_allocate_kept():
    program = make_program(Let(bindings=[("x", Allocate(count=1))], body=Immediate(value=0)))
    assert optimize_program(program) == program


def test_dce_impure_apply_kept():
    program = make_program(
        Let(
            bindings=[("x", Apply(target=Reference(name="f"), arguments=[]))],
            body=Immediate(value=0),
        ),
        parameters=["f"],
    )
    assert optimize_program(program) == program


def test_dce_impure_load_kept():
    program = make_program(
        Let(
            bindings=[("x", Load(base=Reference(name="arr"), index=0))],
            body=Immediate(value=0),
        ),
        parameters=["arr"],
    )
    assert optimize_program(program) == program


def test_dce_impure_store_kept():
    program = make_program(
        Let(
            bindings=[("x", Store(base=Reference(name="arr"), index=0, value=Immediate(value=1)))],
            body=Immediate(value=0),
        ),
        parameters=["arr"],
    )
    assert optimize_program(program) == program


def test_dce_impure_begin_kept():
    program = make_program(
        Let(
            bindings=[("x", Begin(effects=[Reference(name="y")], value=Reference(name="y")))],
            body=Immediate(value=0),
        ),
        parameters=["y"],
    )
    assert optimize_program(program) == program


def test_dce_unused_pure_primitive():
    program = make_program(
        Let(
            bindings=[("x", Primitive(operator="+", left=Reference(name="y"), right=Immediate(value=1)))],
            body=Immediate(value=0),
        ),
        parameters=["y"],
    )
    assert optimize_program(program) == make_program(Immediate(value=0), parameters=["y"])


def test_dce_impure_primitive_kept():
    program = make_program(
        Let(
            bindings=[
                (
                    "x",
                    Primitive(
                        operator="+",
                        left=Apply(target=Reference(name="f"), arguments=[]),
                        right=Immediate(value=1),
                    ),
                )
            ],
            body=Immediate(value=0),
        ),
        parameters=["f"],
    )
    assert optimize_program(program) == program


def test_dce_unused_pure_branch():
    program = make_program(
        Let(
            bindings=[
                (
                    "x",
                    Branch(
                        operator="<",
                        left=Reference(name="y"),
                        right=Immediate(value=0),
                        consequent=Immediate(value=1),
                        otherwise=Immediate(value=0),
                    ),
                )
            ],
            body=Immediate(value=0),
        ),
        parameters=["y"],
    )
    assert optimize_program(program) == make_program(Immediate(value=0), parameters=["y"])


def test_dce_impure_branch_kept():
    program = make_program(
        Let(
            bindings=[
                (
                    "x",
                    Branch(
                        operator="<",
                        left=Reference(name="y"),
                        right=Immediate(value=0),
                        consequent=Allocate(count=1),
                        otherwise=Immediate(value=0),
                    ),
                )
            ],
            body=Immediate(value=0),
        ),
        parameters=["y"],
    )
    assert optimize_program(program) == program


def test_dce_unused_pure_let():
    program = make_program(
        Let(
            bindings=[("x", Let(bindings=[], body=Immediate(value=1)))],
            body=Immediate(value=0),
        )
    )
    assert optimize_program(program) == make_program(Immediate(value=0))


def test_dce_impure_let_kept():
    program = make_program(
        Let(
            bindings=[
                (
                    "x",
                    Let(
                        bindings=[("z", Allocate(count=0))],
                        body=Reference(name="z"),
                    ),
                )
            ],
            body=Immediate(value=0),
        )
    )
    assert optimize_program(program) == program


def test_dce_used_in_subsequent_binding():
    program = make_program(
        Let(
            bindings=[
                ("x", Allocate(count=0)),
                ("y", Load(base=Reference(name="x"), index=0)),
            ],
            body=Reference(name="y"),
        )
    )
    assert optimize_program(program) == program


def test_dce_binding_used_before_store():
    program = make_program(
        Let(
            bindings=[
                ("x", Allocate(count=1)),
                ("y", Store(base=Reference(name="x"), index=0, value=Immediate(value=42))),
            ],
            body=Reference(name="y"),
        )
    )
    assert optimize_program(program) == program


def test_dce_reference_body():
    program = make_program(
        Let(
            bindings=[("x", Allocate(count=0))],
            body=Reference(name="y"),
        ),
        parameters=["y"],
    )
    assert optimize_program(program) == program


def test_dce_allocate_body():
    program = make_program(
        Let(
            bindings=[("x", Allocate(count=0))],
            body=Allocate(count=1),
        )
    )
    assert optimize_program(program) == program


def test_dce_primitive_body():
    program = make_program(
        Let(
            bindings=[("x", Allocate(count=0))],
            body=Primitive(operator="+", left=Reference(name="x"), right=Immediate(value=1)),
        )
    )
    assert optimize_program(program) == program


def test_dce_branch_body():
    program = make_program(
        Let(
            bindings=[("x", Allocate(count=0))],
            body=Branch(
                operator="<",
                left=Reference(name="x"),
                right=Immediate(value=1),
                consequent=Immediate(value=1),
                otherwise=Immediate(value=0),
            ),
        )
    )
    assert optimize_program(program) == program


def test_dce_load_body():
    program = make_program(
        Let(
            bindings=[("x", Allocate(count=1))],
            body=Load(base=Reference(name="x"), index=0),
        )
    )
    assert optimize_program(program) == program


def test_dce_begin_body():
    program = make_program(
        Let(
            bindings=[("x", Allocate(count=0))],
            body=Begin(effects=[Reference(name="x")], value=Immediate(value=1)),
        )
    )
    assert optimize_program(program) == program


def test_dce_apply_body():
    program = make_program(
        Let(
            bindings=[("x", Allocate(count=0))],
            body=Apply(target=Reference(name="f"), arguments=[Reference(name="x")]),
        ),
        parameters=["f"],
    )
    assert optimize_program(program) == program


def test_dce_abstract_body():
    program = make_program(
        Let(
            bindings=[("x", Allocate(count=0))],
            body=Abstract(parameters=["x"], body=Reference(name="x")),
        )
    )
    assert optimize_program(program) == program


def test_dce_let_body():
    program = make_program(
        Let(
            bindings=[("x", Immediate(value=1))],
            body=Let(
                bindings=[("y", Reference(name="x"))],
                body=Reference(name="y"),
            ),
        )
    )
    assert optimize_program(program) == make_program(Immediate(value=1))


def test_reference_not_in_env():
    program = make_program(Reference(name="x"), parameters=["x"])
    assert optimize_program(program) == program


def test_allocate_unchanged():
    program = make_program(Allocate(count=0))
    assert optimize_program(program) == program


def test_abstract_body_optimized():
    program = make_program(
        Abstract(
            parameters=["x"],
            body=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=1)),
        )
    )
    assert optimize_program(program) == make_program(Abstract(parameters=["x"], body=Immediate(value=2)))


def test_abstract_param_shadows_env():
    program = make_program(
        Let(
            bindings=[("x", Immediate(value=1))],
            body=Abstract(parameters=["x"], body=Reference(name="x")),
        )
    )
    assert optimize_program(program) == make_program(Abstract(parameters=["x"], body=Reference(name="x")))


def test_apply_target_and_args_optimized():
    program = make_program(
        Apply(
            target=Reference(name="f"),
            arguments=[Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=1))],
        ),
        parameters=["f"],
    )
    assert optimize_program(program) == make_program(
        Apply(target=Reference(name="f"), arguments=[Immediate(value=2)]),
        parameters=["f"],
    )


def test_load_base_propagated():
    program = make_program(
        Let(
            bindings=[("x", Reference(name="arr"))],
            body=Load(base=Reference(name="x"), index=0),
        ),
        parameters=["arr"],
    )
    assert optimize_program(program) == make_program(
        Load(base=Reference(name="arr"), index=0),
        parameters=["arr"],
    )


def test_store_value_folded():
    program = make_program(
        Store(
            base=Reference(name="arr"),
            index=0,
            value=Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=1)),
        ),
        parameters=["arr"],
    )
    assert optimize_program(program) == make_program(
        Store(base=Reference(name="arr"), index=0, value=Immediate(value=2)),
        parameters=["arr"],
    )


def test_begin_effects_and_value_optimized():
    program = make_program(
        Begin(
            effects=[Primitive(operator="+", left=Immediate(value=1), right=Immediate(value=1))],
            value=Reference(name="x"),
        ),
        parameters=["x"],
    )
    assert optimize_program(program) == make_program(
        Begin(effects=[Immediate(value=2)], value=Reference(name="x")),
        parameters=["x"],
    )


def test_shadowing_non_constant_shadows_outer_constant():
    program = make_program(
        Let(
            bindings=[("x", Immediate(value=1))],
            body=Let(
                bindings=[("x", Allocate(count=0))],
                body=Reference(name="x"),
            ),
        )
    )
    expected = make_program(Let(bindings=[("x", Allocate(count=0))], body=Reference(name="x")))
    assert optimize_program(program) == expected


def test_already_optimized_is_stable():
    program = make_program(Reference(name="x"), parameters=["x"])
    result = optimize_program(program)
    assert optimize_program(result) == result
