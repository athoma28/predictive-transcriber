# app/config.py
from pydantic import BaseModel

class ModelSpec(BaseModel):
    id: str
    order: int
    char: bool
    hotkey: str
    # remove the smooth field entirely or default to "kneser"

MODELS = [
    ModelSpec(id="w5", order=5, char=False, hotkey="Tab"),
    ModelSpec(id="w3", order=3, char=False, hotkey="Ctrl+1"),   # ← no smooth
    ModelSpec(id="c6", order=6, char=True,  hotkey="Ctrl+2"),
]
