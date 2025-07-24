import logging
import os
import tempfile
from datetime import datetime
from katalyst.katalyst_core.utils.system_info import get_os_info

# Cache for loggers by name
_LOGGERS = {}

def get_logger(agent_name: str = "katalyst"):
    """
    Get a logger instance for the specified agent.
    
    Args:
        agent_name: Name of the agent (e.g., "coding_agent", "data_science_agent", "supervisor")
                   Defaults to "katalyst" for backward compatibility.
    
    Returns:
        Logger instance configured for the agent
    """
    # Return cached logger if it exists
    if agent_name in _LOGGERS:
        return _LOGGERS[agent_name]
    
    # Create new logger
    logger = logging.getLogger(agent_name)
    if not logger.handlers:
        # Determine log file location based on OS and add timestamp
        os_info = get_os_info()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if os_info in ("Linux", "Darwin"):
            log_file = f"/tmp/{agent_name}_{timestamp}.log"
        else:
            log_file = os.path.join(tempfile.gettempdir(), f"{agent_name}_{timestamp}.log")
        
        # File handler for DEBUG and above (detailed)
        file_handler = logging.FileHandler(log_file, mode="a")
        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s (%(module)s.%(funcName)s:%(lineno)d): %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)

        # Console handler for INFO and above (simple)
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        logger.addHandler(console_handler)

        print(f"[LOGGER] Logs will be written to: {log_file}")

    logger.setLevel(logging.DEBUG)  # Capture everything; handlers filter output
    
    # Cache the logger
    _LOGGERS[agent_name] = logger
    
    return logger
