# Katalyst Agent

A modular, node-based terminal coding agent for Python, designed for robust, extensible, and production-ready workflows.

## Quick Setup

To install all dependencies, simply run:

```bash
poetry install
```

This will install all required packages, including `tree-sitter-languages` for code structure tools.

## Code Structure Tools

Code structure tools (like listing code definitions) require the `tree-sitter-languages` package, which is installed automatically with Poetry. No manual setup or build steps are required.

## Searching Files (ripgrep required)

The `search_files` tool requires [ripgrep](https://github.com/BurntSushi/ripgrep) (`rg`) to be installed on your system:
- **macOS:**   `brew install ripgrep`
- **Ubuntu:**  `sudo apt-get install ripgrep`
- **Windows:** `choco install ripgrep`

## TODO

- Generalize the `check_syntax` utility (in `src/katalyst_agent/tools/write_to_file.py`) to support syntax checking for more languages (not just Python).

<!-- More TODOs will be added here as the project evolves. --> 