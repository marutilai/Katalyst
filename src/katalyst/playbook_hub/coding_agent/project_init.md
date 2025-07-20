# Playbook: Building the Project Knowledge Base

Description: This playbook outlines the comprehensive strategy for creating a structured, machine-readable knowledge base of the entire project. This process is triggered by the `/init` command. The final output is a single JSON file, `.katalyst/project_knowledge.json`, which will serve as the agent's persistent memory to accelerate and improve all future tasks.

**Target File:** `.katalyst/project_knowledge.json`  
**Output Format:** A single JSON object with the following top-level keys:
- `project_overview`: A summary of the project's purpose, derived from the README.
- `tech_stack`: A summary of dependencies and technologies from `pyproject.toml` or `requirements.txt`.
- `directory_listing`: A complete, recursive list of all files and directories.
- `component_details`: A detailed breakdown of each source file, including its summary, key functions, and classes.

## Step 1: Get the Full File Structure
**Goal:** Create a complete map of all files and directories in the project.  
**Method:**
- Use the `list_files` tool with `path='.'` and `recursive=True`.
- Store the resulting list of file paths. This data will populate the `directory_listing` key in the final JSON object.

## Step 2: Extract the Project Overview
**Goal:** Understand the project's stated purpose from its primary documentation.  
**Method:**
- Use the `read_file` tool to get the contents of the main `README.md` file.
- Summarize this content. The summary will be the value for the `project_overview` key.

## Step 3: Determine the Tech Stack
**Goal:** Identify the project's programming languages, frameworks, and key libraries.  
**Method:**
- Use the `read_file` tool to inspect dependency files in this order of priority: `pyproject.toml`, `requirements.txt`.
- Summarize the `[dependencies]` or equivalent sections from the file found. This summary will be the value for the `tech_stack` key.

## Step 4: Analyze All Source Code Components
**Goal:** Create a detailed, file-by-file analysis of the entire codebase. This is the most critical step.  
**Method:**
- Use `ls` with recursive option to explore the source directory structure (e.g., `src/` or the project root `.`).
- Use `list_code_definitions` to identify key classes and functions in each source file.
- Use `read` to examine important files and understand their purpose and implementation.
- For each significant source file, create a summary including its purpose, key functions, and key classes.
- The list of individual file summaries you create will be the value for the `component_details` key.

## Step 5: Final Assembly and Persistent Storage
**Goal:** Combine all gathered information into a single JSON object and save it to disk.  
**Method:**
- **Synthesize:** In memory, construct the final JSON object by assembling the data from Steps 1, 2, 3, and 4 into the pre-defined structure (`project_overview`, `tech_stack`, etc.).
- **Save:** Use the `write_to_file` tool to save the synthesized JSON object.
  - `path`: `.katalyst/project_knowledge.json`
  - `content`: The complete, beautified JSON string of the synthesized data.

## Strict Execution Requirements
- The final output of this entire process must be the creation of the `.katalyst/project_knowledge.json` file.
- Do not ask the user for any file names or additional input. All information must be derived automatically from the codebase.
- The steps must be followed sequentially, as the final assembly step depends on the successful completion of all preceding analysis steps.