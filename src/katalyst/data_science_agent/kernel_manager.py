"""
Jupyter Kernel Manager for Data Science Agent.

Manages the lifecycle of Jupyter kernels for persistent code execution.
"""

import atexit
import signal
import threading
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
    
    @classmethod
    def reset_instance(cls):
        """Force reset the singleton instance (for recovery from errors)."""
        if cls._instance:
            try:
                cls._instance.shutdown()
            except:
                pass
        cls._instance = None
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.logger = get_logger("kernel_manager")
            self.kernel_manager: Optional[KernelManager] = None
            self.kernel_client = None
            self.initialized = True
            self.libraries_installed = False
            self._lock = threading.Lock()  # Prevent concurrent kernel operations
            # Register cleanup on exit
            atexit.register(self.shutdown)
            # Also handle common termination signals
            signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start_kernel(self) -> None:
        """Start a new Jupyter kernel if not already running."""
        # Always clean up any existing kernel first
        if self.kernel_manager:
            if self.kernel_manager.is_alive():
                self.logger.debug("[KERNEL] Kernel already running, cleaning up first")
                self.shutdown()
            else:
                # Clean up dead kernel
                try:
                    if self.kernel_client:
                        self.kernel_client.stop_channels()
                except:
                    pass
                self.kernel_manager = None
                self.kernel_client = None
        
        self.logger.info("[KERNEL] Starting new Jupyter kernel...")
        self.kernel_manager = KernelManager()
        self.kernel_manager.start_kernel()
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        
        # Wait for kernel to be ready
        try:
            self.kernel_client.wait_for_ready(timeout=10)
            self.logger.info("[KERNEL] Jupyter kernel started successfully")
        except Exception as e:
            self.logger.error(f"[KERNEL] Failed to start kernel: {e}")
            self.shutdown()
            raise
        
        # Reset state
        self.libraries_installed = False
    
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
        with self._lock:  # Ensure thread-safe execution
            if not self.kernel_manager or not self.kernel_manager.is_alive():
                self.start_kernel()
            
            # Install libraries on first actual code execution (not during startup)
            if not self.libraries_installed and "import sys" not in code:
                self._ensure_libraries_installed()
            
            # Execute the code
            try:
                msg_id = self.kernel_client.execute(code)
            except Exception as e:
                self.logger.error(f"[KERNEL] Failed to send execute request: {e}")
                # Kernel is likely in bad state, restart it
                self.restart_kernel()
                # Try once more
                msg_id = self.kernel_client.execute(code)
        
        # Collect results
        outputs = []
        errors = []
        data = {}
        
        # Process messages
        while True:
            try:
                msg = self.kernel_client.get_iopub_msg(timeout=timeout)
                
                # Skip if not our message
                if msg.get('parent_header', {}).get('msg_id') != msg_id:
                    continue
                    
                msg_type = msg.get('header', {}).get('msg_type', '')
                content = msg.get('content', {})
                
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
        if self.kernel_manager and self.kernel_manager.is_alive():
            try:
                # Clear any pending messages before restart
                while True:
                    try:
                        self.kernel_client.get_iopub_msg(timeout=0.1)
                    except Empty:
                        break
                
                # Restart the kernel
                self.kernel_manager.restart_kernel()
                
                # Wait for kernel to be ready
                self.kernel_client.wait_for_ready(timeout=20)
                
                # Verify kernel is responsive
                test_result = self.execute_code("print('Kernel restarted successfully')", timeout=10)
                if test_result['success']:
                    self.logger.info("[KERNEL] Kernel restarted and verified")
                else:
                    self.logger.warning("[KERNEL] Kernel restarted but verification failed")
                
                # Reset libraries flag so they get installed on next execution
                self.libraries_installed = False
                
            except Exception as e:
                self.logger.error(f"[KERNEL] Error during restart: {e}")
                # If restart fails, try shutting down and starting fresh
                self.shutdown()
                self.start_kernel()
        else:
            # No kernel running, just start a new one
            self.start_kernel()
    
    def shutdown(self) -> None:
        """Shutdown the kernel and cleanup."""
        if self.kernel_manager:
            self.logger.info("[KERNEL] Shutting down kernel...")
            try:
                # Stop channels first
                if self.kernel_client:
                    try:
                        self.kernel_client.stop_channels()
                    except:
                        pass
                
                # Then shutdown kernel
                if self.kernel_manager.is_alive():
                    self.kernel_manager.shutdown_kernel(now=True)  # Force immediate shutdown
                    
                # Give it a moment to clean up
                import time
                time.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"[KERNEL] Error during shutdown: {e}")
                # Force kill if graceful shutdown fails
                try:
                    if hasattr(self.kernel_manager, 'kernel') and self.kernel_manager.kernel:
                        self.kernel_manager.kernel.kill()
                except:
                    pass
            finally:
                self.kernel_manager = None
                self.kernel_client = None
                self.libraries_installed = False
    
    def is_alive(self) -> bool:
        """Check if kernel is running."""
        return self.kernel_manager is not None and self.kernel_manager.is_alive()
    
    def check_health(self) -> Dict[str, Any]:
        """Check kernel health and responsiveness."""
        if not self.is_alive():
            return {"healthy": False, "reason": "Kernel not running"}
        
        try:
            # Simple health check
            result = self.execute_code("1 + 1", timeout=5)
            if result['success'] and result['outputs'] and '2' in str(result['outputs']):
                return {"healthy": True, "status": "Kernel responsive"}
            else:
                return {"healthy": False, "reason": "Kernel not responding correctly"}
        except Exception as e:
            return {"healthy": False, "reason": f"Health check failed: {str(e)}"}
    
    def _ensure_libraries_installed(self) -> None:
        """Ensure essential libraries are installed (only runs once)."""
        if self.libraries_installed:
            return
            
        self.logger.info("[KERNEL] Installing essential libraries...")
        self.libraries_installed = True  # Set this first to avoid recursion
        
        try:
            # Direct kernel execution to avoid recursion
            install_code = "!pip install -q pandas numpy matplotlib seaborn scikit-learn optuna"
            msg_id = self.kernel_client.execute(install_code)
            
            # Wait for completion with longer timeout
            while True:
                try:
                    msg = self.kernel_client.get_iopub_msg(timeout=60)
                    if msg['parent_header'].get('msg_id') == msg_id:
                        if msg['header']['msg_type'] == 'status' and msg['content']['execution_state'] == 'idle':
                            break
                except Empty:
                    self.logger.warning("[KERNEL] Library installation timed out")
                    break
            
            self.logger.info("[KERNEL] Essential libraries installed")
        except Exception as e:
            self.logger.error(f"[KERNEL] Error installing libraries: {e}")
            self.libraries_installed = False  # Reset on failure
    
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


def restart_jupyter_kernel() -> None:
    """Force restart the Jupyter kernel (useful for recovery)."""
    _kernel_manager.restart_kernel()