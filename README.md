# Katalyst Agent

A modular, node-based terminal coding agent for Python, designed for robust, extensible, and production-ready workflows.

![Katalyst Coding Agent Architecture](docs/images/katalyst-coding-agent-dag.png)
*Figure: Architecture diagram of the Katalyst Coding Agent (DAG/graph structure)*

## Quick Setup

To install Katalyst from PyPI, simply run:

```bash
pip install katalyst
```

**Important:**
You must set your OpenAI API key as the environment variable `OPENAI_API_KEY` or add it to a `.env` file in your project directory. The first time you run `katalyst`, you will be prompted to enter your API key if it is missing. You can get an API key from [https://platform.openai.com/account/api-keys](https://platform.openai.com/account/api-keys).

## Searching Files (ripgrep required)

The `search_files` tool requires [ripgrep](https://github.com/BurntSushi/ripgrep) (`rg`) to be installed on your system:
- **macOS:**   `brew install ripgrep`
- **Ubuntu:**  `sudo apt-get install ripgrep`
- **Windows:** `choco install ripgrep`

## Features

- Automatic project state persistence: Katalyst saves your project state (such as chat history) to `.katalyst_state.json` in your project directory after every command. This happens in the background—no user action required. When you return to your project, your session context is automatically restored.

## Testing

Katalyst includes both unit and functional tests. For detailed information about running tests, writing new tests, and test coverage, see [TESTS.md](TESTS.md).


## TODO

See [TODO.md](./TODO.md) for the latest development tasks and roadmap.

