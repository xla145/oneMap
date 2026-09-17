"""Read-only adapter for the user-supplied NMG demo. No production resource registration."""
from pathlib import Path
from functools import lru_cache
from copy import deepcopy
import json

SCENE_ID='nmg-reference-demo'
ROOT=Path(__file__).resolve().parents[1]/'assets'/'nmg-demo'/'data'

@lru_cache(maxsize=1)
def data():
    return json.loads((ROOT/'runtime.json').read_text())

def runtime():
    return deepcopy(data())
