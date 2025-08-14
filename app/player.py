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
    pydirectinput.PAUSE = 0  # Remove default pause between actions
    _HAS_PYDIRECT = True
except Exception:
    _HAS_PYDIRECT = False

try:
    import pyautogui  # type: ignore
    pyautogui.PAUSE = 0  # Remove default pause between actions
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
                        
                    # Apply timing delays if with_pauses is enabled
                    if with_pauses and getattr(ev, "time_delta_ms", 0) > 0:
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
                logger.debug(f"Key pressed: {key}")
            elif ev.action == "release":
                keyboard.release(key)
                self._pressed_keys.discard(key)
                logger.debug(f"Key released: {key}")
        except Exception as exc:
            logger.debug(f"Error playing key event: {exc}")

    def _safe_move(self, x: int, y: int, preserve_cursor: bool) -> None:
        if not preserve_cursor:
            move_cursor_abs(x, y)
            time.sleep(0.005)  # Very short delay for smoother movement

    def _play_mouse(self, ev: MouseEvent, preserve_cursor: bool) -> None:
        # Handle click events with priority
        if ev.action == "click":
            btn = _normalize_button_name(ev.button)
            logger.debug(f"Playing mouse click: {btn} at ({ev.x}, {ev.y})")
            
            # If preserve cursor is enabled and we have PostMessage support
            if preserve_cursor and _HAS_WINMSG:
                try:
                    if post_click_at_screen(ev.x, ev.y, btn):
                        logger.debug("Click sent via PostMessage")
                        return
                except Exception as exc:
                    logger.debug(f"PostMessage failed: {exc}")
            
            # Move to position if not preserving cursor
            if not preserve_cursor:
                move_cursor_abs(ev.x, ev.y)
                time.sleep(0.01)  # Small delay to ensure position is set
            
            # Try different methods to perform click
            success = False
            
            # Method 1: Native Windows API (most reliable)
            try:
                mouse_click(btn)
                success = True
                logger.debug("Click executed via native Windows API")
            except Exception as exc:
                logger.debug(f"Native Windows API failed: {exc}")
            
            # Method 2: pydirectinput (good for games)
            if _HAS_PYDIRECT and not success:
                try:
                    # Ensure we're at the right position
                    if not preserve_cursor:
                        pydirectinput.moveTo(ev.x, ev.y)
                    pydirectinput.click(button=btn)
                    success = True
                    logger.debug("Click executed via pydirectinput")
                except Exception as exc:
                    logger.debug(f"pydirectinput failed: {exc}")
            
            # Method 3: pyautogui as fallback
            if _HAS_PYAUTOGUI and not success:
                try:
                    pyautogui.click(x=ev.x, y=ev.y, button=btn)
                    success = True
                    logger.debug("Click executed via pyautogui")
                except Exception as exc:
                    logger.debug(f"pyautogui failed: {exc}")
            
            # Method 4: PostMessage as last resort (even when not preserving cursor)
            if _HAS_WINMSG and not success:
                try:
                    post_click_at_screen(ev.x, ev.y, btn)
                    logger.debug("Click executed via PostMessage (fallback)")
                except Exception as exc:
                    logger.debug(f"PostMessage fallback failed: {exc}")
            
            return
        
        # Handle move events
        if ev.action == "move":
            self._safe_move(ev.x, ev.y, preserve_cursor)
            return
        
        # Handle press/release events (for drag operations)
        if ev.action in ("press", "release"):
            btn = _normalize_button_name(ev.button)
            logger.debug(f"Playing mouse {ev.action}: {btn} at ({ev.x}, {ev.y})")
            
            # Move to position first
            self._safe_move(ev.x, ev.y, preserve_cursor)
            
            # Try different methods
            success = False
            
            # Method 1: Native Windows API
            try:
                if ev.action == "press":
                    mouse_down(btn)
                else:
                    mouse_up(btn)
                success = True
                logger.debug(f"Mouse {ev.action} executed via native Windows API")
            except Exception as exc:
                logger.debug(f"Native Windows API failed: {exc}")
            
            # Method 2: pydirectinput
            if _HAS_PYDIRECT and not success:
                try:
                    if ev.action == "press":
                        pydirectinput.mouseDown(x=ev.x, y=ev.y, button=btn)
                    else:
                        pydirectinput.mouseUp(x=ev.x, y=ev.y, button=btn)
                    success = True
                    logger.debug(f"Mouse {ev.action} executed via pydirectinput")
                except Exception as exc:
                    logger.debug(f"pydirectinput failed: {exc}")
            
            # Method 3: pyautogui
            if _HAS_PYAUTOGUI and not success:
                try:
                    if ev.action == "press":
                        pyautogui.mouseDown(button=btn)
                    else:
                        pyautogui.mouseUp(button=btn)
                    success = True
                    logger.debug(f"Mouse {ev.action} executed via pyautogui")
                except Exception as exc:
                    logger.debug(f"pyautogui failed: {exc}")
            
            return
        
        # Handle scroll events
        if ev.action == "scroll":
            logger.debug(f"Playing mouse scroll: {ev.dy} at ({ev.x}, {ev.y})")
            try:
                mouse_wheel(ev.dy or 0)
                logger.debug("Scroll executed via native Windows API")
            except Exception as exc:
                logger.debug(f"Native scroll failed: {exc}")
                if _HAS_PYAUTOGUI:
                    try:
                        pyautogui.scroll(ev.dy or 0, x=ev.x, y=ev.y)
                        logger.debug("Scroll executed via pyautogui")
                    except Exception as exc2:
                        logger.debug(f"pyautogui scroll failed: {exc2}")
            return

    def _release_stuck_keys(self) -> None:
        for key in list(self._pressed_keys):
            try:
                keyboard.release(key)
            except Exception:
                pass
        self._pressed_keys.clear()
        # Also release common modifier keys
        for mod in ["ctrl", "alt", "shift", "left windows", "right windows", "win", "cmd"]:
            try:
                keyboard.release(mod)
            except Exception:
                pass