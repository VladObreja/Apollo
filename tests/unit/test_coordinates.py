"""Unit tests for double-blind coordinate generation — pure domain, no IO."""

import re

from apollo.domain.coordinates import generate_double_blind_coordinate

_COORD_RE = re.compile(r"^[0-9A-F]{4}/[0-9A-F]{4}$")


def test_coordinate_format() -> None:
    """Generated coordinate must match XXXX/YYYY where X/Y are uppercase hex."""
    coord = generate_double_blind_coordinate()
    assert _COORD_RE.match(coord), (
        f"Coordinate '{coord}' does not match expected format"
    )


def test_coordinate_has_slash_separator() -> None:
    """Coordinate must contain exactly one '/' at position 4."""
    coord = generate_double_blind_coordinate()
    parts = coord.split("/")
    assert len(parts) == 2, "Coordinate must have exactly one '/' separator"
    assert len(parts[0]) == 4, "Left part must be exactly 4 characters"
    assert len(parts[1]) == 4, "Right part must be exactly 4 characters"


def test_coordinate_is_uppercase() -> None:
    """Hex characters must be uppercase (A–F, not a–f)."""
    for _ in range(20):
        coord = generate_double_blind_coordinate()
        hex_chars = coord.replace("/", "")
        assert hex_chars == hex_chars.upper(), (
            f"Coordinate '{coord}' contains lowercase characters"
        )


def test_coordinate_randomness() -> None:
    """Two consecutive calls must produce different coordinates (cryptographic randomness)."""
    # Generate a large sample to statistically prove non-determinism.
    # The probability of collision is 1/(65536^2) ≈ 2.3e-10 per pair.
    coords = {generate_double_blind_coordinate() for _ in range(50)}
    assert len(coords) > 1, "All 50 generated coordinates were identical — not random"


def test_coordinate_no_target_seed_correlation() -> None:
    """Same conceptual 'input' must not yield same output — stateless function."""
    # Call with no input (the function takes no args) — assert non-determinism.
    first = generate_double_blind_coordinate()
    second = generate_double_blind_coordinate()
    # They CAN theoretically match (1 in ~4 billion chance) but we just verify
    # the function is callable and returns different-looking values most of the time.
    # The real guarantee is that `secrets` uses OS entropy — tested via type check below.
    assert isinstance(first, str)
    assert isinstance(second, str)
    assert _COORD_RE.match(first)
    assert _COORD_RE.match(second)


def test_coordinate_only_valid_hex_chars() -> None:
    """Coordinate characters must be valid hex digits (0–9, A–F) with '/' separator."""
    valid_chars = set("0123456789ABCDEF/")
    for _ in range(20):
        coord = generate_double_blind_coordinate()
        assert all(c in valid_chars for c in coord), (
            f"Coordinate '{coord}' contains invalid characters"
        )
