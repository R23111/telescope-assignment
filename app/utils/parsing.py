"""
Utility functions for safely converting string inputs from various sources
(e.g. CSV or JSON) into typed Python values. Especially useful when importing
datasets where fields may be empty, malformed, or inconsistent.
"""


import contextlib
from typing import Any


def number_or_none(value, number_type=float) -> Any:
    """Attempts to convert a value to a specified numeric type, returning None
    on failure.

    This function is useful for safely parsing numbers from user input or
    external sources.

    Args:
        value: The value to convert to a number.
        number_type: The numeric type to convert to (default is float).

    Returns:
        The converted number if successful, otherwise None.
    """
    with contextlib.suppress(ValueError, TypeError):
        return number_type(value)
    return None
