import os
from rich.console import Console
from rich.prompt import Prompt
from pathlib import Path
from src.app.playbook_navigator import PlaybookNavigator
from src.katalyst_core.state import KatalystState
from src.coding_agent.nodes.planner import planner
from src.app.katalyst_runner import run_katalyst_task

console = Console()


def show_help():
    print("""
Available commands:
/help      Show this help message
/init      Create a KATALYST.md file with instructions
/provider  Set LLM provider (openai/anthropic)
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


def handle_init_command(graph):
    """
    Retrieve the playbook for /init, use its text as the planner task, and execute the full Katalyst engine to generate KATALYST.md.
    """
    navigator = PlaybookNavigator()
    playbook = navigator.get_playbook_by_id(
        "project_init"
    )  # or "init_plan" if that's your ID
    if not playbook:
        console.print("[red]No playbook found for /init![/red]")
        return

    # Create a new KatalystState with the playbook guidelines and a simple task
    state = KatalystState(
        task="Execute the project initialization playbook to generate .katalyst/project_knowledge.json.",
        playbook_guidelines=playbook.content_md,
        auto_approve=True,
        project_root_cwd=os.getcwd(),
    )

    # Run the full Katalyst execution engine to generate .katalyst/project_knowledge.json
    final_state = run_katalyst_task(state.task, state, graph)

    # Write the output to KATALYST.md
    if final_state and final_state.response:
        with open(".katalyst/project_knowledge.json", "w") as f:
            f.write(final_state.response)
        console.print(
            "[green].katalyst/project_knowledge.json created with generated output![/green]"
        )
    else:
        console.print("[red]Failed to generate .katalyst/project_knowledge.json [/red]")


def handle_provider_command():
    console.print("\n[bold]Available providers:[/bold]")
    console.print("1. openai")
    console.print("2. anthropic")

    choice = Prompt.ask("Select provider", choices=["1", "2"], default="1")

    provider = "openai" if choice == "1" else "anthropic"
    os.environ["KATALYST_LITELLM_PROVIDER"] = provider
    console.print(f"[green]Provider set to: {provider}[/green]")
    console.print(f"[yellow]Now choose a model for {provider} using /model[/yellow]")


def handle_model_command():
    provider = os.getenv("KATALYST_LITELLM_PROVIDER")
    if not provider:
        console.print("[yellow]Please set the provider first using /provider.[/yellow]")
        return
    if provider == "openai":
        console.print("\n[bold]Available OpenAI models:[/bold]")
        console.print("1. gpt4.1")
        console.print("2. gpt-4.1-mini")
        choice = Prompt.ask("Select model", choices=["1", "2"], default="1")
        model = "gpt4.1" if choice == "1" else "gpt-4.1-mini"
    else:  # anthropic
        console.print("\n[bold]Available Anthropic models:[/bold]")
        console.print("1. sonnet4")
        console.print("2. opus4")
        choice = Prompt.ask("Select model", choices=["1", "2"], default="1")
        model = "sonnet4" if choice == "1" else "opus4"
    os.environ["KATALYST_LITELLM_MODEL"] = model
    console.print(f"[green]Model set to: {model}[/green]")
