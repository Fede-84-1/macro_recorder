from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

from loguru import logger

from .constants import MACROS_FILE, SETTINGS_FILE, DEFAULT_SETTINGS
from .models import Macro


def _read_json(path: Path) -> Dict:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.exception("Failed to read JSON {}: {}", path, exc)
        return {}


def _write_json(path: Path, data: Dict) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        logger.exception("Failed to write JSON {}: {}", path, exc)


def load_settings() -> Dict:
    data = _read_json(SETTINGS_FILE)
    if not data:
        data = DEFAULT_SETTINGS.copy()
        save_settings(data)
    # ensure defaults
    for k, v in DEFAULT_SETTINGS.items():
        data.setdefault(k, v)
    return data


def save_settings(settings: Dict) -> None:
    _write_json(SETTINGS_FILE, settings)


def load_macros() -> List[Macro]:
    data = _read_json(MACROS_FILE)
    macros_raw = data.get("macros", [])
    macros = [Macro.from_dict(m) for m in macros_raw]
    return macros


def save_macros(macros: List[Macro]) -> None:
    data = {"macros": [m.to_dict() for m in macros], "saved_at": int(time.time())}
    _write_json(MACROS_FILE, data)


def next_recording_title(existing: List[Macro]) -> Tuple[str, str]:
    numbers = sorted(
        [int(m.title.split(" ")[-1]) for m in existing if m.title.startswith("Registrazione n.") and m.title.split(" ")[-1].isdigit()]
    )
    n = 1
    for num in numbers:
        if num == n:
            n += 1
        elif num > n:
            break
    rec_id = f"rec-{int(time.time()*1000)}"
    return rec_id, f"Registrazione n.{n}"

