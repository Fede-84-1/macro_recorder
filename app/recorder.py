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
        # Track button states for proper click detection
        self._button_states = {}
        self._last_button_pos = {}

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
        self._button_states.clear()
        self._last_button_pos.clear()
        # keyboard hooks (capture events)
        self._hk_press = keyboard.on_press(self._on_key_press, suppress=False)
        self._hk_release = keyboard.on_release(self._on_key_release, suppress=False)
        # mouse hooks (capture events)
        mouse.hook(self._on_mouse_event)
        self._mouse_hooked = True

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
        # unhook
        try:
            if self._hk_press:
                keyboard.unhook(self._hk_press)
            if self._hk_release:
                keyboard.unhook(self._hk_release)
            if self._mouse_hooked:
                mouse.unhook(self._on_mouse_event)
                self._mouse_hooked = False
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
                # Get position from the event
                x = int(getattr(e, 'x', 0))
                y = int(getattr(e, 'y', 0))
                
                # Throttle mouse move events
                if self._last_move and (abs(x - self._last_move[0]) <= 2 and abs(y - self._last_move[1]) <= 2):
                    return
                if now_ms - self._last_move_ts < 15:
                    return
                    
                self._last_move = (x, y)
                self._last_move_ts = now_ms
                ev = MouseEvent(type="mouse", action="move", x=x, y=y, time_delta_ms=self._time_delta())
                with self._lock:
                    self._events.append(ev)
                    
            elif isinstance(e, mouse.ButtonEvent):
                btn = _normalize_button_name(getattr(e, 'button', 'left'))
                et = getattr(e, 'event_type', '')
                
                # Get current mouse position
                # ButtonEvent doesn't always have x,y attributes, so we use mouse.get_position()
                try:
                    pos = mouse.get_position()
                    x, y = int(pos[0]), int(pos[1])
                except Exception:
                    # Fallback: try to get from event attributes if available
                    x = int(getattr(e, 'x', 0))
                    y = int(getattr(e, 'y', 0))
                    if x == 0 and y == 0:
                        # If still no position, skip this event
                        logger.debug("Could not determine mouse position for button event")
                        return
                
                if et == 'down':
                    # Record button press
                    self._button_states[btn] = True
                    self._last_button_pos[btn] = (x, y)
                    ev = MouseEvent(type="mouse", action="press", x=x, y=y, button=btn, time_delta_ms=self._time_delta())
                    with self._lock:
                        self._events.append(ev)
                    logger.debug(f"Recorded mouse press: {btn} at ({x}, {y})")
                        
                elif et == 'up':
                    # Record button release
                    ev = MouseEvent(type="mouse", action="release", x=x, y=y, button=btn, time_delta_ms=self._time_delta())
                    with self._lock:
                        self._events.append(ev)
                    logger.debug(f"Recorded mouse release: {btn} at ({x}, {y})")
                    
                    # Check if this completes a click (press and release at same position)
                    if btn in self._button_states and self._button_states.get(btn):
                        if btn in self._last_button_pos:
                            press_x, press_y = self._last_button_pos[btn]
                            # If press and release are at approximately same position, also record as click
                            if abs(x - press_x) <= 5 and abs(y - press_y) <= 5:
                                click_ev = MouseEvent(type="mouse", action="click", x=x, y=y, button=btn, time_delta_ms=0)
                                with self._lock:
                                    self._events.append(click_ev)
                                logger.debug(f"Recorded mouse click: {btn} at ({x}, {y})")
                    
                    self._button_states[btn] = False
                    
                elif et == 'double':
                    # Handle double clicks explicitly
                    # First click
                    ev1 = MouseEvent(type="mouse", action="click", x=x, y=y, button=btn, time_delta_ms=self._time_delta())
                    # Second click with small delay
                    ev2 = MouseEvent(type="mouse", action="click", x=x, y=y, button=btn, time_delta_ms=50)
                    with self._lock:
                        self._events.append(ev1)
                        self._events.append(ev2)
                    logger.debug(f"Recorded double click: {btn} at ({x}, {y})")
                        
            elif isinstance(e, mouse.WheelEvent):
                # Get position
                x = int(getattr(e, 'x', 0))
                y = int(getattr(e, 'y', 0))
                delta = int(getattr(e, 'delta', 0))
                
                ev = MouseEvent(type="mouse", action="scroll", x=x, y=y, dx=0, dy=delta, time_delta_ms=self._time_delta())
                with self._lock:
                    self._events.append(ev)
                    
        except Exception as exc:
            logger.debug(f"Error processing mouse event: {exc}")
            return