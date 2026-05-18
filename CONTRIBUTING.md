# Setup Development Environment

Before contributing, make sure your environment is ready.

## Install UV

We use UV for dependency management, running tests, and pre-commit hooks.

- [Installing UV](https://docs.astral.sh/uv/getting-started/installation/)

## Fork and Clone the Repository

1. Fork the repository on GitHub (use your account or organization).

2. Clone your fork locally:

```bash
git clone https://github.com/<your-org>/471c.git
cd 471c
```

3. Enable GitHub Actions for your fork if desired (Actions → Enable workflows).

4. If you use CodeCov, connect it to your GitHub account separately. Update badge URLs in `README.md` as needed for your fork.

## Install project dependencies

```bash
cd <PROJECT>
uv sync --all-extras --all-packages
uv run pre-commit run --all-files
```

## Verify setup

```bash
uv run pytest
```

# Code Formatting & Style Requirements

To keep the codebase consistent and maintainable, please follow these formatting rules:

## Python Style

We use ruff (via UV) to enforce code style and linting rules: See pyproject.toml for the configuration. A pre-commit hook runs ruff automatically and will prevent commits of poor quality code. You can have ruff automatically fix issues by running the following from the project root.

```bash
uv run ruff fix .
```

However, if you're using VS Code, you should install the project's recommended extensions. If you do so, the provided configuration in .vscode/settings.json will reformat on save.

### Type Annotations

Type annotations are required for all functions, methods, and class attributes wherever feasible. They help with:

- Static type checking. We are using pylance.

- Improved code readability and maintainability

- Better editor/IDE support (autocomplete, linting, refactoring)

# Testing & Coverage

All contributions must be tested and tests must be executable via `uv run pytest`. Code coverage is reported and 100% branch coverage is expected. Pragmas may be used to work around tool limitations (e.g., `#pragma: no branch` with `match`) but other adjustments should only be used as a last effort and must be clearly explained.

Note, that a high-level of coverage should be viewed as a sanity check (low coverage is a bad sign but don't assume high coverage means correctness). Compiler passes are complex and require careful test design to achieve confidence in their correctness.

The CI pipeline expects all tests to pass. Use the appropriate annotation to either skip problematic tests (`@pytest.mark.skip`) or to indicate that the corresponding feature has not been implemented (`@pytest.mark.xfail`).
