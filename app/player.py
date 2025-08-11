from __future__ import annotations

import threading
import time
from typing import Iterable, Set, Any

from loguru import logger
import keyboard  # type: ignore

from .models import Event, KeyEvent, MouseEvent, Macro
from .wininput import move_cursor_abs, mouse_down, mouse_up, mouse_click, mouse_wheel, get_cursor_pos

try:
    import pydirectinput  # type: ignore
    _HAS_PYDIRECT = True
except Exception:
    _HAS_PYDIRECT = False

try:
    import pyautogui  # type: ignore
    _HAS_PYAUTOGUI = True
except Exception:
    _HAS_PYAUTOGUI = False

try:
    from .winmsg import post_click_at_screen  # type: ignore
    _HAS_WINMSG = True
except Exception:
    _HAS_WINMSG = False


def _normalize_button_name(btn: Any | None) -> str:
    if btn is None:
        return "left"
    try:
        n = int(str(btn))
        if n == 1:
            return "left"
        if n == 2:
            return "right"
        if n == 3:
            return "middle"
    except Exception:
        pass
    s = str(btn).strip().lower()
    if "left" in s or s in ("l",):
        return "left"
    if "right" in s or s in ("r",):
        return "right"
    if "middle" in s or "wheel" in s or s in ("m",):
        return "middle"
    return "left"


class Player:
    def __init__(self) -> None:
        self._stop_flag = threading.Event()
        self._pressed_keys: Set[str] = set()

    def stop(self) -> None:
        self._stop_flag.set()

    def play(self, events: Iterable[Event], with_pauses: bool = True, repetitions: int = 1, macro: Macro | None = None) -> None:
        self._stop_flag.clear()
        self._pressed_keys.clear()
        preserve_cursor = bool(getattr(macro, "preserve_cursor", False))
        original_pos = get_cursor_pos() if preserve_cursor else None
        try:
            for rep in range(max(1, int(repetitions))):
                logger.info("Playback repetition {}", rep + 1)
                for ev in events:
                    if self._stop_flag.is_set():
                        return
                    if with_pauses and getattr(ev, "time_delta_ms", 0):
                        time.sleep(max(0, ev.time_delta_ms) / 1000.0)
                    self._play_event(ev, preserve_cursor)
        finally:
            self._release_stuck_keys()
            if preserve_cursor and original_pos is not None:
                move_cursor_abs(original_pos[0], original_pos[1])

    def _play_event(self, ev: Event, preserve_cursor: bool) -> None:
        if isinstance(ev, KeyEvent):
            self._play_key(ev)
        elif isinstance(ev, MouseEvent):
            self._play_mouse(ev, preserve_cursor)

    def _play_key(self, ev: KeyEvent) -> None:
        key = ev.key
        try:
            if ev.action == "press":
                keyboard.press(key)
                self._pressed_keys.add(key)
            elif ev.action == "release":
                keyboard.release(key)
                self._pressed_keys.discard(key)
        except Exception:
            pass

    def _safe_move(self, x: int, y: int, preserve_cursor: bool) -> None:
        if not preserve_cursor:
            move_cursor_abs(x, y)
            time.sleep(0.02)

    def _play_mouse(self, ev: MouseEvent, preserve_cursor: bool) -> None:
        # Stealth click via PostMessage se possibile
        if preserve_cursor and ev.action in ("press", "release", "click") and _HAS_WINMSG:
            btn = _normalize_button_name(ev.button)
            try:
                if post_click_at_screen(ev.x, ev.y, btn):
                    return
            except Exception:
                pass
        try:
            if ev.action == "move":
                self._safe_move(ev.x, ev.y, preserve_cursor)
                return
            if ev.action in ("press", "release"):
                btn = _normalize_button_name(ev.button)
                self._safe_move(ev.x, ev.y, preserve_cursor)
                if _HAS_PYDIRECT:
                    if ev.action == "press":
                        pydirectinput.mouseDown(x=ev.x, y=ev.y, button=btn)
                    else:
                        pydirectinput.mouseUp(x=ev.x, y=ev.y, button=btn)
                    return
                if ev.action == "press":
                    mouse_down(btn)
                else:
                    mouse_up(btn)
                return
            if ev.action == "click":
                btn = _normalize_button_name(ev.button)
                self._safe_move(ev.x, ev.y, preserve_cursor)
                if _HAS_PYDIRECT:
                    pydirectinput.click(x=ev.x, y=ev.y, button=btn)
                    return
                mouse_click(btn)
                return
            if ev.action == "scroll":
                mouse_wheel(ev.dy or 0)
                return
        except Exception:
            pass
        if _HAS_PYAUTOGUI:
            try:
                if ev.action == "move":
                    if not preserve_cursor:
                        pyautogui.moveTo(ev.x, ev.y, duration=0)
                    return
                if ev.action in ("press", "release"):
                    btn = _normalize_button_name(ev.button)
                    if not preserve_cursor:
                        pyautogui.moveTo(ev.x, ev.y, duration=0)
                        time.sleep(0.02)
                    if ev.action == "press":
                        pyautogui.mouseDown(button=btn)
                    else:
                        pyautogui.mouseUp(button=btn)
                    return
                if ev.action == "click":
                    btn = _normalize_button_name(ev.button)
                    if not preserve_cursor:
                        pyautogui.moveTo(ev.x, ev.y, duration=0)
                        time.sleep(0.02)
                    pyautogui.click(x=ev.x, y=ev.y, button=btn)
                    return
                if ev.action == "scroll":
                    pyautogui.scroll(ev.dy or 0, x=ev.x, y=ev.y)
                    return
            except Exception:
                pass
        if ev.action in ("press", "release", "click") and _HAS_WINMSG:
            btn = _normalize_button_name(ev.button)
            try:
                post_click_at_screen(ev.x, ev.y, btn)
            except Exception:
                pass

    def _release_stuck_keys(self) -> None:
        for key in list(self._pressed_keys):
            try:
                keyboard.release(key)
            except Exception:
                pass
        self._pressed_keys.clear()
        for mod in ["ctrl", "alt", "shift", "left windows", "right windows", "win", "cmd"]:
            try:
                keyboard.release(mod)
            except Exception:
                pass

