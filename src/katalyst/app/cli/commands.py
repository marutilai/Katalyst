import os
from rich.console import Console
from pathlib import Path
from katalyst.app.ui.input_handler import InputHandler

console = Console()
input_handler = InputHandler(console)


def show_help():
    print("""
Available commands:
/help      Show this help message
/init      Generate a developer guide for the repository (saved as KATALYST.md)
/provider  Set LLM provider (openai/anthropic/ollama)
/model     Set LLM model (gpt4.1 for OpenAI, sonnet4/opus4 for Anthropic)
/exit      Exit the agent

Type / to see available commands or enter your coding task below.
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
    providers = [
        {"label": "OpenAI", "value": "openai", "description": "GPT models via OpenAI API"},
        {"label": "Anthropic", "value": "anthropic", "description": "Claude models via Anthropic API"},
        {"label": "Ollama", "value": "ollama", "description": "Local models via Ollama"}
    ]
    
    provider = input_handler.prompt_arrow_menu(
        title="Select LLM Provider",
        options=providers,
        quit_keys=["escape"]
    )
    
    if provider is None:
        input_handler.show_status("Provider selection cancelled", status="warning")
        return
    
    os.environ["KATALYST_PROVIDER"] = provider
    input_handler.show_status(f"Provider set to: {provider}", status="success")
    
    if provider == "ollama":
        input_handler.show_status(
            "Make sure Ollama is running locally (ollama serve)",
            status="warning"
        )
    
    input_handler.show_status(
        f"Now choose a model for {provider} using /model",
        status="info"
    )


def handle_model_command():
    provider = os.getenv("KATALYST_PROVIDER")
    if not provider:
        input_handler.show_status(
            "Please set the provider first using /provider.",
            status="warning"
        )
        return
    
    if provider == "openai":
        models = [
            {"label": "GPT-4.1", "value": "gpt4.1", "description": "Latest GPT-4 model"}
        ]
    elif provider == "anthropic":
        models = [
            {"label": "Claude 3.5 Sonnet", "value": "sonnet4", "description": "Fast and capable"},
            {"label": "Claude 3 Opus", "value": "opus4", "description": "Most capable model"}
        ]
    else:  # ollama
        models = [
            {"label": "Qwen 2.5 Coder (7B)", "value": "ollama/qwen2.5-coder:7b", "description": "Best for coding tasks"},
            {"label": "Phi-4", "value": "ollama/phi4", "description": "Fast execution, lightweight"},
            {"label": "Codestral (22B)", "value": "ollama/codestral", "description": "Large code model"},
            {"label": "Devstral (24B)", "value": "ollama/devstral", "description": "Agentic coding model"}
        ]
    
    model = input_handler.prompt_arrow_menu(
        title=f"Select Model for {provider.title()}",
        options=models,
        quit_keys=["escape"]
    )
    
    if model is None:
        input_handler.show_status("Model selection cancelled", status="warning")
        return
    
    os.environ["KATALYST_MODEL"] = model
    input_handler.show_status(f"Model set to: {model}", status="success")
