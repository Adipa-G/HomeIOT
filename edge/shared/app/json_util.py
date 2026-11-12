"""Typed views of decoded JSON values.

isinstance() on a json.loads() result narrows Any to dict[Unknown, Unknown] (or
list[Unknown]), which strict type checking rejects. These helpers do the check
once and return the value typed for JSON.
"""

TYPE_CHECKING = False
if TYPE_CHECKING:  # never true on a device; see edge/shared/hal/interfaces.py
    from typing import Any


def as_dict(value: "Any") -> "dict[str, Any] | None":
    """value if it is a JSON object, else None."""
    if isinstance(value, dict):
        # JSON object keys are always str.
        return value  # pyright: ignore[reportUnknownVariableType]
    return None


def as_list(value: "Any") -> "list[Any] | None":
    """value if it is a JSON array, else None."""
    if isinstance(value, list):
        return value  # pyright: ignore[reportUnknownVariableType]
    return None
