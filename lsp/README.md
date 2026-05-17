# LSP Example

Heavily documented sample code for https://code.visualstudio.com/api/language-extensions/language-server-extension-guide

## Functionality

This Language Server works for plain text file. It has the following language features:
- Completions
- Diagnostics regenerated on each file change or configuration change

It also includes an End-to-End test.

## Structure

```
.
├── client // Language Client
│   ├── src
│   │   ├── test // End to End tests for Language Client / Server
│   │   └── extension.ts // Language Client entry point
├── package.json // The extension manifest.
└── server // Language Server
    └── src
        └── server.ts // Language Server entry point
```

## Running the Sample

- Run `npm install` in this folder. This installs all necessary npm modules in both the client and server folder
- Open VS Code on this folder.
- Press Ctrl+Shift+B to start compiling the client and server in [watch mode](https://code.visualstudio.com/docs/editor/tasks#:~:text=The%20first%20entry%20executes,the%20HelloWorld.js%20file.).
- Switch to the Run and Debug View in the Sidebar (Ctrl+Shift+D).
- Select `Launch Client` from the drop down (if it is not already).
- Press ▷ to run the launch config (F5).
- In the [Extension Development Host](https://code.visualstudio.com/api/get-started/your-first-extension#:~:text=Then%2C%20inside%20the%20editor%2C%20press%20F5.%20This%20will%20compile%20and%20run%20the%20extension%20in%20a%20new%20Extension%20Development%20Host%20window.) instance of VSCode, open a document in 'plain text' language mode.
  - Type `j` or `t` to see `Javascript` and `TypeScript` completion.
  - Enter text content such as `AAA aaa BBB`. The extension will emit diagnostics for all words in all-uppercase.

## L4 Development notes

When working on the L4 compiler and server integration you will often need the local Python packages to be importable by the language server.

- The `Launch Client` launch configuration now sets `PYTHONPATH` so the Extension Development Host can run the L4 diagnostics CLI against workspace sources.
- To run the L4 CLI directly from the repo root (recommended):

```bash
cd /Users/johnfulkerson/src/CISC471/471c
PYTHONPATH=packages/L4/src:packages/L3/src:packages/L2/src:packages/util/src .venv/bin/python -m L4.main packages/L4/examples/two.l4 --output /tmp/l4_two.py && .venv/bin/python /tmp/l4_two.py
```

- The server publishes a quick parenthesis syntax diagnostic immediately and replaces it with richer diagnostics produced by `python -m L4.main --diagnostics-json <file>` when available.

If you'd like these notes moved or expanded into a top-level developer README, tell me where and I can add it.
