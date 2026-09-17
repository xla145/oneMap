"""Run backend unit tests from any working directory using the active Python."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "test"))

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.discover(str(ROOT / "test"), pattern="test*.py")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    sys.exit(not result.wasSuccessful())
