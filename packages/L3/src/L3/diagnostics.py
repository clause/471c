from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from lark import UnexpectedInput
from pydantic import BaseModel

from .check import check_program
from .parse import parse_program

type DiagnosticStage = Literal["syntax", "semantic", "internal"]
type DiagnosticSeverity = Literal["error", "warning", "information"]


class Diagnostic(BaseModel, frozen=True):
    stage: DiagnosticStage
    severity: DiagnosticSeverity = "error"
    code: str
    message: str
    line: int | None = None
    column: int | None = None
    end_line: int | None = None
    end_column: int | None = None
    snippet: str | None = None


class DiagnosticsReport(BaseModel, frozen=True):
    ok: bool
    diagnostics: Sequence[Diagnostic]


def _line_snippet(source: str, line: int | None) -> str | None:
    if line is None:
        return None

    lines = source.splitlines()
    if line < 1 or line > len(lines):
        return None

    return lines[line - 1]


def _position_for_identifier(source: str, identifier: str) -> tuple[int, int] | None:
    pattern = re.compile(rf"\b{re.escape(identifier)}\b")
    match = pattern.search(source)
    if match is None:
        return None

    before = source[: match.start()]
    line = before.count("\n") + 1
    if "\n" in before:
        column = len(before.rsplit("\n", maxsplit=1)[-1]) + 1
    else:
        column = len(before) + 1

    return line, column


def _identifier_from_message(message: str) -> str | None:
    unbound = re.search(r"Unbound variable:\s*([A-Za-z_][A-Za-z0-9_]*)", message)
    if unbound:
        return unbound.group(1)

    duplicate = re.search(r"Duplicate (?:bindings|parameters):\s*(.+)$", message)
    if duplicate is None:
        return None

    names = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", duplicate.group(1))
    if not names:
        return None

    return names[0]


def _normalize_error_position(source: str, line: int | None, column: int | None) -> tuple[int, int]:
    if isinstance(line, int) and isinstance(column, int) and line > 0 and column > 0:
        return line, column

    lines = source.splitlines()
    if not lines:
        return 1, 1

    last_line_number = len(lines)
    last_column = len(lines[-1]) + 1
    return last_line_number, last_column


def _syntax_diagnostic(source: str, error: UnexpectedInput) -> Diagnostic:
    expected = sorted(getattr(error, "expected", []))
    expected_message = ""
    if expected:
        expected_message = f" Expected one of: {', '.join(expected)}."

    line, column = _normalize_error_position(
        source,
        getattr(error, "line", None),
        getattr(error, "column", None),
    )

    return Diagnostic(
        stage="syntax",
        code="L3_SYNTAX_ERROR",
        message=f"{str(error).strip()}.{expected_message}",
        line=line,
        column=column,
        end_line=line,
        end_column=column + 1,
        snippet=_line_snippet(source, line),
    )


def _semantic_diagnostic(source: str, message: str) -> Diagnostic:
    identifier = _identifier_from_message(message)
    position = _position_for_identifier(source, identifier) if identifier else None

    line: int | None = None
    column: int | None = None
    end_column: int | None = None

    if position is not None:
        line, column = position
        end_column = column + len(identifier) if identifier else None

    code = "L3_SEMANTIC_ERROR"
    if message.startswith("Unbound variable"):
        code = "L3_UNBOUND_VARIABLE"
    elif message.startswith("Duplicate bindings"):
        code = "L3_DUPLICATE_BINDINGS"
    elif message.startswith("Duplicate parameters"):
        code = "L3_DUPLICATE_PARAMETERS"

    return Diagnostic(
        stage="semantic",
        code=code,
        message=message,
        line=line,
        column=column,
        end_line=line,
        end_column=end_column,
        snippet=_line_snippet(source, line),
    )


def analyze_source(source: str) -> DiagnosticsReport:
    try:
        program = parse_program(source)
        check_program(program)
        return DiagnosticsReport(ok=True, diagnostics=[])
    except UnexpectedInput as error:
        return DiagnosticsReport(ok=False, diagnostics=[_syntax_diagnostic(source, error)])
    except ValueError as error:
        return DiagnosticsReport(ok=False, diagnostics=[_semantic_diagnostic(source, str(error))])
    except Exception as error:  # pragma: no cover
        return DiagnosticsReport(
            ok=False,
            diagnostics=[
                Diagnostic(
                    stage="internal",
                    code="L3_INTERNAL_ERROR",
                    message=str(error),
                )
            ],
        )


def analyze_file(path: Path) -> DiagnosticsReport:
    return analyze_source(path.read_text())
