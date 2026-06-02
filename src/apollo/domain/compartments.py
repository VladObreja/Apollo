"""
Compartment boundary definitions and enforcement decorator.

The @requires decorator is currently a non-functional stub that documents
capability boundaries in code. Full Postgres RLS / role isolation will be
wired in a future story. The decorator contract is final — do not remove it.
"""

from enum import Enum
from functools import wraps
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable[..., object])


class Compartment(Enum):
    """Compartment labels for double-blind capability enforcement."""

    TARGET_WRITE = "target_write"
    TARGET_READ = "target_read"
    EXTRACTION_WRITE = "extraction_write"
    CALIBRATION_READ = "calibration_read"


def requires(compartment: Compartment) -> Callable[[F], F]:
    """
    Enforce that the caller holds the given compartment capability.

    Stub implementation — logs boundary intent. Full RLS enforcement
    (Postgres role checks) will replace this body in a future story.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> object:
            # TODO(compartment-guard): assert active Postgres role matches compartment
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
