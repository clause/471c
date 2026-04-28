from L3.diagnostics import analyze_source


def test_diagnostics_ok_program() -> None:
    report = analyze_source("(l3 (x) x)")

    assert report.ok is True
    assert report.diagnostics == []


def test_diagnostics_reports_syntax_error() -> None:
    report = analyze_source("(l3 (x) x")

    assert report.ok is False
    assert len(report.diagnostics) == 1
    diagnostic = report.diagnostics[0]

    assert diagnostic.stage == "syntax"
    assert diagnostic.code == "L3_SYNTAX_ERROR"
    assert diagnostic.line == 1
    assert diagnostic.column is not None


def test_diagnostics_reports_unbound_variable() -> None:
    report = analyze_source("(l3 () x)")

    assert report.ok is False
    assert len(report.diagnostics) == 1
    diagnostic = report.diagnostics[0]

    assert diagnostic.stage == "semantic"
    assert diagnostic.code == "L3_UNBOUND_VARIABLE"
    assert diagnostic.line == 1
    assert diagnostic.column is not None
    assert diagnostic.message == "Unbound variable: x"
