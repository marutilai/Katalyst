import platform

def get_os_info():
    """Return the current operating system name (e.g., 'Linux', 'Darwin', 'Windows')."""
    return platform.system()

os_info = get_os_info() 