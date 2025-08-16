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
        # CORREZIONE PROBLEMA 2: Gestione ottimizzata movimento mouse
        self._last_move: Optional[Tuple[int, int]] = None
        self._last_move_ts: int = 0
        self._move_threshold_pixels = 2  # Soglia ridotta per catturare più movimenti
        self._move_throttle_ms = 8       # Throttle ridotto per maggiore precisione
        # Callback di stop esterno
        self._on_stop_requested: Optional[Callable[[], None]] = None
        # CORREZIONE PROBLEMA 2: Tracciamento avanzato per sequenze di tasti ripetuti
        self._key_press_history: List[Tuple[str, str, float]] = []  # (key, action, timestamp)
        self._key_timing_optimization = True
        # Tracciamento stati pulsanti per drag detection migliorata
        self._button_states = {}
        self._last_button_pos = {}
        self._button_press_time = {}
        self._last_click_time = {}
        self._click_threshold_ms = 25    # Soglia ridotta per click più responsivi
        self._drag_threshold_pixels = 6   # Soglia ottimizzata per drag detection
        self._drag_threshold_time_ms = 120  # Tempo ottimizzato per drag

    def set_on_stop_requested(self, cb: Optional[Callable[[], None]]) -> None:
        """Imposta il callback per la richiesta di stop"""
        self._on_stop_requested = cb

    @property
    def is_recording(self) -> bool:
        """Restituisce True se la registrazione è in corso"""
        return self._recording

    def start(self) -> None:
        """
        Inizia la registrazione con ottimizzazioni per il PROBLEMA 2
        CORREZIONE: Configurazione ottimizzata per cattura tasti ripetuti
        """
        if self._recording:
            return
        logger.info("Inizio registrazione con ottimizzazioni per tasti ripetuti")
        
        # Reset completo dello stato con ottimizzazioni
        self._events.clear()
        self._last_time_ms = int(time.time() * 1000)
        self._recording = True
        self._last_move = None
        self._last_move_ts = 0
        self._button_states.clear()
        self._last_button_pos.clear()
        self._button_press_time.clear()
        self._last_click_time.clear()
        # CORREZIONE PROBLEMA 2: Reset storia tasti
        self._key_press_history.clear()
        
        # Hook tastiera con configurazioni ottimizzate
        self._hk_press = keyboard.on_press(self._on_key_press, suppress=False)
        self._hk_release = keyboard.on_release(self._on_key_release, suppress=False)
        
        # Hook mouse con configurazioni ottimizzate
        mouse.hook(self._on_mouse_event)
        self._mouse_hooked = True
        
        logger.debug("Hook tastiera e mouse attivati con ottimizzazioni")

    def _request_stop(self) -> None:
        """Richiede lo stop della registrazione"""
        if self._on_stop_requested:
            try:
                self._on_stop_requested()
            except Exception:
                pass

    def stop(self) -> List[Event]:
        """
        Ferma la registrazione con post-processing per ottimizzare sequenze ripetute
        CORREZIONE PROBLEMA 2: Analisi e ottimizzazione eventi catturati
        """
        if not self._recording:
            return []
        logger.info("Stop registrazione con post-processing eventi")
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
        
        # Finalizza operazioni in sospeso
        self._finalize_pending_operations()
        
        # CORREZIONE PROBLEMA 2: Post-processing per ottimizzare sequenze
        with self._lock:
            optimized_events = self._optimize_key_sequences(list(self._events))
            event_count = len(optimized_events)
            logger.info(f"Registrazione completata: {event_count} eventi ottimizzati")
            return optimized_events

    def _optimize_key_sequences(self, events: List[Event]) -> List[Event]:
        """
        CORREZIONE PROBLEMA 2: Ottimizza le sequenze di tasti per prevenire perdite
        """
        if not self._key_timing_optimization:
            return events
        
        optimized = []
        i = 0
        
        while i < len(events):
            current_event = events[i]
            
            # Per eventi tastiera, analizza sequenze ripetute
            if isinstance(current_event, KeyEvent):
                # Cerca sequenze di press/release dello stesso tasto
                sequence = [current_event]
                j = i + 1
                
                # Raccogli eventi consecutivi dello stesso tasto
                while (j < len(events) and 
                       isinstance(events[j], KeyEvent) and 
                       events[j].key == current_event.key):
                    sequence.append(events[j])
                    j += 1
                
                # Se abbiamo una sequenza di tasti ripetuti, ottimizzala
                if len(sequence) > 2:
                    optimized_sequence = self._optimize_repeated_key_sequence(sequence)
                    optimized.extend(optimized_sequence)
                    i = j
                else:
                    optimized.append(current_event)
                    i += 1
            else:
                # Per eventi non-tastiera, mantieni originali
                optimized.append(current_event)
                i += 1
        
        logger.debug(f"Ottimizzazione sequenze: {len(events)} -> {len(optimized)} eventi")
        return optimized

    def _optimize_repeated_key_sequence(self, sequence: List[KeyEvent]) -> List[KeyEvent]:
        """
        CORREZIONE PROBLEMA 2: Ottimizza una sequenza di tasti ripetuti
        """
        if len(sequence) <= 2:
            return sequence
        
        optimized = []
        key_name = sequence[0].key
        min_interval = 15  # Intervallo minimo in ms per tasti ripetuti
        
        for i, event in enumerate(sequence):
            if i == 0:
                # Primo evento sempre incluso
                optimized.append(event)
            else:
                # Per eventi successivi, assicura intervallo minimo
                prev_event = optimized[-1]
                
                # Se l'intervallo è troppo piccolo e sono eventi alternati press/release
                if (event.time_delta_ms < min_interval and 
                    prev_event.action != event.action):
                    
                    # Regola il timing per evitare perdite
                    adjusted_event = KeyEvent(
                        type=event.type,
                        action=event.action,
                        key=event.key,
                        time_delta_ms=max(min_interval, event.time_delta_ms)
                    )
                    optimized.append(adjusted_event)
                    logger.debug(f"Regolato timing per {key_name}: {event.time_delta_ms} -> {adjusted_event.time_delta_ms}ms")
                else:
                    optimized.append(event)
        
        return optimized

    def _finalize_pending_operations(self) -> None:
        """Finalizza le operazioni di drag eventualmente in sospeso"""
        current_time = int(time.time() * 1000)
        
        for btn, is_pressed in list(self._button_states.items()):
            if is_pressed and btn in self._last_button_pos:
                try:
                    pos = mouse.get_position()
                    x, y = int(pos[0]), int(pos[1])
                    press_x, press_y = self._last_button_pos[btn]
                    
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
        """
        CORREZIONE PROBLEMA 2: Gestione press con tracking avanzato per tasti ripetuti
        """
        if not self._recording:
            return
        
        key_name = (e.name or "").lower()
        key_name = self._normalize_key_name(key_name)
        current_time = time.time()
        
        # CORREZIONE PROBLEMA 2: Registra nella storia per analisi sequenze
        self._key_press_history.append((key_name, "press", current_time))
        
        # Mantieni solo gli ultimi 20 eventi per performance
        if len(self._key_press_history) > 20:
            self._key_press_history = self._key_press_history[-20:]
        
        ev = KeyEvent(type="key", action="press", key=str(key_name), time_delta_ms=self._time_delta())
        with self._lock:
            self._events.append(ev)
        logger.debug(f"Registrato tasto premuto: {key_name}")

    def _on_key_release(self, e) -> None:
        """
        CORREZIONE PROBLEMA 2: Gestione release con tracking avanzato per tasti ripetuti
        """
        if not self._recording:
            return
        
        key_name = (e.name or "").lower()
        key_name = self._normalize_key_name(key_name)
        current_time = time.time()
        
        # CORREZIONE PROBLEMA 2: Registra nella storia per analisi sequenze
        self._key_press_history.append((key_name, "release", current_time))
        
        # Mantieni solo gli ultimi 20 eventi per performance
        if len(self._key_press_history) > 20:
            self._key_press_history = self._key_press_history[-20:]
        
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
        Gestisce tutti gli eventi del mouse con logica ottimizzata per precision
        MIGLIORAMENTO: Cattura più precisa eventi mouse per riproduzione accurata
        """
        if not self._recording:
            return
        
        try:
            # Eventi di movimento con throttling ottimizzato
            if isinstance(e, mouse.MoveEvent):
                now_ms = int(time.time() * 1000)
                x = int(getattr(e, 'x', 0))
                y = int(getattr(e, 'y', 0))
                
                # CORREZIONE: Throttling ottimizzato per maggiore precisione
                if self._last_move:
                    distance = abs(x - self._last_move[0]) + abs(y - self._last_move[1])
                    time_diff = now_ms - self._last_move_ts
                    
                    # Logica ottimizzata: cattura più movimenti per precision
                    if distance <= self._move_threshold_pixels and time_diff < self._move_throttle_ms:
                        return
                    
                    # Filtro per movimenti troppo rapidi (probabile rumore)
                    if time_diff < 3:
                        return
                
                self._last_move = (x, y)
                self._last_move_ts = now_ms
                
                ev = MouseEvent(type="mouse", action="move", x=x, y=y, time_delta_ms=self._time_delta())
                with self._lock:
                    self._events.append(ev)
                logger.debug(f"Registrato movimento mouse: ({x}, {y})")
            
            # Eventi dei pulsanti con logica ottimizzata per drag detection
            elif isinstance(e, mouse.ButtonEvent):
                btn = _normalize_button_name(getattr(e, 'button', 'left'))
                et = getattr(e, 'event_type', '')
                
                # Ottieni posizione corrente con fallback robusto
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
                    # Registra inizio pressione con timing preciso
                    self._button_states[btn] = True
                    self._last_button_pos[btn] = (x, y)
                    self._button_press_time[btn] = now_ms
                    logger.debug(f"Inizio pressione pulsante: {btn} a ({x}, {y})")
                    
                elif et == 'up':
                    # Analisi intelligente click vs drag
                    if btn in self._button_states and self._button_states.get(btn):
                        if btn in self._last_button_pos and btn in self._button_press_time:
                            press_x, press_y = self._last_button_pos[btn]
                            press_time = self._button_press_time[btn]
                            
                            # Calcola metriche per classificazione
                            distance = max(abs(x - press_x), abs(y - press_y))
                            duration_ms = now_ms - press_time
                            
                            # CORREZIONE: Logica ottimizzata per drag detection
                            is_drag = (distance > self._drag_threshold_pixels or 
                                      duration_ms > self._drag_threshold_time_ms)
                            
                            if not is_drag:
                                # È un click - verifica duplicazioni
                                last_click = self._last_click_time.get(btn, 0)
                                if now_ms - last_click > self._click_threshold_ms:
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
                                    logger.debug(f"Registrato click: {btn} a ({x}, {y})")
                            else:
                                # È un drag - registra press e release separati
                                press_delta = max(0, press_time - (self._last_time_ms or press_time))
                                
                                press_ev = MouseEvent(
                                    type="mouse", 
                                    action="press", 
                                    x=press_x, 
                                    y=press_y, 
                                    button=btn, 
                                    time_delta_ms=press_delta
                                )
                                
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
                                
                                logger.debug(f"Registrato drag: {btn} da ({press_x}, {press_y}) a ({x}, {y})")
                    
                    # Pulizia stato pulsante
                    self._button_states[btn] = False
                    self._last_button_pos.pop(btn, None)
                    self._button_press_time.pop(btn, None)
                
                elif et == 'double':
                    # Gestione doppi click ottimizzata
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
                        time_delta_ms=80  # Timing ottimizzato per doppio click
                    )
                    with self._lock:
                        self._events.append(ev1)
                        self._events.append(ev2)
                    self._last_click_time[btn] = now_ms
                    logger.debug(f"Registrato doppio click: {btn} a ({x}, {y})")
            
            # Eventi di scroll con precisione migliorata
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