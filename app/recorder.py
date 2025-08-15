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
        # Throttle migliorato per movimento mouse
        self._last_move: Optional[Tuple[int, int]] = None
        self._last_move_ts: int = 0
        self._move_threshold_pixels = 3  # Soglia minima di movimento in pixel
        self._move_throttle_ms = 10      # Throttle temporale per movimenti
        # Callback di stop esterno
        self._on_stop_requested: Optional[Callable[[], None]] = None
        # Tracciamento migliorato stati dei pulsanti per rilevamento drag e click
        self._button_states = {}
        self._last_button_pos = {}
        self._button_press_time = {}     # Timestamp della pressione
        # Prevenzione duplicazioni click
        self._last_click_time = {}
        self._click_threshold_ms = 30    # Soglia ridotta per click più responsivi
        # Soglie per determinare se è drag o click
        self._drag_threshold_pixels = 8   # Distanza minima per considerare drag
        self._drag_threshold_time_ms = 150  # Tempo minimo per considerare drag

    def set_on_stop_requested(self, cb: Optional[Callable[[], None]]) -> None:
        """Imposta il callback per la richiesta di stop"""
        self._on_stop_requested = cb

    @property
    def is_recording(self) -> bool:
        """Restituisce True se la registrazione è in corso"""
        return self._recording

    def start(self) -> None:
        """Inizia la registrazione degli eventi con configurazione migliorata"""
        if self._recording:
            return
        logger.info("Inizio registrazione con parametri ottimizzati")
        
        # Reset completo dello stato
        self._events.clear()
        self._last_time_ms = int(time.time() * 1000)
        self._recording = True
        self._last_move = None
        self._last_move_ts = 0
        self._button_states.clear()
        self._last_button_pos.clear()
        self._button_press_time.clear()
        self._last_click_time.clear()
        
        # Hook tastiera (cattura eventi)
        self._hk_press = keyboard.on_press(self._on_key_press, suppress=False)
        self._hk_release = keyboard.on_release(self._on_key_release, suppress=False)
        
        # Hook mouse (cattura eventi)
        mouse.hook(self._on_mouse_event)
        self._mouse_hooked = True
        
        logger.debug("Hook tastiera e mouse attivati con successo")

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
        logger.info("Stop registrazione, elaborazione eventi finali")
        self._recording = False
        
        # Rimuovi gli hook in modo sicuro
        try:
            if self._hk_press:
                keyboard.unhook(self._hk_press)
                self._hk_press = None
            if self._hk_release:
                keyboard.unhook(self._hk_release)
                self._hk_release = None
            if self._mouse_hooked:
                mouse.unhook(self._on_mouse_event)
                self._mouse_hooked = False
            logger.debug("Hook rimossi con successo")
        except Exception as e:
            logger.debug(f"Errore durante rimozione hook: {e}")
        
        # Gestisci eventuali operazioni di drag in sospeso
        self._finalize_pending_operations()
        
        with self._lock:
            event_count = len(self._events)
            logger.info(f"Registrazione completata: {event_count} eventi catturati")
            return list(self._events)

    def _finalize_pending_operations(self) -> None:
        """Finalizza le operazioni di drag eventualmente in sospeso"""
        current_time = int(time.time() * 1000)
        
        for btn, is_pressed in list(self._button_states.items()):
            if is_pressed and btn in self._last_button_pos:
                # C'è un pulsante ancora premuto, finalizza come drag
                try:
                    pos = mouse.get_position()
                    x, y = int(pos[0]), int(pos[1])
                    
                    press_x, press_y = self._last_button_pos[btn]
                    
                    # Registra l'evento di rilascio finale
                    release_ev = MouseEvent(
                        type="mouse", 
                        action="release", 
                        x=x, 
                        y=y, 
                        button=btn, 
                        time_delta_ms=self._time_delta()
                    )
                    with self._lock:
                        self._events.append(release_ev)
                    
                    logger.debug(f"Finalizzata operazione drag per {btn}: da ({press_x}, {press_y}) a ({x}, {y})")
                    
                except Exception as e:
                    logger.debug(f"Errore durante finalizzazione drag: {e}")

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
        """Gestisce l'evento di pressione di un tasto con normalizzazione migliorata"""
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
        """Gestisce l'evento di rilascio di un tasto con normalizzazione migliorata"""
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
        """
        Normalizza i nomi dei tasti per coerenza migliorata
        MIGLIORAMENTO: Gestione più completa delle varianti di tasti
        """
        key_lower = key_name.lower().strip()
        
        # Mappa varianti di Shift
        if key_lower in ['maiusc', 'shift', 'left shift', 'right shift', 'lshift', 'rshift']:
            if any(l in key_lower for l in ['left', 'lshift']):
                return 'left shift'
            elif any(r in key_lower for r in ['right', 'rshift']):
                return 'right shift'
            elif key_lower == 'maiusc':
                return 'shift'
            return key_lower
        
        # Mappa varianti di Ctrl
        if key_lower in ['ctrl', 'control', 'left ctrl', 'right ctrl', 'lctrl', 'rctrl']:
            if any(l in key_lower for l in ['left', 'lctrl']):
                return 'left ctrl'
            elif any(r in key_lower for r in ['right', 'rctrl']):
                return 'right ctrl'
            return 'ctrl'
        
        # Mappa varianti di Alt
        if 'alt' in key_lower:
            if 'gr' in key_lower or 'altgr' in key_lower:
                return 'alt gr'
            elif any(l in key_lower for l in ['left', 'lalt']):
                return 'left alt'
            elif any(r in key_lower for r in ['right', 'ralt']):
                return 'right alt'
            return key_lower
        
        # Mappa varianti di Windows/Cmd
        if any(w in key_lower for w in ['win', 'windows', 'cmd', 'command']):
            if any(l in key_lower for l in ['left', 'lwin']):
                return 'left windows'
            elif any(r in key_lower for r in ['right', 'rwin']):
                return 'right windows'
            return 'windows'
        
        return key_lower

    def _on_mouse_event(self, e) -> None:
        """
        Gestisce tutti gli eventi del mouse con logica migliorata per drag e click
        MIGLIORAMENTO: Distinzione più precisa tra click e drag
        """
        if not self._recording:
            return
        
        try:
            # Eventi di movimento con throttling ottimizzato
            if isinstance(e, mouse.MoveEvent):
                now_ms = int(time.time() * 1000)
                x = int(getattr(e, 'x', 0))
                y = int(getattr(e, 'y', 0))
                
                # Throttling migliorato basato su distanza e tempo
                if self._last_move:
                    distance = abs(x - self._last_move[0]) + abs(y - self._last_move[1])  # Distanza Manhattan
                    time_diff = now_ms - self._last_move_ts
                    
                    # Skip se movimento troppo piccolo o troppo frequente
                    if distance <= self._move_threshold_pixels and time_diff < self._move_throttle_ms:
                        return
                    
                    # Skip se troppo veloce indipendentemente dalla distanza
                    if time_diff < 5:  # Minimo 5ms tra movimenti
                        return
                
                self._last_move = (x, y)
                self._last_move_ts = now_ms
                
                ev = MouseEvent(type="mouse", action="move", x=x, y=y, time_delta_ms=self._time_delta())
                with self._lock:
                    self._events.append(ev)
                logger.debug(f"Registrato movimento mouse: ({x}, {y})")
            
            # Eventi dei pulsanti con logica migliorata per drag detection
            elif isinstance(e, mouse.ButtonEvent):
                btn = _normalize_button_name(getattr(e, 'button', 'left'))
                et = getattr(e, 'event_type', '')
                
                # Ottieni la posizione corrente del mouse
                try:
                    pos = mouse.get_position()
                    x, y = int(pos[0]), int(pos[1])
                except Exception:
                    x = int(getattr(e, 'x', 0))
                    y = int(getattr(e, 'y', 0))
                    if x == 0 and y == 0:
                        logger.debug("Impossibile determinare posizione mouse per evento pulsante")
                        return
                
                now_ms = int(time.time() * 1000)
                
                if et == 'down':
                    # Registra l'inizio della pressione
                    self._button_states[btn] = True
                    self._last_button_pos[btn] = (x, y)
                    self._button_press_time[btn] = now_ms
                    
                    logger.debug(f"Inizio pressione pulsante mouse: {btn} a ({x}, {y})")
                    
                elif et == 'up':
                    # Analizza se è click o drag
                    if btn in self._button_states and self._button_states.get(btn):
                        if btn in self._last_button_pos and btn in self._button_press_time:
                            press_x, press_y = self._last_button_pos[btn]
                            press_time = self._button_press_time[btn]
                            
                            # Calcola distanza e tempo di pressione
                            distance = max(abs(x - press_x), abs(y - press_y))  # Distanza massima
                            duration_ms = now_ms - press_time
                            
                            # Determina se è click o drag
                            is_drag = (distance > self._drag_threshold_pixels or 
                                      duration_ms > self._drag_threshold_time_ms)
                            
                            if not is_drag:
                                # È un click - controlla duplicazioni
                                last_click = self._last_click_time.get(btn, 0)
                                if now_ms - last_click > self._click_threshold_ms:
                                    # Registra SOLO l'evento click
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
                                    logger.debug(f"Registrato click: {btn} a ({x}, {y}) [distanza: {distance}px, durata: {duration_ms}ms]")
                            else:
                                # È un drag - registra press e release separati
                                # CORREZIONE CRITICA: Registra l'evento press con timing corretto
                                press_ev = MouseEvent(
                                    type="mouse", 
                                    action="press", 
                                    x=press_x, 
                                    y=press_y, 
                                    button=btn, 
                                    time_delta_ms=max(0, press_time - (self._last_time_ms or press_time))
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
                                
                                logger.debug(f"Registrato drag: {btn} da ({press_x}, {press_y}) a ({x}, {y}) [distanza: {distance}px, durata: {duration_ms}ms]")
                    
                    # Pulisci lo stato del pulsante
                    self._button_states[btn] = False
                    self._last_button_pos.pop(btn, None)
                    self._button_press_time.pop(btn, None)
                
                elif et == 'double':
                    # Gestisce doppi click con timing migliorato
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
                        time_delta_ms=100  # Ritardo standard per doppio click
                    )
                    with self._lock:
                        self._events.append(ev1)
                        self._events.append(ev2)
                    self._last_click_time[btn] = now_ms
                    logger.debug(f"Registrato doppio click: {btn} a ({x}, {y})")
            
            # Eventi di scroll con registrazione migliorata
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
                logger.debug(f"Registrato scroll: delta={delta} a ({x}, {y})")
                
        except Exception as exc:
            logger.debug(f"Errore durante elaborazione evento mouse: {exc}")