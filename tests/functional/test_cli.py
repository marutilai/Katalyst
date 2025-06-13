import subprocess
import shutil


def test_cli_help():
    cli_path = shutil.which("katalyst")
    if cli_path is None:
        raise RuntimeError("katalyst CLI not found in PATH")
    result = subprocess.run([cli_path, "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert (
        "Usage" in result.stdout
        or "usage" in result.stdout
        or "KATALYST" in result.stdout
    )
