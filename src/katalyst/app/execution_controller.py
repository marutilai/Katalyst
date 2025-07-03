"""
Execution controller for handling global Ctrl+C to halt execution.

This module provides a mechanism to gracefully stop Katalyst execution
when the user presses Ctrl+C. A single Ctrl+C cancels the current operation,
while double Ctrl+C (within 0.5 seconds) exits Katalyst completely.
"""

import threading
import signal
import sys
import os
import time
from typing import Callable
from katalyst.katalyst_core.utils.logger import get_logger
from rich.console import Console


class ExecutionController:
    """
    Manages execution state and provides global Ctrl+C (SIGINT) handler functionality.
    
    Handles:
    - Single Ctrl+C: Cancels current operation
    - Double Ctrl+C: Exits Katalyst completely
    """
    
    def __init__(self):
        self.logger = get_logger()
        self.console = Console()
        self._cancelled = threading.Event()
        self._original_sigint_handler = None
        self._last_interrupt_time = 0
        self._interrupt_count = 0
        self._double_press_window = 0.5  # 500ms window for double press
        
    def is_cancelled(self) -> bool:
        """Check if execution has been cancelled."""
        return self._cancelled.is_set()
    
    def cancel(self):
        """Cancel the current execution."""
        self._cancelled.set()
        self.logger.info("Execution cancelled by user")
        
    def reset(self):
        """Reset the cancellation state for a new execution."""
        self._cancelled.clear()
        
    def check_cancelled(self, context: str = ""):
        """
        Check if execution is cancelled and raise exception if so.
        
        Args:
            context: Optional context string for logging
            
        Raises:
            KeyboardInterrupt: If execution has been cancelled
        """
        if self.is_cancelled():
            msg = f"Execution cancelled{f' during {context}' if context else ''}"
            self.logger.info(msg)
            raise KeyboardInterrupt(msg)
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful interruption."""
        def signal_handler(signum, frame):
            current_time = time.time()
            time_since_last = current_time - self._last_interrupt_time
            
            if time_since_last <= self._double_press_window:
                # Double press detected
                self._interrupt_count += 1
                if self._interrupt_count >= 2:
                    self.logger.info("Double Ctrl+C detected - Exiting Katalyst")
                    self.console.print("\n\n[bold red]Double interrupt detected. Exiting Katalyst...[/bold red]")
                    self.console.print("[green]Goodbye![/green]")
                    sys.exit(0)
            else:
                # First press or too much time passed
                self._interrupt_count = 1
                self.logger.info("Received interrupt signal (Ctrl+C) - Press again to exit")
                self.console.print("\n[yellow]Execution cancelled. Press Ctrl+C again to exit Katalyst.[/yellow]")
                self.cancel()
            
            self._last_interrupt_time = current_time
            
        # Store original handler
        self._original_sigint_handler = signal.signal(signal.SIGINT, signal_handler)
        
    def restore_signal_handlers(self):
        """Restore original signal handlers."""
        if self._original_sigint_handler is not None:
            signal.signal(signal.SIGINT, self._original_sigint_handler)
            self._original_sigint_handler = None
    
    def wrap_execution(self, func: Callable, *args, **kwargs):
        """
        Wrap a function execution with cancellation checking.
        
        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func if not cancelled
            
        Raises:
            KeyboardInterrupt: If execution is cancelled
        """
        self.reset()
        self.setup_signal_handlers()
        
        try:
            # Check for cancellation before starting
            self.check_cancelled("initialization")
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Check for cancellation after completion
            self.check_cancelled("completion")
            
            return result
            
        finally:
            self.restore_signal_handlers()


# Global instance
execution_controller = ExecutionController()


def check_execution_cancelled(context: str = ""):
    """
    Convenience function to check if execution is cancelled.
    
    This can be called from anywhere in the codebase to check
    if the user has requested cancellation.
    """
    execution_controller.check_cancelled(context)