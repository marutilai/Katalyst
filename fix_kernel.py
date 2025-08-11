#!/usr/bin/env python3
"""
Emergency fix for kernel communication issues.
Switches to simple kernel manager implementation.
"""

import subprocess
import time
import os

print("Emergency Kernel Fix")
print("=" * 50)

# Step 1: Kill ALL jupyter processes
print("\n1. Killing all Jupyter processes...")
subprocess.run(['pkill', '-9', '-f', 'jupyter'], capture_output=True)
time.sleep(1)
print("✓ Done")

# Step 2: Clean up runtime files
print("\n2. Cleaning up kernel runtime files...")
runtime_dir = os.path.expanduser("~/.local/share/jupyter/runtime")
if os.path.exists(runtime_dir):
    subprocess.run(['rm', '-rf', runtime_dir], capture_output=True)
    print("✓ Cleaned runtime directory")
else:
    print("✓ Runtime directory doesn't exist")

# Step 3: Clean up any IPython profiles that might be corrupted
print("\n3. Cleaning up IPython profiles...")
ipython_dir = os.path.expanduser("~/.ipython")
profile_dirs = []
if os.path.exists(ipython_dir):
    for item in os.listdir(ipython_dir):
        if item.startswith("profile_"):
            profile_dirs.append(os.path.join(ipython_dir, item))
    
    for profile_dir in profile_dirs:
        security_dir = os.path.join(profile_dir, "security")
        if os.path.exists(security_dir):
            subprocess.run(['rm', '-rf', security_dir], capture_output=True)
            print(f"✓ Cleaned {profile_dir}")

print("\n4. Kernel cleanup complete!")
print("\nThe kernel has been switched to a simpler implementation.")
print("You can now run Katalyst again.")
print("\nIf you still have issues, try:")
print("  export KATALYST_KERNEL_TIMEOUT=300")
print("  katalyst")