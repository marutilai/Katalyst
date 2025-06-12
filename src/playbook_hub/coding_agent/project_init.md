# Playbook: Generating a Project Overview (`KATALYST.md`)

**Description:** This playbook provides a comprehensive strategy for creating a `KATALYST.md` file. It's the primary playbook for the `/init` command but its sections can also guide other analysis tasks. Each section outlines a goal and the specific tools required to achieve it.

**Target File:** `KATALYST.md`
**Output Format:** GitHub-flavoured Markdown

### Overview: How to get a high-level overview of the project?
- **Goal:** Understand the project's main purpose, architecture, and stated goals.
- **Method:**
  1. Use the `read_file` tool to get the contents of the main `README.md`.
  2. Use the `summarize_code_structure` tool on the primary source directory (e.g., `src/` or `app/`).
  3. Synthesize the results from these tools into a concise, one-paragraph project overview.

### Tech Stack: How to determine the project's tech stack and dependencies?
- **Goal:** Identify the programming languages, frameworks, and key libraries used.
- **Method:**
  1. Use the `read_file` tool to inspect dependency files in this order of priority: `pyproject.toml`, `requirements.txt`, `package.json`, `setup.py`.
  2. Summarize the `[dependencies]` or `[project]` sections of the file found.

### File Structure: How to visualize the project's file structure?
- **Goal:** Create a clean ASCII tree of the project layout.
- **Method:**
  1. Use the `list_files` tool with the `recursive=True` parameter on the project root (`.`).
  2. Format the resulting list of files into an ASCII tree, respecting `.gitignore` and excluding hidden files or build artifacts (like `__pycache__`).

### Code Analysis: How to analyze a specific source code file in detail?
- **Goal:** Understand a file's purpose, what it contains, and how it's structured.
- **Method:**
  1. **Use the `summarize_code_structure` tool on the file's path.** This provides a conceptual summary.
  2. **Use the `list_code_definition_names` tool on the file's path.** This provides a structural map of all classes and functions.
  3. Combine the summary and the list of definitions to create a detailed breakdown for that component.

### Final Assembly Instructions
- After gathering all information from the steps above, synthesize the content.
- Arrange the final output in the following section order: `Project Overview`, `Tech Stack`, `Directory Tree`, `Component Details`, and a `README Snapshot`.
- Use the `write_to_file` tool to save the complete document to `KATALYST.md`.
- **Strict Requirement:** Do not ask the user for any file names or additional input during this process. All information must be derived from the codebase.