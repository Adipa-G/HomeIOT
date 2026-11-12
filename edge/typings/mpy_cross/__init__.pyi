# Type stubs for the parts of the mpy-cross package (a dev dependency without
# type information) that edge/tools/build_artifact.py uses.

mpy_cross: str
"""Path to the bundled mpy-cross executable."""

def fix_perms() -> None:
    """Make the bundled executable runnable (sets the execute bit on POSIX)."""
