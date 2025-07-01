from textwrap import dedent

GENERATE_DIRECTORY_OVERVIEW_PROMPT = dedent("""
# generate_directory_overview Tool

Description: Provides high-level overview and documentation of a codebase by scanning a directory, summarizing each source file, and creating an overall summary. Most efficient for understanding multiple files at once.

## When to Use:
- Understanding entire project, module, or large directory structure
- Getting up to speed on a new codebase quickly
- Generating documentation or architectural overviews
- Analyzing relationships between files and components
- Creating project summaries for documentation

## Parameters:
- dir_path: (string, required) Directory path to analyze (must be directory, not file)
- respect_gitignore: (boolean, optional) Respect .gitignore patterns. Defaults to true.

## Important Notes:
- Call on top-level directory (e.g., 'project/', 'module/') for comprehensive overview
- Call ONCE per major directory - it recursively analyzes all nested content
- Tool handles file reading internally - just provide directory path
- Automatically respects .gitignore patterns

## Example:
{
  "thought": "I need to understand the entire project directory structure.",
  "action": "generate_directory_overview",
  "action_input": {
    "dir_path": "project/"
  }
}

## Output Format:
Returns a comprehensive markdown overview with:
- Directory structure visualization
- File-by-file summaries
- Overall project analysis
- Key insights and patterns
""")
