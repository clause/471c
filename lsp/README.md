# LSP for L3/L4

Language Server Protocol extension providing syntax and semantic diagnostics, semantic token highlighting for L3 and L4 language files (`.l3`, `.l4`).

## Functionality

This Language Server provides:
- **Syntax diagnostics** — parser errors (e.g., unmatched parentheses)
- **Semantic diagnostics** — type checking, unbound variables, duplicate bindings
- **Semantic token highlighting** — keywords and types
- **End-to-End tests** — regression tests for diagnostics and highlighting

## Structure

```
.
├── client              // VSCode extension client
│   ├── src
│   │   ├── extension.ts    // Extension entry point
│   │   └── test/           // End-to-end tests
│   └── testFixture/        // L3/L4 test files
├── server              // Language server (Node.js)
│   └── src/server.ts   // Server logic; calls L3/L4 Python diagnostics CLI
├── package.json        // Extension manifest
└── README.md           // This file
```

## Running the Extension

- Run `npm install` in this folder to install dependencies
- Open VS Code on this folder (or the repo root)
- Press F5 to launch the Extension Development Host (or go to Run → Launch Client)
- Open an `.l3` or `.l4` file to see diagnostics and highlighting
- Run `npm test` to run end-to-end tests

## L4 Development notes

When working on the L4 compiler and server integration you will often need the local Python packages to be importable by the language server.

- The `Launch Client` launch configuration now sets `PYTHONPATH` so the Extension Development Host can run the L4 diagnostics CLI against workspace sources.
- To run the L4 CLI directly from the repo root (recommended):

```bash
cd /Users/johnfulkerson/src/CISC471/471c
PYTHONPATH=packages/L4/src:packages/L3/src:packages/L2/src:packages/util/src .venv/bin/python -m L4.main packages/L4/examples/two.l4 --output /tmp/l4_two.py && .venv/bin/python /tmp/l4_two.py
```

- The server publishes a quick parenthesis syntax diagnostic immediately and replaces it with richer diagnostics produced by `python -m L4.main --diagnostics-json <file>` when available.
