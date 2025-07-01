import subprocess
from katalyst.katalyst_core.utils.logger import get_logger
from katalyst.katalyst_core.utils.tools import katalyst_tool
import os
import json


def format_execute_command_response(
    success: bool,
    command: str,
    cwd: str,
    stdout: str = None,
    stderr: str = None,
    error: str = None,
    user_instruction: str = None,
) -> str:
    """
    Standardizes the output as a JSON string for downstream processing.
    """
    resp = {"success": success, "command": command, "cwd": cwd}
    if stdout:
        resp["stdout"] = stdout
    if stderr:
        resp["stderr"] = stderr
    if error:
        resp["error"] = error
    if user_instruction:
        resp["user_instruction"] = user_instruction
    return json.dumps(resp)


@katalyst_tool(prompt_module="execute_command", prompt_var="EXECUTE_COMMAND_TOOL_PROMPT")
def execute_command(
    command: str,
    cwd: str = None,
    timeout: int = 30,
    auto_approve: bool = True,
    user_input_fn=None,
) -> str:
    """
    Executes a shell command in the terminal.
    Parameters:
      - command: str (the CLI command to execute)
      - cwd: str (optional, working directory)
      - timeout: int (optional, seconds to wait before killing the process)
      - auto_approve: bool (default False)
    Returns a JSON string detailing the command output, error, or user denial with feedback.
    """
    logger = get_logger()
    logger.debug(
        f"Entered execute_command with command={command}, cwd={cwd}, timeout={timeout}, auto_approve={auto_approve}"
    )

    # Validate command
    if not command or not isinstance(command, str):
        logger.error("No valid 'command' provided to execute_command.")
        return format_execute_command_response(
            False,
            command or "",
            cwd or os.getcwd(),
            error="No valid 'command' provided.",
        )

    # Validate and resolve working directory
    if cwd:
        absolute_cwd = os.path.abspath(cwd)
        if not os.path.isdir(absolute_cwd):
            logger.error(f"The specified 'cwd': '{cwd}' is not a valid directory.")
            return format_execute_command_response(
                False,
                command,
                cwd,
                error=f"The specified 'cwd': '{cwd}' is not a valid directory. Please provide a valid directory.",
            )
    else:
        absolute_cwd = os.getcwd()

    # Set default timeout if not provided
    if timeout is None:
        timeout = 3600

    # Print a formatted preview of the command to the user
    print(
        f"\n# Katalyst is about to execute the command: '{command}' inside '{absolute_cwd}' for {timeout} seconds.\n"
    )
    print("-" * 80)
    print(f"> {command}")
    print("-" * 80)

    # Ask for user confirmation unless auto_approve is set
    if not auto_approve:
        if user_input_fn is None:
            user_input_fn = input
        confirm = (
            user_input_fn("Allow Katalyst to run the above command? (y/n): ")
            .strip()
            .lower()
        )
        if confirm != "y":
            feedback = user_input_fn(
                "Instruct Katalyst on what to do instead as you have rejected the command execution: "
            ).strip()
            logger.info("User denied permission to execute command.")
            return format_execute_command_response(
                False, command, absolute_cwd, user_instruction=feedback
            )

    try:
        # Run the command using subprocess
        result = subprocess.run(
            command,
            shell=True,
            cwd=absolute_cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        logger.info(
            f"Command '{command}' executed with return code {result.returncode}"
        )
        # Collect stdout and stderr for output
        stdout = result.stdout.strip() if result.stdout else None
        stderr = result.stderr.strip() if result.stderr else None
        if result.returncode == 0:
            logger.debug("Exiting execute_command successfully.")
            return format_execute_command_response(
                True, command, absolute_cwd, stdout=stdout, stderr=stderr
            )
        else:
            error_message = f"Command '{command}' failed with code {result.returncode}."
            logger.error(error_message)
            return format_execute_command_response(
                False,
                command,
                absolute_cwd,
                stdout=stdout,
                stderr=stderr,
                error=error_message,
            )
    except subprocess.TimeoutExpired:
        logger.error(f"Command '{command}' timed out after {timeout} seconds.")
        return format_execute_command_response(
            False,
            command,
            absolute_cwd,
            error=f"Command '{command}' timed out after {timeout} seconds.",
        )
    except FileNotFoundError:
        logger.error(f"Command not found: {command.split()[0]}")
        return format_execute_command_response(
            False,
            command,
            absolute_cwd,
            error=f"Command not found: {command.split()[0]}. Please ensure it's installed and in PATH.",
        )
    except Exception as e:
        logger.exception(f"Error executing command '{command}'.")
        return format_execute_command_response(
            False,
            command,
            absolute_cwd,
            error=f"An unexpected error occurred while executing command '{command}': {e}",
        )
    finally:
        logger.debug("Exiting execute_command")
