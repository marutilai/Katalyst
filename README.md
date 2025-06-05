# Katalyst Agent

A modular, node-based terminal coding agent for Python, designed for robust, extensible, and production-ready workflows.

## Quick Setup

To install all dependencies, simply run:

```bash
poetry install
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

## Running Tests & Checking Coverage

To run all tests:

```
pytest
```

To check test coverage:

```
pytest --cov=src/katalyst_agent
```

This will show a coverage report in the terminal. For a detailed HTML report:

```
pytest --cov=src/katalyst_agent --cov-report=html
```

The HTML report will be in the `htmlcov/` directory.

## TODO

See [TODO.md](./TODO.md) for the latest development tasks and roadmap.

