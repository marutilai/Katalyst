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
        "task": "Generate a concise developer guide, in markdown format, for this repo. Cover setup/test commands, architecture, key components, project layout, technologies used, main entry point, environment variables, and example usage. Keep it structured and specific to the codebase. Add the output to a file named KATALYST.md.",
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
