"""
Simple Jupyter Kernel Manager - minimal implementation to avoid communication issues.
"""

import os
import time
from typing import Dict, Any, Optional
from jupyter_client import KernelManager
from queue import Empty

from katalyst.katalyst_core.utils.logger import get_logger


class SimpleKernelManager:
    """Simple kernel manager without complex state management."""
    
    def __init__(self):
        self.logger = get_logger("kernel_manager")
        self.kernel_manager: Optional[KernelManager] = None
        self.kernel_client = None
    
    def ensure_kernel(self) -> None:
        """Ensure kernel is running."""
        if self.kernel_manager and self.kernel_manager.is_alive():
            return
        
        # Clean up any old kernel
        if self.kernel_manager:
            try:
                if self.kernel_client:
                    self.kernel_client.stop_channels()
                self.kernel_manager.shutdown_kernel(now=True)
                time.sleep(0.5)
            except:
                pass
            self.kernel_manager = None
            self.kernel_client = None
        
        # Start fresh kernel
        self.logger.info("[KERNEL] Starting new Jupyter kernel...")
        self.kernel_manager = KernelManager()
        self.kernel_manager.start_kernel()
        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        
        # Wait for kernel to be ready
        self.kernel_client.wait_for_ready(timeout=10)
        self.logger.info("[KERNEL] Kernel started successfully")
    
    def execute_code(self, code: str, timeout: int = 120) -> Dict[str, Any]:
        """Execute code in the kernel."""
        # Ensure kernel is running
        self.ensure_kernel()
        
        # Get timeout from environment if set
        env_timeout = os.getenv('KATALYST_KERNEL_TIMEOUT')
        if env_timeout:
            try:
                timeout = int(env_timeout)
            except ValueError:
                pass
        
        # Execute the code
        msg_id = self.kernel_client.execute(code)
        
        # Collect results
        outputs = []
        errors = []
        data = {}
        
        # Process messages with timeout
        start_time = time.time()
        while True:
            try:
                # Check total timeout
                if time.time() - start_time > timeout:
                    self.logger.warning(f"[KERNEL] Code execution timed out after {timeout}s")
                    errors.append({
                        'ename': 'TimeoutError',
                        'evalue': f'Code execution exceeded {timeout} seconds',
                        'traceback': []
                    })
                    break
                
                # Get message with short timeout
                msg = self.kernel_client.get_iopub_msg(timeout=1)
                
                # Skip if not our message
                if msg.get('parent_header', {}).get('msg_id') != msg_id:
                    continue
                
                msg_type = msg.get('header', {}).get('msg_type', '')
                content = msg.get('content', {})
                
                if msg_type == 'stream':
                    outputs.append(content.get('text', ''))
                elif msg_type == 'error':
                    errors.append({
                        'ename': content.get('ename', 'Error'),
                        'evalue': content.get('evalue', 'Unknown error'),
                        'traceback': content.get('traceback', [])
                    })
                elif msg_type == 'execute_result':
                    if 'text/plain' in content.get('data', {}):
                        outputs.append(content['data']['text/plain'])
                    data.update(content.get('data', {}))
                elif msg_type == 'display_data':
                    data.update(content.get('data', {}))
                elif msg_type == 'status':
                    if content.get('execution_state') == 'idle':
                        break
                        
            except Empty:
                # Continue waiting for messages
                continue
            except Exception as e:
                self.logger.error(f"[KERNEL] Error processing message: {e}")
                errors.append({
                    'ename': 'KernelError',
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
        """Restart the kernel."""
        self.logger.info("[KERNEL] Restarting kernel...")
        if self.kernel_manager:
            try:
                self.kernel_client.stop_channels()
                self.kernel_manager.shutdown_kernel(now=True)
                time.sleep(0.5)
            except:
                pass
            self.kernel_manager = None
            self.kernel_client = None
        
        # Start fresh
        self.ensure_kernel()
    
    def shutdown(self) -> None:
        """Shutdown the kernel."""
        if self.kernel_manager:
            self.logger.info("[KERNEL] Shutting down kernel...")
            try:
                if self.kernel_client:
                    self.kernel_client.stop_channels()
                if self.kernel_manager.is_alive():
                    self.kernel_manager.shutdown_kernel(now=True)
            except:
                pass
            finally:
                self.kernel_manager = None
                self.kernel_client = None


# Create a simple global instance
_simple_kernel_manager = SimpleKernelManager()


def get_kernel_manager() -> SimpleKernelManager:
    """Get the kernel manager instance."""
    return _simple_kernel_manager