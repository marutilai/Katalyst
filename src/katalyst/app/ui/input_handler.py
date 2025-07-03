"""
Unified input handler for consistent user interaction across Katalyst.

This module provides a centralized interface for all user input operations,
using Rich components for enhanced styling and user experience.
"""

from typing import List, Optional, Callable, Union, Dict, Any
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.syntax import Syntax
from rich.markdown import Markdown
import os
import sys


class InputHandler:
    """Unified handler for all user input operations in Katalyst."""
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize the InputHandler.
        
        Args:
            console: Optional Rich Console instance. Creates new one if not provided.
        """
        self.console = console or Console()
    
    def prompt_text(
        self, 
        prompt: str, 
        default: Optional[str] = None,
        password: bool = False,
        show_default: bool = True
    ) -> str:
        """
        Get text input from user with consistent styling.
        
        Args:
            prompt: The prompt message to display
            default: Default value if user presses Enter
            password: Hide input for passwords
            show_default: Whether to show the default value in prompt
            
        Returns:
            User's input as string
        """
        return Prompt.ask(
            prompt,
            default=default,
            password=password,
            show_default=show_default,
            console=self.console
        )
    
    def prompt_choice(
        self,
        prompt: str,
        choices: List[str],
        default: Optional[str] = None,
        show_choices: bool = True
    ) -> str:
        """
        Get a choice from a list of options.
        
        Args:
            prompt: The prompt message
            choices: List of valid choices
            default: Default choice if user presses Enter
            show_choices: Whether to show available choices
            
        Returns:
            Selected choice as string
        """
        return Prompt.ask(
            prompt,
            choices=choices,
            default=default,
            show_choices=show_choices,
            console=self.console
        )
    
    def prompt_menu(
        self,
        title: str,
        options: List[Union[str, Dict[str, Any]]],
        prompt_text: str = "Select an option",
        show_numbers: bool = True,
        allow_custom: bool = False,
        custom_prompt: str = "Enter custom value"
    ) -> Union[str, int]:
        """
        Display a menu with numbered options and get user selection.
        
        Args:
            title: Title for the menu
            options: List of options (strings or dicts with 'label' and 'value')
            prompt_text: Text to show when asking for selection
            show_numbers: Whether to show numbers next to options
            allow_custom: Allow user to enter custom value
            custom_prompt: Prompt for custom value entry
            
        Returns:
            Selected option value or index (if options are strings)
        """
        # Create menu display
        table = Table(show_header=False, box=None, padding=(0, 2))
        
        option_values = []
        for idx, option in enumerate(options, 1):
            if isinstance(option, dict):
                label = option.get('label', str(option))
                value = option.get('value', option)
                description = option.get('description', '')
            else:
                label = str(option)
                value = option
                description = ''
            
            option_values.append(value)
            
            if show_numbers:
                number = f"[bold cyan]{idx}.[/bold cyan]"
                table.add_row(number, label, f"[dim]{description}[/dim]" if description else "")
            else:
                table.add_row(label, f"[dim]{description}[/dim]" if description else "")
        
        if allow_custom:
            custom_idx = len(options) + 1
            if show_numbers:
                table.add_row(f"[bold cyan]{custom_idx}.[/bold cyan]", "[italic]Enter custom value[/italic]")
            else:
                table.add_row("[italic]Enter custom value[/italic]")
        
        # Display menu
        self.console.print(Panel(table, title=f"[bold]{title}[/bold]", expand=False))
        
        # Get user choice
        if show_numbers:
            valid_choices = [str(i) for i in range(1, len(options) + 1)]
            if allow_custom:
                valid_choices.append(str(custom_idx))
            
            choice = self.prompt_choice(
                prompt_text,
                choices=valid_choices,
                show_choices=False
            )
            
            choice_idx = int(choice) - 1
            if allow_custom and choice_idx == len(options):
                return self.prompt_text(custom_prompt)
            
            return option_values[choice_idx]
        else:
            # For non-numbered menus, return the label directly
            return self.prompt_text(prompt_text)
    
    def confirm(
        self,
        prompt: str,
        default: bool = True,
        show_default: bool = True
    ) -> bool:
        """
        Get yes/no confirmation from user.
        
        Args:
            prompt: The confirmation prompt
            default: Default value if user presses Enter
            show_default: Whether to show the default value
            
        Returns:
            True for yes, False for no
        """
        return Confirm.ask(
            prompt,
            default=default,
            show_default=show_default,
            console=self.console
        )
    
    def show_file_preview(
        self,
        file_path: str,
        content: str,
        syntax: Optional[str] = None,
        line_numbers: bool = True,
        max_lines: Optional[int] = None
    ) -> None:
        """
        Display a file preview with syntax highlighting.
        
        Args:
            file_path: Path to the file being shown
            content: Content to display
            syntax: Language for syntax highlighting (auto-detected if None)
            line_numbers: Whether to show line numbers
            max_lines: Maximum number of lines to show (None for all)
        """
        if syntax is None:
            # Auto-detect syntax from file extension
            ext = os.path.splitext(file_path)[1].lstrip('.')
            syntax = ext if ext else 'text'
        
        lines = content.split('\n')
        if max_lines and len(lines) > max_lines:
            lines = lines[:max_lines]
            truncated = True
        else:
            truncated = False
        
        # Create syntax highlighted view
        syntax_view = Syntax(
            '\n'.join(lines),
            syntax,
            line_numbers=line_numbers,
            theme="monokai"
        )
        
        title = f"Preview: {file_path}"
        if truncated:
            title += f" (showing first {max_lines} lines)"
        
        self.console.print(Panel(syntax_view, title=title, expand=False))
    
    def prompt_file_approval(
        self,
        file_path: str,
        content: str,
        exists: bool = False,
        show_diff: bool = False,
        old_content: Optional[str] = None
    ) -> bool:
        """
        Enhanced file write approval with preview.
        
        Args:
            file_path: Path to the file
            content: New content to write
            exists: Whether file already exists
            show_diff: Whether to show diff (requires old_content)
            old_content: Existing content for diff display
            
        Returns:
            True if approved, False otherwise
        """
        action = "overwrite" if exists else "create"
        self.console.print(f"\n[bold yellow]Katalyst wants to {action} file:[/bold yellow] {file_path}")
        
        # Show file preview
        self.show_file_preview(file_path, content, max_lines=50)
        
        # Show diff if requested and available
        if show_diff and old_content is not None:
            # Simple line-based diff display
            self.console.print("\n[bold]Changes:[/bold]")
            old_lines = old_content.split('\n')
            new_lines = content.split('\n')
            
            # This is a simplified diff - in production, use difflib
            if len(old_lines) != len(new_lines):
                self.console.print(f"[dim]Line count: {len(old_lines)} → {len(new_lines)}[/dim]")
        
        return self.confirm(f"Proceed with {action}?", default=True)
    
    def show_status(
        self,
        message: str,
        status: str = "info",
        title: Optional[str] = None
    ) -> None:
        """
        Display a status message with appropriate styling.
        
        Args:
            message: The message to display
            status: Status type (info, success, warning, error)
            title: Optional title for the message panel
        """
        style_map = {
            "info": "blue",
            "success": "green",
            "warning": "yellow",
            "error": "red"
        }
        
        style = style_map.get(status, "white")
        
        if title:
            self.console.print(Panel(message, title=title, border_style=style))
        else:
            self.console.print(f"[{style}]{message}[/{style}]")
    
    def prompt_with_suggestions(
        self,
        question: str,
        suggestions: List[str],
        allow_custom: bool = True,
        show_descriptions: bool = False
    ) -> str:
        """
        Enhanced version of request_user_input with better display.
        
        Args:
            question: Question to ask the user
            suggestions: List of suggested responses
            allow_custom: Whether to allow custom answers
            show_descriptions: Show descriptions for suggestions
            
        Returns:
            User's answer as string
        """
        self.console.print(f"\n[bold cyan]Katalyst Question:[/bold cyan]")
        self.console.print(Panel(question, expand=False))
        
        # Prepare options for menu
        options = []
        for suggestion in suggestions:
            if isinstance(suggestion, dict):
                options.append(suggestion)
            else:
                options.append({'label': suggestion, 'value': suggestion})
        
        return self.prompt_menu(
            title="Suggested Answers",
            options=options,
            prompt_text="Your answer (number or custom)",
            allow_custom=allow_custom,
            custom_prompt=f"Your answer to: {question}"
        )
    
    def prompt_arrow_menu(
        self,
        title: str,
        options: List[Union[str, Dict[str, Any]]],
        show_search_hint: bool = False,
        multi_select: bool = False,
        preselected_indices: Optional[List[int]] = None,
        quit_keys: List[str] = ["escape", "q"]
    ) -> Optional[Union[str, List[str]]]:
        """
        Display an interactive menu with arrow key navigation.
        
        Args:
            title: Title for the menu
            options: List of options (strings or dicts with 'label' and 'value')
            show_search_hint: Whether to show search functionality hint
            multi_select: Enable multi-selection mode
            preselected_indices: Indices of pre-selected items (for multi-select)
            quit_keys: Keys that will cancel selection
            
        Returns:
            Selected option value(s) or None if cancelled
        """
        try:
            from simple_term_menu import TerminalMenu
        except ImportError:
            # Fallback to numbered menu if simple-term-menu not available
            self.console.print("[yellow]Arrow key navigation not available. Using numbered menu.[/yellow]")
            return self.prompt_menu(title, options, show_numbers=True)
        
        # Extract labels for display
        menu_entries = []
        values = []
        
        for option in options:
            if isinstance(option, dict):
                label = option.get('label', str(option))
                value = option.get('value', option)
                description = option.get('description', '')
                
                # Format with description if available
                if description:
                    menu_entries.append(f"{label} - {description}")
                else:
                    menu_entries.append(label)
                values.append(value)
            else:
                menu_entries.append(str(option))
                values.append(option)
        
        # Clear line and print title with Rich
        self.console.print(f"\n[bold]{title}[/bold]")
        if show_search_hint and not multi_select:
            self.console.print("[dim]Use ↑↓ to navigate, Enter to select, Esc to cancel[/dim]")
        elif multi_select:
            self.console.print("[dim]Use ↑↓ to navigate, Space to toggle, Enter to confirm, Esc to cancel[/dim]")
        else:
            self.console.print("[dim]Use ↑↓ to navigate, Enter to select, Esc to cancel[/dim]")
        
        try:
            # Configure terminal menu
            menu_cursor_style = ("fg_cyan", "bold")
            
            # Create terminal menu
            terminal_menu = TerminalMenu(
                menu_entries,
                title="",  # We already printed title with Rich
                multi_select=multi_select,
                show_multi_select_hint=multi_select,
                preselected_entries=preselected_indices,
                quit_keys=quit_keys,
                menu_cursor_style=menu_cursor_style,
                clear_screen=False  # Don't clear, we want to preserve Rich output
            )
            
            # Show menu and get selection
            menu_entry_index = terminal_menu.show()
        except (OSError, IOError) as e:
            # Handle non-TTY environments (e.g., when running tests)
            self.console.print(f"[yellow]Arrow navigation unavailable in this environment. Using numbered menu.[/yellow]")
            return self.prompt_menu(title, options, show_numbers=True)
        
        # Handle cancellation
        if menu_entry_index is None:
            return None
        
        # Return selected value(s)
        if multi_select:
            if isinstance(menu_entry_index, tuple):
                return [values[i] for i in menu_entry_index]
            else:
                return []
        else:
            return values[menu_entry_index]


# Global instance for convenience
default_handler = InputHandler()