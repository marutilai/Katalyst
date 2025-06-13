from typing import Any, List, Optional, TypeVar, Union
from pydantic import BaseModel

T = TypeVar("T")


def load_persisted_state(
    state: Union[BaseModel, dict],
    attr_name: str,
    default_value: T,
    attr_type: Optional[type] = None,
) -> T:
    """
    Load a persisted state attribute from either a Pydantic model or dictionary.

    Args:
        state: The state object (either Pydantic model or dict)
        attr_name: Name of the attribute to load
        default_value: Default value to return if attribute not found
        attr_type: Optional type to cast the loaded value to

    Returns:
        The loaded attribute value or default_value if not found
    """
    if hasattr(state, attr_name):
        value = getattr(state, attr_name)
    elif isinstance(state, dict):
        value = state.get(attr_name, default_value)
    else:
        value = default_value

    if attr_type is not None and value is not None:
        try:
            value = attr_type(value)
        except (TypeError, ValueError):
            return default_value

    return value
