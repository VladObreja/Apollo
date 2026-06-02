"""
Pytest configuration for the Apollo test suite.

Adds `src/` to sys.path so all unit tests can import `apollo.*`
without requiring the package to be installed in the test environment.
"""
import sys
from pathlib import Path

# Make `src/apollo` importable without `pip install -e .`
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
