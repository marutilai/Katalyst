"""
Jupyter Kernel Manager for Data Science Agent.

Manages the lifecycle of Jupyter kernels for persistent code execution.
"""

import atexit
import signal
from typing import Optional, Dict, Any
from jupyter_client import KernelManager
from queue import Empty

from katalyst.katalyst_core.utils.logger import get_logger


class JupyterKernelManager:
    """Singleton manager for Jupyter kernels."""
    
    _instance: Optional['JupyterKernelManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.logger = get_logger("kernel_manager")
            self.kernel_manager: Optional[KernelManager] = None
            self.kernel_client = None
            self.initialized = True
            # Register cleanup on exit
            atexit.register(self.shutdown)
            # Also handle common termination signals
            signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start_kernel(self) -> None:
        """Start a new Jupyter kernel if not already running."""
        if self.kernel_manager and self.kernel_manager.is_alive():
            self.logger.debug("[KERNEL] Kernel already running")
            return
        
        self.logger.info("[KERNEL] Starting new Jupyter kernel...")
        self.kernel_manager = KernelManager()
        self.kernel_manager.start_kernel()
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        
        # Wait for kernel to be ready
        self.kernel_client.wait_for_ready(timeout=10)
        self.logger.info("[KERNEL] Jupyter kernel started successfully")
        
        # Get kernel info for debugging
        try:
            info_result = self.execute_code("import sys; print(f'Python: {sys.version}'); print(f'Executable: {sys.executable}')", timeout=10)
            if info_result['outputs']:
                self.logger.debug(f"[KERNEL] Kernel environment info: {' '.join(info_result['outputs'])}")
        except Exception as e:
            self.logger.debug(f"[KERNEL] Could not get kernel info: {e}")
        
        # Install essential data science libraries
        self._install_essential_libraries()
    
    def execute_code(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute code in the kernel and return results.
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            Dict with:
                - success: bool
                - outputs: List of output strings
                - errors: List of error dicts
                - data: Dict of rich outputs (images, etc)
        """
        if not self.kernel_manager or not self.kernel_manager.is_alive():
            self.start_kernel()
        
        # Execute the code
        msg_id = self.kernel_client.execute(code)
        
        # Collect results
        outputs = []
        errors = []
        data = {}
        
        # Process messages
        while True:
            try:
                msg = self.kernel_client.get_iopub_msg(timeout=timeout)
                msg_type = msg['header']['msg_type']
                content = msg['content']
                
                if msg['parent_header'].get('msg_id') != msg_id:
                    continue
                
                if msg_type == 'stream':
                    # stdout/stderr
                    outputs.append(content['text'])
                    
                elif msg_type == 'error':
                    # Execution error
                    error_info = {
                        'ename': content['ename'],
                        'evalue': content['evalue'],
                        'traceback': content['traceback']
                    }
                    errors.append(error_info)
                    self.logger.debug(f"[KERNEL] Execution error: {error_info['ename']}: {error_info['evalue']}")
                    
                elif msg_type == 'execute_result':
                    # Expression result
                    if 'text/plain' in content['data']:
                        outputs.append(content['data']['text/plain'])
                    data.update(content['data'])
                    
                elif msg_type == 'display_data':
                    # Rich display (plots, etc)
                    data.update(content['data'])
                    
                elif msg_type == 'status':
                    # Kernel status
                    if content['execution_state'] == 'idle':
                        break
                        
            except Empty:
                # Timeout
                self.logger.warning(f"[KERNEL] Code execution timed out after {timeout}s")
                errors.append({
                    'ename': 'TimeoutError',
                    'evalue': f'Code execution exceeded {timeout} seconds',
                    'traceback': []
                })
                break
            except Exception as e:
                self.logger.error(f"[KERNEL] Error during execution: {e}")
                errors.append({
                    'ename': type(e).__name__,
                    'evalue': str(e),
                    'traceback': []
                })
                break
        
        return {
            'success': len(errors) == 0,
            'outputs': outputs,
            'errors': errors,
            'data': data
        }
    
    def restart_kernel(self) -> None:
        """Restart the kernel to clear state."""
        self.logger.info("[KERNEL] Restarting kernel...")
        if self.kernel_manager:
            self.kernel_manager.restart_kernel()
            self.kernel_client.wait_for_ready(timeout=10)
        self.logger.info("[KERNEL] Kernel restarted")
    
    def shutdown(self) -> None:
        """Shutdown the kernel and cleanup."""
        if self.kernel_manager and self.kernel_manager.is_alive():
            self.logger.info("[KERNEL] Shutting down kernel...")
            try:
                self.kernel_client.stop_channels()
                self.kernel_manager.shutdown_kernel(now=True)  # Force immediate shutdown
            except Exception as e:
                self.logger.error(f"[KERNEL] Error during shutdown: {e}")
            finally:
                self.kernel_manager = None
                self.kernel_client = None
    
    def is_alive(self) -> bool:
        """Check if kernel is running."""
        return self.kernel_manager is not None and self.kernel_manager.is_alive()
    
    def _install_essential_libraries(self) -> None:
        """Install essential data science libraries in the kernel."""
        essential_libs = ['pandas', 'numpy', 'matplotlib', 'seaborn', 'scikit-learn', 'optuna']
        
        # First check which libraries are missing
        check_code = f"""
import importlib
missing_libs = []
for lib in {essential_libs}:
    try:
        if lib == 'scikit-learn':
            importlib.import_module('sklearn')
        else:
            importlib.import_module(lib)
    except ImportError:
        missing_libs.append(lib)
print(f"Missing libraries: {{missing_libs}}")
"""
        
        result = self.execute_code(check_code, timeout=30)
        
        # Install missing libraries
        if result['outputs']:
            output = ' '.join(result['outputs'])
            if 'Missing libraries: []' not in output:
                self.logger.info("[KERNEL] Installing missing data science libraries...")
                install_code = "!pip install -q " + " ".join(essential_libs)
                install_result = self.execute_code(install_code, timeout=60)
                
                if install_result['errors']:
                    self.logger.warning(f"[KERNEL] Error installing libraries: {install_result['errors']}")
                else:
                    self.logger.info("[KERNEL] Essential libraries installed successfully")
    
    def _signal_handler(self, signum, frame):
        """Handle termination signals by shutting down the kernel."""
        self.logger.info(f"[KERNEL] Received signal {signum}, shutting down kernel...")
        self.shutdown()
        # Re-raise the signal to let the default handler run
        signal.signal(signum, signal.SIG_DFL)
        signal.raise_signal(signum)


# Global instance
_kernel_manager = JupyterKernelManager()


def get_kernel_manager() -> JupyterKernelManager:
    """Get the global kernel manager instance."""
    return _kernel_manager