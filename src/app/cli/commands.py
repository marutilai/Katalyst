import os
from rich.console import Console
from rich.prompt import Prompt
from app.onboarding.doc_templates import get_katalyst_md_template
from app.onboarding.summarize import summarize_text

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


def handle_init_command():
    """
    Analyze the current directory and generate a KATALYST.md documentation file.
    - Lists project structure (clean ASCII tree)
    - Summarizes README.md and config files
    - Uses onboarding templates/utilities
    """
    # 1. List project structure as ASCII tree
    project_tree = "\n".join(["."] + build_ascii_tree("."))

    # 2. Summarize README.md
    if os.path.exists("README.md"):
        with open("README.md", "r") as f:
            readme_summary = summarize_text(f.read())
    else:
        readme_summary = "No README.md found."

    # 3. Summarize config files
    config_files = ["setup.py", "pyproject.toml", "requirements.txt"]
    config_summaries_list = []
    for fname in config_files:
        if os.path.exists(fname):
            with open(fname, "r") as f:
                summary = summarize_text(f.read())
            config_summaries_list.append(f"### {fname}\n{summary}")
    config_summaries = (
        "\n\n".join(config_summaries_list)
        if config_summaries_list
        else "No config files found."
    )

    # 4. (Optional) Extract common commands from README or configs
    common_commands = "(Add common commands here if needed)"

    # 5. Write KATALYST.md using the template
    katalyst_md = get_katalyst_md_template().format(
        project_tree=project_tree,
        readme_summary=readme_summary,
        config_summaries=config_summaries,
        common_commands=common_commands,
    )
    with open("KATALYST.md", "w") as f:
        f.write(katalyst_md)
    console.print("[green]KATALYST.md created with project documentation![/green]")


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
