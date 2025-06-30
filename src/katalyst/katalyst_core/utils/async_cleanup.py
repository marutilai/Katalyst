"""
Async cleanup utilities to handle pending tasks and avoid warnings.
"""
import asyncio
import atexit
from katalyst.katalyst_core.utils.logger import get_logger


logger = get_logger()


def cleanup_pending_tasks():
    """Clean up any pending async tasks to avoid warnings on exit."""
    try:
        # Get the current event loop if it exists
        loop = asyncio.get_running_loop()
        # Get all pending tasks
        pending = asyncio.all_tasks(loop)
        if pending:
            logger.debug(f"Cleaning up {len(pending)} pending async tasks")
            # Cancel all pending tasks
            for task in pending:
                if not task.done():
                    task.cancel()
            # Give tasks a chance to clean up
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except RuntimeError:
        # No event loop running, try to get one
        try:
            loop = asyncio.get_event_loop()
            if loop and not loop.is_closed():
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    if not task.done():
                        task.cancel()
        except:
            pass
    except Exception as e:
        logger.debug(f"Error during async cleanup: {e}")


# Register cleanup function to run on exit
atexit.register(cleanup_pending_tasks)