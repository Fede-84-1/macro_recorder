from __future__ import annotations

import threading
import time
from typing import List, Optional, Tuple, Callable

from loguru import logger
import keyboard  # type: ignore
import mouse  # type: ignore

from .models import KeyEvent, MouseEvent, Event


def _normalize_button_name(btn) -> str:
    s = str(btn).lower()
    if "left" in s:
        return "left"
    if "right" in s:
        return "right"
    if "middle" in s or "wheel" in s:
        return "middle"
    return "left"


class Recorder:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: List[Event] = []
        self._last_time_ms: Optional[int] = None
        self._recording: bool = False
        # hook references for unhook
        self._hk_press = None
        self._hk_release = None
        self._mouse_hooked: bool = False
        # throttle mouse move
        self._last_move: Optional[Tuple[int, int]] = None
        self._last_move_ts: int = 0
        # external stop callback
        self._on_stop_requested: Optional[Callable[[], None]] = None
        # temp stop hotkeys
        self._temp_stop_handles: List[str] = []
        # polling thread for stop
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_stop = threading.Event()

    def set_on_stop_requested(self, cb: Optional[Callable[[], None]]) -> None:
        self._on_stop_requested = cb

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        if self._recording:
            return
        logger.info("Start recording")
        self._events.clear()
        self._last_time_ms = int(time.time() * 1000)
        self._recording = True
        self._last_move = None
        self._last_move_ts = 0
        # keyboard hooks (capture events)
        self._hk_press = keyboard.on_press(self._on_key_press, suppress=False)
        self._hk_release = keyboard.on_release(self._on_key_release, suppress=False)
        # mouse hooks (capture events)
        mouse.hook(self._on_mouse_event)
        self._mouse_hooked = True
        # temporary hotkeys to force stop (ESC/escape + ctrl+alt+r)
        try:
            self._temp_stop_handles.append(keyboard.add_hotkey('esc', self._request_stop))
        except Exception:
            pass
        try:
            self._temp_stop_handles.append(keyboard.add_hotkey('escape', self._request_stop))
        except Exception:
            pass
        try:
            self._temp_stop_handles.append(keyboard.add_hotkey('ctrl+alt+r', self._request_stop))
        except Exception:
            pass
        # start polling monitor as additional safety
        self._monitor_stop.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self) -> None:
        while not self._monitor_stop.is_set():
            try:
                if keyboard.is_pressed('esc') or keyboard.is_pressed('escape') or (keyboard.is_pressed('ctrl') and keyboard.is_pressed('alt') and keyboard.is_pressed('r')):
                    self._request_stop()
                    return
            except Exception:
                pass
            time.sleep(0.05)

    def _request_stop(self) -> None:
        if self._on_stop_requested:
            try:
                self._on_stop_requested()
            except Exception:
                pass

    def stop(self) -> List[Event]:
        if not self._recording:
            return []
        logger.info("Stop recording")
        self._recording = False
        # stop monitor thread
        try:
            self._monitor_stop.set()
        except Exception:
            pass
        # unhook
        try:
            if self._hk_press:
                keyboard.unhook(self._hk_press)
            if self._hk_release:
                keyboard.unhook(self._hk_release)
            if self._mouse_hooked:
                mouse.unhook(self._on_mouse_event)
                self._mouse_hooked = False
            for handle in self._temp_stop_handles:
                try:
                    keyboard.remove_hotkey(handle)
                except Exception:
                    pass
            self._temp_stop_handles.clear()
        except Exception:
            pass
        with self._lock:
            return list(self._events)

    # Timing helper
    def _time_delta(self) -> int:
        now = int(time.time() * 1000)
        if self._last_time_ms is None:
            self._last_time_ms = now
            return 0
        delta = now - self._last_time_ms
        self._last_time_ms = now
        return max(0, int(delta))

    # Keyboard handlers
    def _on_key_press(self, e) -> None:
        if not self._recording:
            return
        key_name = (e.name or "").lower()
        if key_name in ("esc", "escape"):
            self._request_stop()
            return
        ev = KeyEvent(type="key", action="press", key=str(key_name), time_delta_ms=self._time_delta())
        with self._lock:
            self._events.append(ev)

    def _on_key_release(self, e) -> None:
        if not self._recording:
            return
        key_name = (e.name or "").lower()
        ev = KeyEvent(type="key", action="release", key=str(key_name), time_delta_ms=self._time_delta())
        with self._lock:
            self._events.append(ev)

    # Mouse handler (receives any event)
    def _on_mouse_event(self, e) -> None:
        if not self._recording:
            return
        try:
            if isinstance(e, mouse.MoveEvent):
                now_ms = int(time.time() * 1000)
                if self._last_move and (abs(e.x - self._last_move[0]) <= 2 and abs(e.y - self._last_move[1]) <= 2):
                    return
                if now_ms - self._last_move_ts < 15:
                    return
                self._last_move = (int(e.x), int(e.y))
                self._last_move_ts = now_ms
                ev = MouseEvent(type="mouse", action="move", x=int(e.x), y=int(e.y), time_delta_ms=self._time_delta())
            elif isinstance(e, mouse.ButtonEvent):
                btn = _normalize_button_name(getattr(e, 'button', 'left'))
                et = getattr(e, 'event_type', '')
                if et == 'down':
                    ev = MouseEvent(type="mouse", action="press", x=int(e.x), y=int(e.y), button=btn, time_delta_ms=self._time_delta())
                elif et == 'up':
                    ev = MouseEvent(type="mouse", action="release", x=int(e.x), y=int(e.y), button=btn, time_delta_ms=self._time_delta())
                else:
                    return
            elif isinstance(e, mouse.WheelEvent):
                ev = MouseEvent(type="mouse", action="scroll", x=int(e.x), y=int(e.y), dx=0, dy=int(e.delta), time_delta_ms=self._time_delta())
            else:
                return
            with self._lock:
                self._events.append(ev)
        except Exception:
            return

