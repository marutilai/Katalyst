import subprocess
from katalyst_agent.utils.logger import get_logger
from katalyst_agent.utils.tools import katalyst_tool
import os

@katalyst_tool(prompt_module="execute_command", prompt_var="EXECUTE_COMMAND_PROMPT")
def execute_command(command: str, cwd: str = None, timeout: int = 30, mode: str = None, auto_approve: bool = True) -> str:
    """
    Executes a shell command in the terminal.
    Parameters:
      - command: str (the CLI command to execute)
      - cwd: str (optional, working directory)
      - timeout: int (optional, seconds to wait before killing the process)
      - mode: str ("architect" or "code", default "code")
      - auto_approve: bool (default False)
    Returns a string detailing the command output, error, or user denial with feedback.
    """
    logger = get_logger()
    logger.info(f"Entered execute_command with command={command}, cwd={cwd}, timeout={timeout}, mode={mode}, auto_approve={auto_approve}")

    # Restrict command execution in architect mode
    if mode == "architect":
        logger.error("execute_command is not available in architect mode.")
        return "[ERROR] execute_command is not available in architect mode."

    # Validate command
    if not command or not isinstance(command, str):
        logger.error("No valid 'command' provided to execute_command.")
        return "[ERROR] No valid 'command' provided."

    # Validate and resolve working directory
    if cwd:
        absolute_cwd = os.path.abspath(cwd)
        if not os.path.isdir(absolute_cwd):
            logger.error(f"The specified 'cwd': '{cwd}' is not a valid directory.")
            return f"[ERROR] The specified 'cwd': '{cwd}' is not a valid directory. Please provide a valid directory."
    else:
        absolute_cwd = os.getcwd()

    # Set default timeout if not provided
    if timeout is None:
        timeout = 3600

    # Print a formatted preview of the command to the user
    print(f"\n# Katalyst is about to execute the command: '{command}' inside '{absolute_cwd}' for {timeout} seconds.\n")
    print("-" * 80)
    print(f"> {command}")
    print("-" * 80)

    # Ask for user confirmation unless auto_approve is set
    if not auto_approve:
        confirm = input("Allow Katalyst to run the above command? (y/n): ").strip().lower()
        if confirm != 'y':
            feedback = input("Instruct Katalyst on what to do instead as you have rejected the command execution: ").strip()
            logger.info("User denied permission to execute command.")
            # Return a string with denial and user feedback
            return (
                f"[USER_DENIAL] User denied permission to execute command: '{command}' in '{absolute_cwd}'.\n"
                f"User instruction: <instruction>{feedback}</instruction>"
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
            check=False
        )
        logger.info(f"Command '{command}' executed with return code {result.returncode}")
        # Collect stdout and stderr for output
        output_str = ""
        if result.stdout:
            output_str += f"Stdout:\n{result.stdout.strip()}\n"
        if result.stderr:
            output_str += f"Stderr:\n{result.stderr.strip()}\n"
        # Return success or error message based on return code
        if result.returncode == 0:
            final_output = f"[SUCCESS] Command '{command}' executed successfully.\n"
            final_output += output_str if output_str.strip() else "No output."
            logger.info("Exiting execute_command successfully.")
            return final_output.strip()
        else:
            error_message = f"[ERROR] Command '{command}' failed with code {result.returncode}.\n"
            error_message += output_str if output_str.strip() else "No specific error output on stdout/stderr."
            logger.error(error_message)
            return error_message.strip()
    except subprocess.TimeoutExpired:
        logger.error(f"Command '{command}' timed out after {timeout} seconds.")
        return f"[ERROR] Command '{command}' timed out after {timeout} seconds."
    except FileNotFoundError:
        logger.error(f"Command not found: {command.split()[0]}")
        return f"[ERROR] Command not found: {command.split()[0]}. Please ensure it's installed and in PATH."
    except Exception as e:
        logger.exception(f"Error executing command '{command}'.")
        return f"[ERROR] An unexpected error occurred while executing command '{command}': {e}"
