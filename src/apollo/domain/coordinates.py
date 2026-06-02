"""
Double-blind coordinate generation for Apollo.

Pure domain logic — no database or service imports.
Uses cryptographic entropy from the OS to generate stateless,
session-agnostic coordinates that cannot be reverse-engineered.
"""

import secrets


def generate_double_blind_coordinate() -> str:
    """Generate a cryptographically random double-blind coordinate.

    Format: ``8A2F/9B4C`` — 4 uppercase hex chars, slash, 4 uppercase hex chars.

    The coordinate is completely stateless and independent of any target
    identity. Even if the same target is used in multiple sessions, each
    call produces a distinct, unpredictable coordinate.

    Returns:
        A string in the form ``XXXX/YYYY`` where X and Y are uppercase
        hexadecimal digits (0–9, A–F).
    """
    part_a = secrets.token_hex(2).upper()  # 4 hex chars
    part_b = secrets.token_hex(2).upper()  # 4 hex chars
    return f"{part_a}/{part_b}"
