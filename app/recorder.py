from __future__ import annotations

import threading
import time
from typing import List, Optional, Tuple, Callable

from loguru import logger
import keyboard  # type: ignore
import mouse  # type: ignore

from .models import KeyEvent, MouseEvent, Event


def _normalize_button_name(btn) -> str:
    """Normalizza il nome del pulsante del mouse"""
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
        # Riferimenti agli hook per unhook
        self._hk_press = None
        self._hk_release = None
        self._mouse_hooked: bool = False
        # Throttle per movimento mouse
        self._last_move: Optional[Tuple[int, int]] = None
        self._last_move_ts: int = 0
        # Callback di stop esterno
        self._on_stop_requested: Optional[Callable[[], None]] = None
        # Tracciamento stati dei pulsanti per rilevamento click corretto
        self._button_states = {}
        self._last_button_pos = {}
        # Tracciamento per evitare duplicazioni di click
        self._last_click_time = {}
        self._click_threshold_ms = 50  # Soglia per ignorare click duplicati

    def set_on_stop_requested(self, cb: Optional[Callable[[], None]]) -> None:
        """Imposta il callback per la richiesta di stop"""
        self._on_stop_requested = cb

    @property
    def is_recording(self) -> bool:
        """Restituisce True se la registrazione è in corso"""
        return self._recording

    def start(self) -> None:
        """Inizia la registrazione degli eventi"""
        if self._recording:
            return
        logger.info("Inizio registrazione")
        self._events.clear()
        self._last_time_ms = int(time.time() * 1000)
        self._recording = True
        self._last_move = None
        self._last_move_ts = 0
        self._button_states.clear()
        self._last_button_pos.clear()
        self._last_click_time.clear()
        
        # Hook tastiera (cattura eventi)
        self._hk_press = keyboard.on_press(self._on_key_press, suppress=False)
        self._hk_release = keyboard.on_release(self._on_key_release, suppress=False)
        
        # Hook mouse (cattura eventi)
        mouse.hook(self._on_mouse_event)
        self._mouse_hooked = True

    def _request_stop(self) -> None:
        """Richiede lo stop della registrazione"""
        if self._on_stop_requested:
            try:
                self._on_stop_requested()
            except Exception:
                pass

    def stop(self) -> List[Event]:
        """Ferma la registrazione e restituisce gli eventi registrati"""
        if not self._recording:
            return []
        logger.info("Stop registrazione")
        self._recording = False
        
        # Rimuovi gli hook
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

    def _time_delta(self) -> int:
        """Calcola il delta temporale dall'ultimo evento in millisecondi"""
        now = int(time.time() * 1000)
        if self._last_time_ms is None:
            self._last_time_ms = now
            return 0
        delta = now - self._last_time_ms
        self._last_time_ms = now
        return max(0, int(delta))

    def _on_key_press(self, e) -> None:
        """Gestisce l'evento di pressione di un tasto"""
        if not self._recording:
            return
        
        key_name = (e.name or "").lower()
        
        # Normalizza i nomi dei tasti modificatori per coerenza
        key_name = self._normalize_key_name(key_name)
        
        ev = KeyEvent(type="key", action="press", key=str(key_name), time_delta_ms=self._time_delta())
        with self._lock:
            self._events.append(ev)
        logger.debug(f"Registrato tasto premuto: {key_name}")

    def _on_key_release(self, e) -> None:
        """Gestisce l'evento di rilascio di un tasto"""
        if not self._recording:
            return
        
        key_name = (e.name or "").lower()
        
        # Normalizza i nomi dei tasti modificatori per coerenza
        key_name = self._normalize_key_name(key_name)
        
        ev = KeyEvent(type="key", action="release", key=str(key_name), time_delta_ms=self._time_delta())
        with self._lock:
            self._events.append(ev)
        logger.debug(f"Registrato tasto rilasciato: {key_name}")

    def _normalize_key_name(self, key_name: str) -> str:
        """Normalizza i nomi dei tasti per coerenza, specialmente per i modificatori"""
        key_lower = key_name.lower()
        
        # Mappa varianti di Shift a un nome coerente
        if key_lower in ['maiusc', 'shift', 'left shift', 'right shift']:
            if 'left' in key_lower:
                return 'left shift'
            elif 'right' in key_lower:
                return 'right shift'
            elif key_lower == 'maiusc':
                return 'shift'
            return key_lower
        
        # Mappa varianti di Ctrl
        if key_lower in ['ctrl', 'control', 'left ctrl', 'right ctrl']:
            if 'left' in key_lower:
                return 'left ctrl'
            elif 'right' in key_lower:
                return 'right ctrl'
            return 'ctrl'
        
        # Mappa varianti di Alt
        if 'alt' in key_lower:
            if 'gr' in key_lower:
                return 'alt gr'
            elif 'left' in key_lower:
                return 'left alt'
            elif 'right' in key_lower:
                return 'right alt'
            return key_lower
        
        return key_lower

    def _on_mouse_event(self, e) -> None:
        """Gestisce tutti gli eventi del mouse"""
        if not self._recording:
            return
        
        try:
            # Eventi di movimento
            if isinstance(e, mouse.MoveEvent):
                now_ms = int(time.time() * 1000)
                # Ottieni la posizione dall'evento
                x = int(getattr(e, 'x', 0))
                y = int(getattr(e, 'y', 0))
                
                # Throttle eventi di movimento del mouse
                if self._last_move and (abs(x - self._last_move[0]) <= 2 and abs(y - self._last_move[1]) <= 2):
                    return
                if now_ms - self._last_move_ts < 15:
                    return
                
                self._last_move = (x, y)
                self._last_move_ts = now_ms
                ev = MouseEvent(type="mouse", action="move", x=x, y=y, time_delta_ms=self._time_delta())
                with self._lock:
                    self._events.append(ev)
            
            # Eventi dei pulsanti
            elif isinstance(e, mouse.ButtonEvent):
                btn = _normalize_button_name(getattr(e, 'button', 'left'))
                et = getattr(e, 'event_type', '')
                
                # Ottieni la posizione corrente del mouse
                try:
                    pos = mouse.get_position()
                    x, y = int(pos[0]), int(pos[1])
                except Exception:
                    # Fallback: prova a ottenere dagli attributi dell'evento
                    x = int(getattr(e, 'x', 0))
                    y = int(getattr(e, 'y', 0))
                    if x == 0 and y == 0:
                        logger.debug("Impossibile determinare la posizione del mouse per l'evento pulsante")
                        return
                
                now_ms = int(time.time() * 1000)
                
                if et == 'down':
                    # Registra la pressione del pulsante
                    self._button_states[btn] = True
                    self._last_button_pos[btn] = (x, y)
                    
                    # NON registrare l'evento press separatamente per click normali
                    # Lo registriamo solo se è parte di un'operazione di trascinamento
                    logger.debug(f"Pulsante mouse premuto: {btn} a ({x}, {y})")
                    
                elif et == 'up':
                    # Controlla se questo completa un click
                    if btn in self._button_states and self._button_states.get(btn):
                        if btn in self._last_button_pos:
                            press_x, press_y = self._last_button_pos[btn]
                            
                            # Se press e release sono nella stessa posizione (approssimativamente), è un click
                            if abs(x - press_x) <= 5 and abs(y - press_y) <= 5:
                                # Controlla se non è un click duplicato
                                last_click = self._last_click_time.get(btn, 0)
                                if now_ms - last_click > self._click_threshold_ms:
                                    # Registra SOLO l'evento click, non press/release separati
                                    click_ev = MouseEvent(
                                        type="mouse", 
                                        action="click", 
                                        x=x, 
                                        y=y, 
                                        button=btn, 
                                        time_delta_ms=self._time_delta()
                                    )
                                    with self._lock:
                                        self._events.append(click_ev)
                                    self._last_click_time[btn] = now_ms
                                    logger.debug(f"Registrato click mouse: {btn} a ({x}, {y})")
                            else:
                                # È un'operazione di trascinamento, registra press e release
                                # Registra l'evento press originale
                                press_ev = MouseEvent(
                                    type="mouse", 
                                    action="press", 
                                    x=press_x, 
                                    y=press_y, 
                                    button=btn, 
                                    time_delta_ms=0
                                )
                                # Registra l'evento release
                                release_ev = MouseEvent(
                                    type="mouse", 
                                    action="release", 
                                    x=x, 
                                    y=y, 
                                    button=btn, 
                                    time_delta_ms=self._time_delta()
                                )
                                with self._lock:
                                    self._events.append(press_ev)
                                    self._events.append(release_ev)
                                logger.debug(f"Registrato trascinamento: {btn} da ({press_x}, {press_y}) a ({x}, {y})")
                    
                    self._button_states[btn] = False
                
                elif et == 'double':
                    # Gestisce i doppi click esplicitamente
                    # Registra due click con un piccolo ritardo
                    ev1 = MouseEvent(
                        type="mouse", 
                        action="click", 
                        x=x, 
                        y=y, 
                        button=btn, 
                        time_delta_ms=self._time_delta()
                    )
                    ev2 = MouseEvent(
                        type="mouse", 
                        action="click", 
                        x=x, 
                        y=y, 
                        button=btn, 
                        time_delta_ms=50
                    )
                    with self._lock:
                        self._events.append(ev1)
                        self._events.append(ev2)
                    self._last_click_time[btn] = now_ms
                    logger.debug(f"Registrato doppio click: {btn} a ({x}, {y})")
            
            # Eventi di scroll
            elif isinstance(e, mouse.WheelEvent):
                x = int(getattr(e, 'x', 0))
                y = int(getattr(e, 'y', 0))
                delta = int(getattr(e, 'delta', 0))
                
                ev = MouseEvent(
                    type="mouse", 
                    action="scroll", 
                    x=x, 
                    y=y, 
                    dx=0, 
                    dy=delta, 
                    time_delta_ms=self._time_delta()
                )
                with self._lock:
                    self._events.append(ev)
                logger.debug(f"Registrato scroll: {delta} a ({x}, {y})")
                
        except Exception as exc:
            logger.debug(f"Errore durante l'elaborazione dell'evento mouse: {exc}")
            return