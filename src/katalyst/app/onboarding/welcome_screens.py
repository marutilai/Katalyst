from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from rich.prompt import Prompt
from katalyst.app.ui.input_handler import InputHandler
import os

console = Console()
input_handler = InputHandler(console)


def screen_1_welcome_and_security():
    console.print(
        Panel(
            "[bold red]*[/bold red] Welcome to [bold]Katalyst Agent[/bold]\n\n"
            "Let's get started.\n\n"
            "[bold]Security notes:[/bold]\n"
            "1. [bold]Katalyst can make mistakes[/bold]\n   You should always review Katalyst's responses, especially when running code.\n\n"
            "2. Due to prompt injection risks, only use it with code you trust\n",
            border_style="red",
            expand=False,
        )
    )
    input_handler.prompt_text("Press [bold]Enter[/bold] to continue", default="", show_default=False)


def screen_2_trust_folder(folder_path):
    console.print(
        Panel(
            f"[bold yellow]Do you trust the files in this folder?[/bold yellow]\n\n"
            f"[bold]{folder_path}[/bold]\n\n"
            "Katalyst Agent may read files in this folder. Reading untrusted files may lead Katalyst Agent to behave in unexpected ways.\n"
            "With your permission Katalyst Agent may execute files in this folder. Executing untrusted code is unsafe.",
            border_style="yellow",
            expand=False,
        )
    )
    
    trust_options = [
        {"label": "Yes, I trust these files", "value": "proceed"},
        {"label": "No, exit for safety", "value": "exit"}
    ]
    
    choice = input_handler.prompt_arrow_menu(
        title="Trust Verification",
        options=trust_options,
        quit_keys=["escape", "q"]
    )
    
    if choice == "exit" or choice is None:
        input_handler.show_status("Exiting for safety.", status="error")
        exit(0)
    
    input_handler.show_status("Proceeding with trusted folder...", status="success")


def screen_3_final_tips(cwd):
    welcome_text = (
        "[bold red]*[/bold red] Welcome to [bold]Katalyst Agent![/bold]\n\n"
        "[dim]/help for help, /provider to set LLM provider, /model to set LLM model[/dim]\n\n"
        f"[bold]cwd:[/bold] {cwd}"
    )
    console.print(Panel(welcome_text, border_style="red", expand=False))
    tips_md = Markdown(
        """
Tips for getting started:

1. Run `/init` to create a KATALYST.md file with instructions for Katalyst
2. Use `/provider` to switch between OpenAI and Anthropic
3. Use `/model` to select specific models (gpt4.1 for OpenAI, sonnet4/opus4 for Anthropic)
4. Be as specific as you would with another engineer for the best results

*Tip:* Start with small features or bug fixes, tell Katalyst to propose a plan, and verify its suggested edits
        """,
        style="white",
    )
    console.print(tips_md)


# Example usage (for testing):
if __name__ == "__main__":
    screen_1_welcome_and_security()
    screen_2_trust_folder(os.getcwd())
    screen_3_final_tips(os.getcwd())
