import pytest
from L3.check import Context, check_term
from L3.syntax import Reference

from packages.L0.src.L0.syntax import Immediate


@pytest.mark.skip()
def test_check_reference_bound():
    term = Reference(name="x")

    context: Context = {
        "x": None,
    }

    check_term(term, context)


@pytest.mark.skip()
def test_check_reference_free():
    term = Reference(name="x")

    context: Context = {}

    with pytest.raises(ValueError):
        check_term(term, context)


def test_check_intermediate():
    term = Immediate(value=0)

    context: Context = {}

    check_term(term, context)
