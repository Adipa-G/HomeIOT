import types
from typing import Any


def fake_module(name: str, **attrs: Any) -> Any:
    """Stand-in for a MicroPython-only module (machine, network, ...).

    Typed as Any so tests can attach attributes the type checker cannot know about.
    """
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    return module
