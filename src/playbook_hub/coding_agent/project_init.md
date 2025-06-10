# Plan for /init Command

Description: This plan is used by the planner when user runs the `/init` command. It guides the agent to generate a comprehensive `KATALYST.md` file that documents the project's purpose, architecture, dependencies, structure, and key components. The plan covers project summary, tech stack, file structure, detailed breakdowns, and README summary. Use this plan to help onboard new contributors or provide a high-level overview of the codebase. Do not include or reference this guidance in the output.

## 0. Metadata
- Target output file: KATALYST.md
- Format: GitHub-flavoured Markdown
- Sections (in order): Project Overview → Tech Stack → Directory Tree → Component Details → README Snapshot → How to Contribute → Next Steps
    
## 1. Overall Project Overview
- Generate a high-level description of the project, including its main purpose, core architecture, and goals.

## 2. Tech Stack & Key Dependencies
- Read and summarize the project's primary programming languages, frameworks, and significant libraries.
  - Use `read_file` (for `pyproject.toml`, `requirements.txt`, `setup.py`) and summarize the relevant sections.

## 3. Directory Tree
- Generate a clean ASCII tree representation of the directory and file layout (recursively, respecting .gitignore), excluding hidden files and build artifacts.
  - Use `list_files`, `ascii_tree` utility, or `/init` logic as appropriate.

## 4. Detailed Component Breakdown (File/Module Level)
- For each significant source file/module:
  - List the file path (e.g., `src/app/main.py`).
  - Summarize the file's purpose (1-2 sentences).
  - List all classes and functions using code introspection.
    - Use `list_code_definitions`.
  - For each class:
    - Summarize the class's role (1 sentence).
  - For each top-level or critical function/method:
    - Show the function/method signature.
    - Summarize what the function does (1 sentence).

## 5. README.md Summary (if exists)
- Read and summarize the project's main README file.
- Use `read_file` and summarize the content if the file exists.

## 6. Final Remark
- Do not ask the user for any additional input; all information must be gathered from the codebase and existing files.
- The playbook guidelines are strict requirements. Do not deviate from them or ask the user for any file names or additional input.
