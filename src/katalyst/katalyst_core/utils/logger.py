import logging
import os
import tempfile
from datetime import datetime
from katalyst.katalyst_core.utils.system_info import get_os_info

_LOGGER_NAME = "coding_agent"

# Determine log file location based on OS and add timestamp
os_info = get_os_info()
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
if os_info in ("Linux", "Darwin"):
    _LOG_FILE = f"/tmp/coding_agent_{timestamp}.log"
else:
    _LOG_FILE = os.path.join(tempfile.gettempdir(), f"coding_agent_{timestamp}.log")


def get_logger():
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        # File handler for DEBUG and above (detailed)
        file_handler = logging.FileHandler(_LOG_FILE, mode="a")
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

        print(f"[LOGGER] Logs will be written to: {_LOG_FILE}")

    logger.setLevel(logging.DEBUG)  # Capture everything; handlers filter output
    return logger
