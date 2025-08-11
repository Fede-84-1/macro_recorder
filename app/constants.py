from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from platformdirs import user_data_dir

APP_NAME = "MacroRecorder"
APP_AUTHOR = "MacroRecorder"

DATA_DIR: Path = Path(user_data_dir(APP_NAME, APP_AUTHOR))
DATA_DIR.mkdir(parents=True, exist_ok=True)

MACROS_FILE: Path = DATA_DIR / "macros.json"
SETTINGS_FILE: Path = DATA_DIR / "settings.json"

DEFAULT_HOTKEYS = {
    "toggle_record": "<ctrl>+<alt>+r",
    "toggle_window": "<ctrl>+<alt>+m",
    "quick_execute": "<ctrl>+<alt>+e",
}

DEFAULT_SETTINGS = {
    "hotkeys": DEFAULT_HOTKEYS,
    "ui": {"theme": "light"},
}

@dataclass
class PlaybackOptions:
    with_pauses: bool = True
    repetitions: int = 1

