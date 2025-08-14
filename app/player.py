from __future__ import annotations

import threading
import time
from typing import Iterable, Set, Any, Dict

from loguru import logger
import keyboard  # type: ignore

from .models import Event, KeyEvent, MouseEvent, Macro
from .wininput import move_cursor_abs, mouse_down, mouse_up, mouse_click, mouse_wheel, get_cursor_pos

try:
    import pydirectinput  # type: ignore
    pydirectinput.PAUSE = 0  # Rimuove la pausa predefinita tra le azioni
    _HAS_PYDIRECT = True
except Exception:
    _HAS_PYDIRECT = False

try:
    import pyautogui  # type: ignore
    pyautogui.PAUSE = 0  # Rimuove la pausa predefinita tra le azioni
    _HAS_PYAUTOGUI = True
except Exception:
    _HAS_PYAUTOGUI = False

try:
    from .winmsg import post_click_at_screen  # type: ignore
    _HAS_WINMSG = True
except Exception:
    _HAS_WINMSG = False


def _normalize_button_name(btn: Any | None) -> str:
    """Normalizza il nome del pulsante del mouse"""
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
        # Tracciamento dettagliato dei modificatori
        self._modifier_states: Dict[str, bool] = {}
        self._last_key_time: Dict[str, float] = {}  # Per gestire tasti ripetuti

    def stop(self) -> None:
        """Ferma la riproduzione in corso"""
        self._stop_flag.set()

    def play(self, events: Iterable[Event], with_pauses: bool = True, repetitions: int = 1, macro: Macro | None = None) -> None:
        """
        Riproduce una sequenza di eventi registrati
        
        Args:
            events: Gli eventi da riprodurre
            with_pauses: Se True, mantiene i tempi originali tra gli eventi
            repetitions: Numero di ripetizioni della macro
            macro: L'oggetto Macro completo (opzionale)
        """
        self._stop_flag.clear()
        self._pressed_keys.clear()
        self._modifier_states.clear()
        self._last_key_time.clear()
        
        preserve_cursor = bool(getattr(macro, "preserve_cursor", False))
        original_pos = get_cursor_pos() if preserve_cursor else None
        
        try:
            # Assicurati che tutti i modificatori siano rilasciati prima di iniziare
            self._ensure_modifiers_released()
            
            for rep in range(max(1, int(repetitions))):
                logger.info("Ripetizione riproduzione {}", rep + 1)
                
                # Pulisci lo stato tra le ripetizioni
                if rep > 0:
                    self._release_all_keys()
                    time.sleep(0.1)  # Breve pausa tra ripetizioni
                
                for ev in events:
                    if self._stop_flag.is_set():
                        return
                    
                    # Applica i ritardi temporali se with_pauses è abilitato
                    if with_pauses and getattr(ev, "time_delta_ms", 0) > 0:
                        time.sleep(max(0, ev.time_delta_ms) / 1000.0)
                    elif not with_pauses:
                        # In modalità senza pause, aggiungi un piccolo ritardo per i tasti ripetuti
                        if isinstance(ev, KeyEvent):
                            key = ev.key
                            current_time = time.time()
                            if key in self._last_key_time:
                                # Se è lo stesso tasto premuto di recente, aggiungi un piccolo ritardo
                                if current_time - self._last_key_time[key] < 0.01:
                                    time.sleep(0.015)  # 15ms di ritardo per tasti ripetuti
                            self._last_key_time[key] = current_time
                    
                    self._play_event(ev, preserve_cursor)
                    
        finally:
            # Rilascia tutti i tasti alla fine
            self._release_all_keys()
            if preserve_cursor and original_pos is not None:
                move_cursor_abs(original_pos[0], original_pos[1])

    def _play_event(self, ev: Event, preserve_cursor: bool) -> None:
        """Riproduce un singolo evento"""
        if isinstance(ev, KeyEvent):
            self._play_key(ev)
        elif isinstance(ev, MouseEvent):
            self._play_mouse(ev, preserve_cursor)

    def _is_modifier_key(self, key: str) -> bool:
        """Controlla se un tasto è un modificatore"""
        key_lower = key.lower()
        modifiers = [
            'shift', 'left shift', 'right shift', 'maiusc',
            'ctrl', 'left ctrl', 'right ctrl', 'control',
            'alt', 'left alt', 'right alt', 'alt gr',
            'win', 'left windows', 'right windows', 'windows', 'cmd', 'command'
        ]
        return any(mod in key_lower for mod in modifiers)

    def _normalize_modifier_key(self, key: str) -> str:
        """Normalizza i nomi dei tasti modificatori per coerenza"""
        key_lower = key.lower()
        
        # Mappa le varianti di Shift
        if any(s in key_lower for s in ['shift', 'maiusc']):
            if 'left' in key_lower:
                return 'left shift'
            elif 'right' in key_lower:
                return 'right shift'
            return 'shift'
        
        # Mappa le varianti di Ctrl
        if any(c in key_lower for c in ['ctrl', 'control']):
            if 'left' in key_lower:
                return 'left ctrl'
            elif 'right' in key_lower:
                return 'right ctrl'
            return 'ctrl'
        
        # Mappa le varianti di Alt
        if 'alt' in key_lower:
            if 'gr' in key_lower:
                return 'alt gr'
            elif 'left' in key_lower:
                return 'left alt'
            elif 'right' in key_lower:
                return 'right alt'
            return 'alt'
        
        # Mappa le varianti di Windows
        if any(w in key_lower for w in ['win', 'windows', 'cmd', 'command']):
            if 'left' in key_lower:
                return 'left windows'
            elif 'right' in key_lower:
                return 'right windows'
            return 'windows'
        
        return key

    def _play_key(self, ev: KeyEvent) -> None:
        """Riproduce un evento tastiera con gestione corretta dei modificatori"""
        key = ev.key
        
        # Normalizza il nome del tasto se è un modificatore
        if self._is_modifier_key(key):
            key = self._normalize_modifier_key(key)
        
        try:
            if ev.action == "press":
                # Prima di premere un nuovo tasto, assicurati che i modificatori siano nello stato corretto
                if self._is_modifier_key(key):
                    # Se è un modificatore, traccia il suo stato
                    self._modifier_states[key] = True
                
                keyboard.press(key)
                self._pressed_keys.add(key)
                logger.debug(f"Tasto premuto: {key}")
                
            elif ev.action == "release":
                # Rilascia il tasto
                keyboard.release(key)
                self._pressed_keys.discard(key)
                
                # Se è un modificatore, aggiorna il suo stato
                if self._is_modifier_key(key):
                    self._modifier_states[key] = False
                    # Forza il rilascio per sicurezza
                    time.sleep(0.005)  # Piccolo ritardo per assicurare il rilascio
                    keyboard.release(key)  # Doppio rilascio per sicurezza
                
                logger.debug(f"Tasto rilasciato: {key}")
                
        except Exception as exc:
            logger.debug(f"Errore durante la riproduzione dell'evento tastiera: {exc}")

    def _safe_move(self, x: int, y: int, preserve_cursor: bool) -> None:
        """Muove il cursore in modo sicuro"""
        if not preserve_cursor:
            move_cursor_abs(x, y)
            time.sleep(0.005)  # Ritardo molto breve per movimento più fluido

    def _play_mouse(self, ev: MouseEvent, preserve_cursor: bool) -> None:
        """Riproduce un evento mouse evitando duplicazioni"""
        
        # IMPORTANTE: Ignora gli eventi press/release se c'è anche un evento click
        # per evitare click multipli
        if ev.action in ("press", "release"):
            # Questi eventi vengono gestiti solo per operazioni di trascinamento
            # Non li eseguiamo per click normali poiché l'evento "click" li gestisce già
            logger.debug(f"Ignorato evento mouse {ev.action} per evitare duplicazioni")
            return
        
        # Gestisce eventi click con priorità
        if ev.action == "click":
            btn = _normalize_button_name(ev.button)
            logger.debug(f"Riproduzione click mouse: {btn} a ({ev.x}, {ev.y})")
            
            # Se preserva il cursore ed è disponibile PostMessage
            if preserve_cursor and _HAS_WINMSG:
                try:
                    if post_click_at_screen(ev.x, ev.y, btn):
                        logger.debug("Click inviato tramite PostMessage")
                        return
                except Exception as exc:
                    logger.debug(f"PostMessage fallito: {exc}")
            
            # Muovi alla posizione se non preserva il cursore
            if not preserve_cursor:
                move_cursor_abs(ev.x, ev.y)
                time.sleep(0.02)  # Ritardo più lungo per assicurare il posizionamento
            
            # Esegui il click usando l'API Windows nativa
            try:
                mouse_click(btn)
                logger.debug("Click eseguito tramite API Windows nativa")
                time.sleep(0.03)  # Ritardo dopo il click per evitare problemi
            except Exception as exc:
                logger.debug(f"API Windows nativa fallita: {exc}")
                
                # Fallback a pydirectinput
                if _HAS_PYDIRECT:
                    try:
                        if not preserve_cursor:
                            pydirectinput.moveTo(ev.x, ev.y)
                        pydirectinput.click(button=btn)
                        logger.debug("Click eseguito tramite pydirectinput")
                    except Exception as exc:
                        logger.debug(f"pydirectinput fallito: {exc}")
            
            return
        
        # Gestisce eventi di movimento
        if ev.action == "move":
            self._safe_move(ev.x, ev.y, preserve_cursor)
            return
        
        # Gestisce eventi di scroll
        if ev.action == "scroll":
            logger.debug(f"Riproduzione scroll mouse: {ev.dy} a ({ev.x}, {ev.y})")
            try:
                mouse_wheel(ev.dy or 0)
                logger.debug("Scroll eseguito tramite API Windows nativa")
            except Exception as exc:
                logger.debug(f"Scroll nativo fallito: {exc}")
                if _HAS_PYAUTOGUI:
                    try:
                        pyautogui.scroll(ev.dy or 0, x=ev.x, y=ev.y)
                        logger.debug("Scroll eseguito tramite pyautogui")
                    except Exception as exc2:
                        logger.debug(f"Scroll pyautogui fallito: {exc2}")
            return

    def _ensure_modifiers_released(self) -> None:
        """Assicura che tutti i modificatori siano rilasciati prima di iniziare"""
        modifiers = [
            'shift', 'left shift', 'right shift',
            'ctrl', 'left ctrl', 'right ctrl',
            'alt', 'left alt', 'right alt', 'alt gr',
            'win', 'left windows', 'right windows', 'windows', 'cmd'
        ]
        
        for mod in modifiers:
            try:
                keyboard.release(mod)
            except Exception:
                pass
        
        time.sleep(0.05)  # Breve pausa per assicurare il rilascio

    def _release_all_keys(self) -> None:
        """Rilascia tutti i tasti premuti e i modificatori"""
        # Prima rilascia tutti i tasti tracciati
        for key in list(self._pressed_keys):
            try:
                keyboard.release(key)
                logger.debug(f"Rilasciato tasto bloccato: {key}")
            except Exception:
                pass
        self._pressed_keys.clear()
        
        # Poi rilascia tutti i modificatori conosciuti
        self._ensure_modifiers_released()
        
        # Pulisci gli stati dei modificatori
        self._modifier_states.clear()

    def _release_stuck_keys(self) -> None:
        """Metodo legacy per compatibilità - chiama _release_all_keys"""
        self._release_all_keys()