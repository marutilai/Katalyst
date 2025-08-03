# Terminal UI Improvement Plan

## Overview

This document outlines a comprehensive plan to transform Katalyst's terminal interface to match the polished, professional experience provided by Claude Code. The goal is to move beyond basic terminal output to create a clean, intuitive, and keyboard-driven interface that enhances user productivity.

## Background: Claude Code's Superior UX

Claude Code (Anthropic's official CLI) demonstrates several key advantages in terminal UX:

1. **Clean, structured output** - No raw logs or debug messages mixed with content
2. **Modal interface** - Distinct Plan mode vs Code mode with keyboard shortcuts (Shift+Tab to toggle)
3. **Neat summaries** - Pretty-printed results instead of verbose debug logs
4. **Professional appearance** - Thoughtful formatting and visual hierarchy
5. **Keyboard-driven workflow** - Quick navigation and mode switching without leaving the keyboard

## Current Issues in Katalyst

### 1. Mixed Output
- Logger messages (`[INFO]`, `[DEBUG]`, `[ERROR]`) are interspersed with agent responses
- Technical implementation details are exposed to users
- Difficult to distinguish between system messages and actual content

### 2. No Mode Separation
- Single execution flow without distinction between planning and implementation
- Users can't easily switch contexts between discussing approach vs executing code
- No visual indication of current agent state or capabilities

### 3. Verbose Logging
- Console shows internal debug information by default
- Log prefixes like `[CONVERSATION] Generated response:` clutter the output
- Timestamps and module names add visual noise

### 4. Basic Interface
- Simple `>` prompt without context
- No status bar or mode indicators
- Limited keyboard shortcuts
- No visual feedback during operations

## Proposed Solution: Clean Terminal Experience

### Core Principles
1. **Separation of Concerns** - Logging for debugging, UI for user interaction
2. **Progressive Disclosure** - Show only what's relevant, hide technical details
3. **Visual Hierarchy** - Clear distinction between different types of information
4. **Keyboard Efficiency** - Common actions accessible via shortcuts

## Implementation Phases

### Phase 1: Clean Output System

#### 1.1 Create Dedicated UI Output Module

Create `src/katalyst/app/ui/ui_output.py`:

```python
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from typing import Optional, List, Dict, Any

class UIOutput:
    """Handles all user-facing terminal output."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.current_mode = "plan"
    
    def print_agent_message(self, content: str, agent_type: str = "assistant"):
        """Print agent responses without log prefixes."""
        # For conversation responses, just print the content directly
        if agent_type == "conversation":
            self.console.print(content)
        else:
            # For other agents, add subtle formatting
            self.console.print(f"\n{content}\n")
    
    def print_status(self, message: str, status_type: str = "info"):
        """Display status updates in a clean format."""
        styles = {
            "info": "blue",
            "success": "green",
            "warning": "yellow",
            "error": "red"
        }
        style = styles.get(status_type, "white")
        
        # Use a subtle indicator instead of log-style prefix
        if status_type == "error":
            self.console.print(f"[{style}]⚠ {message}[/{style}]")
        elif status_type == "success":
            self.console.print(f"[{style}]✓ {message}[/{style}]")
        else:
            self.console.print(f"[dim]{message}[/dim]")
    
    def print_mode_indicator(self):
        """Display current mode in the prompt."""
        mode_display = {
            "plan": "📝 Plan Mode",
            "execute": "⚡ Execute Mode"
        }
        return mode_display.get(self.current_mode, "Katalyst")
```

#### 1.2 Modify Logger Configuration

Update `src/katalyst/katalyst_core/utils/logger.py` to remove console output by default:

```python
# Add environment variable check
SHOW_DEBUG_LOGS = os.getenv("KATALYST_DEBUG", "false").lower() == "true"

# In get_logger function, conditionally add console handler
if SHOW_DEBUG_LOGS:
    # Console handler for INFO and above (simple)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)
```

#### 1.3 Update Conversation Output

Modify conversation agent to use clean output instead of logger.info().

### Phase 2: Mode System

#### 2.1 Add Mode Tracking

Extend `KatalystState` to include current mode:

```python
class KatalystState(BaseModel):
    # ... existing fields ...
    current_mode: str = Field(default="plan", description="Current operation mode: plan or execute")
    mode_history: List[str] = Field(default_factory=list, description="History of mode switches")
```

#### 2.2 Mode-Specific Behavior

Create mode-aware prompts and behaviors:

- **Plan Mode**: Discussion, analysis, approach planning (no file modifications)
- **Execute Mode**: Full implementation capabilities with all tools

#### 2.3 Keyboard Shortcuts

Implement keyboard handler for mode switching and other shortcuts:
- `Ctrl+M`: Toggle between plan/execute mode
- `Ctrl+L`: Clear screen
- `Ctrl+T`: Show current task list
- `Ctrl+H`: Display help

### Phase 3: Visual Enhancements

#### 3.1 Rich Prompt System

Replace basic prompt with context-aware display:

```
╭─ Katalyst ─────────────────────────────────╮
│ 📝 Plan Mode | Working on: Authentication  │
╰────────────────────────────────────────────╯

> _
```

#### 3.2 Clean Status Updates

Replace verbose logging with clean status indicators:
- Use spinners for operations in progress
- Show progress bars for long-running tasks
- Display completion messages in formatted boxes

#### 3.3 Formatted Output

Use Rich components for structured display:
- Tables for task lists
- Panels for important messages
- Syntax highlighting for code
- Markdown rendering for formatted text

### Phase 4: Enhanced Interactions

#### 4.1 Task Summary Display

Create beautiful task summaries instead of raw output:

```
╭─ Task Completed ───────────────────────────╮
│ ✓ Fixed request_user_input terminal menu   │
│                                            │
│ Changes made:                              │
│ • Modified interrupt condition             │
│ • Cleaned up unused code paths            │
│ • Added fallback for terminal issues      │
│                                            │
│ Files modified: 3                          │
│ Tests passed: All                          │
╰────────────────────────────────────────────╯
```

#### 4.2 Interactive Elements

- Collapsible sections for long output
- Scrollable regions for code previews
- Interactive menus with arrow navigation

## Example: Before vs After

### Before (Current Output)
```
[INFO] [CONVERSATION] Generated response: Hello! I'm Katalyst, your AI coding assistant specialized in software engineering and data science tasks. I can help you with:

- Writing and debugging code
- Refactoring and optimization
- Building features and applications
[DEBUG] ==================== 🚀🚀🚀  KATALYST RUN START  🚀🚀🚀 ====================
[INFO] [MAIN_REPL] Starting new task: 'hello'
[DEBUG] [CONVERSATION] Processing input: hello
```

### After (Clean Output)
```
╭─ Katalyst ─────────────────────────────────╮
│ 📝 Plan Mode | Ready                       │
╰────────────────────────────────────────────╯

> hello

Hello! I'm Katalyst, your AI coding assistant specialized in software 
engineering and data science tasks. I can help you with:

• Writing and debugging code
• Refactoring and optimization  
• Building features and applications
• Data analysis and machine learning
• Testing and documentation

What would you like to work on today?

> _
[Ctrl+M: Execute Mode | Ctrl+H: Help]
```

## Technical Implementation Details

### New Modules Structure
```
src/katalyst/app/ui/
├── ui_output.py       # Clean output handling
├── mode_manager.py    # Mode switching logic
├── keyboard.py        # Keyboard shortcut handling
└── formatters.py      # Output formatting utilities
```

### Configuration Options
- `KATALYST_DEBUG`: Show debug logs in terminal
- `KATALYST_UI_STYLE`: Choose UI theme (minimal, rich, classic)
- `KATALYST_DEFAULT_MODE`: Set default mode (plan or execute)

### Backward Compatibility
- Keep existing functionality intact
- Add `--classic` flag for old-style output
- Gradual migration path for users

## Benefits

1. **Professional Appearance** - Clean, structured output that looks polished
2. **Improved Usability** - Clear modes and intuitive shortcuts
3. **Reduced Noise** - Technical details hidden unless requested
4. **Better Workflow** - Quick context switching between planning and coding
5. **Enhanced Productivity** - Keyboard-driven interface for power users

## Future Enhancements

### Potential Textual Framework Adoption
- Consider migrating to Textual for advanced TUI capabilities
- Support for mouse interactions
- Smooth animations and transitions
- Multiple panes and layouts

### Additional Features
- Split-screen mode for code comparison
- Integrated file browser
- Real-time syntax checking
- Inline documentation viewer

## Migration Strategy

1. **Phase 1** (Week 1-2): Implement clean output system
   - Create ui_output module
   - Update logger configuration
   - Modify conversation agent

2. **Phase 2** (Week 3-4): Add basic mode system
   - Implement mode tracking
   - Create mode-specific behaviors
   - Add mode toggle shortcut

3. **Phase 3** (Week 5-6): Enhance visual presentation
   - Implement rich prompts
   - Add formatted summaries
   - Create status indicators

4. **Phase 4** (Week 7-8): Polish and refine
   - Add remaining shortcuts
   - Implement help system
   - User testing and feedback

## Success Metrics

- Reduced visual clutter (90% less log output in normal operation)
- Faster task completion (keyboard shortcuts reduce friction)
- Improved user satisfaction (cleaner, more professional interface)
- Better discoverability (clear modes and help system)

## Conclusion

This plan transforms Katalyst from a functional but verbose CLI tool into a polished, professional terminal application that rivals the best in class. By focusing on the overall experience rather than just adding animations, we create a tool that developers will enjoy using every day.

The phased approach ensures we can deliver improvements incrementally while maintaining stability and backward compatibility. Each phase provides immediate value while building toward the complete vision of a modern, keyboard-driven terminal interface.