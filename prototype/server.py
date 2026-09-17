"""Compatibility entry point: python prototype/server.py --port 5190."""
import runpy
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(BACKEND))

if __name__ == "__main__":
    runpy.run_path(str(BACKEND / "server.py"), run_name="__main__")
else:
    # Share the actual module so assignments such as server.DB remain effective.
    import importlib.util
    spec = importlib.util.spec_from_file_location(__name__, BACKEND / "server.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[__name__] = module
    spec.loader.exec_module(module)
