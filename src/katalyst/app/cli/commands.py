import os
from rich.console import Console
from rich.prompt import Prompt
from pathlib import Path

console = Console()


def show_help():
    print("""
Available commands:
/help      Show this help message
/init      Generate a developer guide for the repository (saved as KATALYST.md)
/provider  Set LLM provider (openai/anthropic/ollama)
/model     Set LLM model (gpt4.1 for OpenAI, sonnet4/opus4 for Anthropic)
/exit      Exit the agent
(Type your coding task or command below)
""")


def build_ascii_tree(start_path, prefix=""):
    """
    Recursively build an ASCII tree for the directory, excluding __pycache__, .pyc, and hidden files/folders.
    """
    entries = [
        e
        for e in os.listdir(start_path)
        if not e.startswith(".") and e != "__pycache__" and not e.endswith(".pyc")
    ]
    entries.sort()
    tree_lines = []
    for idx, entry in enumerate(entries):
        path = os.path.join(start_path, entry)
        connector = "└── " if idx == len(entries) - 1 else "├── "
        tree_lines.append(f"{prefix}{connector}{entry}")
        if os.path.isdir(path):
            extension = "    " if idx == len(entries) - 1 else "│   "
            tree_lines.extend(build_ascii_tree(path, prefix + extension))
    return tree_lines


def get_init_plan(plan_name: str) -> str:
    plan_path = Path("plans/planner") / f"{plan_name}.md"
    if plan_path.exists():
        return plan_path.read_text()
    return ""


def handle_init_command(graph, config):
    """
    Execute a task to generate a comprehensive developer guide for the repository and save it to KATALYST.md.
    """
    # Create the input dictionary for generating the developer guide
    init_input = {
        "task": """ROLE: You are a technical documentation specialist analyzing a codebase to create a comprehensive developer guide.

OBJECTIVE: Generate a complete developer guide (KATALYST.md) for this repository by analyzing the existing codebase.

IMPORTANT: Start the document with a comprehensive introductory paragraph that describes what this project is, its purpose, key features, and technology stack. This should be the first thing after the title, before any other sections.

CONSTRAINTS:
- This is PURELY a documentation task
- Do NOT modify any source code files
- Do NOT create new features or functionality
- Do NOT change application behavior
- ONLY create documentation files

REQUIREMENTS:
1. Analyze the codebase to understand:
   - Project structure and organization (list ALL directories)
   - Technologies and dependencies (from pyproject.toml)
   - Architecture and design patterns (two-level agent, graph-based)
   - Key components and their interactions (EVERY module matters)

2. Document the following sections IN DETAIL AND IN THIS ORDER:
   - (Start with introductory paragraph as mentioned above)
   - Project Overview (expand on the intro with more details)
   - Setup and Installation Commands (step-by-step with prerequisites)
   - Test Commands and Testing Strategy (all test types and commands)
   - Architecture Overview (explain the two-level agent structure, data flow)
   - Key Components and Modules (DETAILED - list EVERY major module/file with its purpose and key functions)
   - Project Layout (MANDATORY: Include complete ASCII tree with 'tree' command output style)
   - Technologies Used (full list from pyproject.toml with purposes)
   - Main Entry Point (how the application starts and flows)
   - Environment Variables (ALL variables with descriptions and examples)
   - Example Usage and Common Tasks (comprehensive examples)

3. Output Requirements:
   - Save as KATALYST.md in the repository root
   - If KATALYST.md already exists, assume it's outdated and OVERWRITE it completely
   - Use clear, detailed markdown formatting
   - Include code examples, file paths, and command snippets
   - IMPORTANT: Write the COMPLETE document - do NOT use placeholders
   - The file must be self-contained with ALL sections fully written out
   - DO NOT over-summarize - maintain detail from your analysis
   - Target length: 300-500 lines of comprehensive documentation
   - NEVER use placeholders like "[...TRUNCATED...]" or "[...continued...]"
   - Write out ALL content completely - no shortcuts or abbreviations

PROCESS:
- You may create temporary documentation files during analysis
- When writing KATALYST.md, compile ALL sections into ONE complete file
- Do NOT reference previous sections with placeholders - write everything out
- Ensure the final file contains ALL documentation from start to finish
- For Project Layout, use format like:
  ```
  project-root/
  ├── src/
  │   └── package-name/
  │       ├── module1/
  │       │   ├── main.py          # Entry point description
  │       │   ├── submodule/       # Submodule description
  │       │   └── ...
  │       ├── module2/             # Module description
  │       └── ...
  └── tests/
  ```

CLEANUP REQUIREMENT:
After completing KATALYST.md, you MUST delete ONLY the temporary documentation files YOU created during this task:
1. Check for temporary files in BOTH the root directory AND docs/ directory
2. Look for files YOU created with patterns like: _*.md, *_temp*.md, *_analysis*.md, *_notes*.md, tree.txt, project_tree.txt
3. Do NOT delete: KATALYST.md, README.md, or any existing project documentation
4. Use execute_command to remove ONLY your temporary files
5. Example: execute_command("rm _project_analysis.md docs/tree.txt _tech_notes.md")""",
        "auto_approve": True,  # Auto-approve file creation for the init process
        "project_root_cwd": os.getcwd(),
    }

    console.print("[yellow]Generating developer guide for the repository...[/yellow]")
    
    # Run the full Katalyst execution engine
    try:
        final_state = graph.invoke(init_input, config)

        # Check if the task was completed successfully
        if final_state and final_state.get("response"):
            console.print(f"[green]Developer guide generation complete![/green]")
            console.print(f"[green]Created KATALYST.md in the repository root.[/green]")
            if "error" not in final_state.get("response", "").lower():
                console.print("\n" + final_state.get("response"))
        else:
            console.print("[red]Failed to generate KATALYST.md developer guide.[/red]")
    except Exception as e:
        console.print(f"[red]Error generating developer guide: {str(e)}[/red]")


def handle_provider_command():
    console.print("\n[bold]Available providers:[/bold]")
    console.print("1. openai")
    console.print("2. anthropic")
    console.print("3. ollama (local models)")

    choice = Prompt.ask("Select provider", choices=["1", "2", "3"], default="1")

    if choice == "1":
        provider = "openai"
    elif choice == "2":
        provider = "anthropic"
    else:
        provider = "ollama"
    
    os.environ["KATALYST_LITELLM_PROVIDER"] = provider
    console.print(f"[green]Provider set to: {provider}[/green]")
    
    if provider == "ollama":
        console.print("[yellow]Make sure Ollama is running locally (ollama serve)[/yellow]")
    
    console.print(f"[yellow]Now choose a model for {provider} using /model[/yellow]")


def handle_model_command():
    provider = os.getenv("KATALYST_LITELLM_PROVIDER")
    if not provider:
        console.print("[yellow]Please set the provider first using /provider.[/yellow]")
        return
    if provider == "openai":
        console.print("\n[bold]Available OpenAI models:[/bold]")
        console.print("1. gpt4.1")
        choice = Prompt.ask("Select model", choices=["1"], default="1")
        model = "gpt4.1"
    elif provider == "anthropic":
        console.print("\n[bold]Available Anthropic models:[/bold]")
        console.print("1. sonnet4")
        console.print("2. opus4")
        choice = Prompt.ask("Select model", choices=["1", "2"], default="1")
        model = "sonnet4" if choice == "1" else "opus4"
    else:  # ollama
        console.print("\n[bold]Available Ollama models:[/bold]")
        console.print("1. qwen2.5-coder:7b (Best for coding)")
        console.print("2. phi4 (Fast execution)")
        console.print("3. codestral (22B model)")
        console.print("4. devstral (24B agentic model)")
        choice = Prompt.ask("Select model", choices=["1", "2", "3", "4"], default="1")
        model_map = {
            "1": "ollama/qwen2.5-coder:7b",
            "2": "ollama/phi4",
            "3": "ollama/codestral",
            "4": "ollama/devstral",
        }
        model = model_map[choice]
    os.environ["KATALYST_LITELLM_MODEL"] = model
    console.print(f"[green]Model set to: {model}[/green]")
