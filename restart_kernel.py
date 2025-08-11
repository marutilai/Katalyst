#!/usr/bin/env python3
"""
Utility script to restart the Jupyter kernel used by Katalyst.

This can help resolve kernel timeout issues.
"""

import sys
import subprocess
import time
sys.path.insert(0, 'src')

from katalyst.data_science_agent.kernel_manager import get_kernel_manager, restart_jupyter_kernel, JupyterKernelManager
from katalyst.katalyst_core.utils.logger import get_logger

logger = get_logger("kernel_restart")

def main():
    print("Cleaning up Jupyter kernels...")
    
    # First, kill any existing jupyter kernels
    try:
        subprocess.run(['pkill', '-f', 'jupyter-kernel'], capture_output=True)
        print("✓ Killed existing Jupyter kernel processes")
        time.sleep(1)  # Give processes time to die
    except Exception as e:
        print(f"Warning: Could not kill kernel processes: {e}")
    
    # Reset the singleton instance completely
    print("\nResetting kernel manager...")
    JupyterKernelManager.reset_instance()
    print("✓ Kernel manager reset")
    
    # Now get a fresh instance
    print("\nStarting fresh kernel manager...")
    kernel_manager = get_kernel_manager()
    
    # Force shutdown regardless of state
    try:
        kernel_manager.shutdown()
        print("✓ Kernel manager shutdown complete")
    except Exception as e:
        print(f"Warning during shutdown: {e}")
    
    # Start fresh
    print("\nStarting fresh kernel...")
    try:
        kernel_manager.start_kernel()
    
        print("✓ Kernel started successfully")
    except Exception as e:
        print(f"✗ Failed to start kernel: {e}")
        return
    
    # Test it
    print("\nTesting kernel...")
    health = kernel_manager.check_health()
    
    if health['healthy']:
        print("✓ Kernel is responsive")
        
        # Test pandas import
        print("\nTesting pandas import...")
        result = kernel_manager.execute_code("import pandas as pd; print('Pandas version:', pd.__version__)", timeout=30)
        if result['success']:
            print("✓ Pandas imported successfully")
            if result['outputs']:
                print(f"  {result['outputs'][0]}")
        else:
            print("✗ Failed to import pandas")
            if result['errors']:
                print(f"  Error: {result['errors'][0]['ename']}: {result['errors'][0]['evalue']}")
    else:
        print(f"✗ Kernel health check failed: {health['reason']}")
        
    print("\nKernel restart complete. You can now run Katalyst.")

if __name__ == "__main__":
    main()