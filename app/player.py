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
        # CORREZIONE CRITICA PROBLEMA 1: Tracciamento dettagliato modificatori
        self._active_modifiers: Set[str] = set()
        self._modifier_balance: Dict[str, int] = {}  # Contatore press/release per ogni modificatore
        self._key_sequence_timing: Dict[str, float] = {}  # CORREZIONE PROBLEMA 2: Timing per tasti ripetuti
        self._mouse_button_states: Dict[str, bool] = {}
        self._forced_cleanup_enabled = True  # Controllo per cleanup forzato modificatori

    def stop(self) -> None:
        """Ferma la riproduzione in corso"""
        self._stop_flag.set()

    def play(self, events: Iterable[Event], with_pauses: bool = True, repetitions: int = 1, macro: Macro | None = None) -> None:
        """
        Riproduce una sequenza di eventi con correzioni per i problemi identificati
        
        CORREZIONE PROBLEMA 1: Gestione robusta dei modificatori
        CORREZIONE PROBLEMA 2: Timing ottimizzato per tasti ripetuti
        """
        self._stop_flag.clear()
        self._reset_all_states()
        
        preserve_cursor = bool(getattr(macro, "preserve_cursor", False))
        original_pos = get_cursor_pos() if preserve_cursor else None
        
        try:
            # FASE PRELIMINARE: Cleanup completo modificatori
            self._emergency_cleanup_modifiers()
            
            for rep in range(max(1, int(repetitions))):
                logger.info("Inizio ripetizione {} di {}", rep + 1, repetitions)
                
                # CORREZIONE: Pulizia completa tra ripetizioni
                if rep > 0:
                    self._complete_state_reset()
                    time.sleep(0.05)  # Pausa più lunga per stabilità
                
                # CORREZIONE PROBLEMA 2: Preprocessing per ottimizzare timing tasti ripetuti
                events_list = list(events)
                self._optimize_repeated_key_timing(events_list, with_pauses)
                
                for ev in events_list:
                    if self._stop_flag.is_set():
                        return
                    
                    # CORREZIONE PROBLEMA 2: Gestione intelligente timing
                    if with_pauses and getattr(ev, "time_delta_ms", 0) > 0:
                        delay = max(0, ev.time_delta_ms) / 1000.0
                        time.sleep(delay)
                    elif not with_pauses:
                        self._apply_intelligent_delay(ev)
                    
                    self._play_event(ev, preserve_cursor)
                    
        except Exception as exc:
            logger.exception("Errore durante la riproduzione della macro: {}", exc)
        finally:
            # FASE FINALE: Cleanup garantito
            self._guaranteed_cleanup()
            if preserve_cursor and original_pos is not None:
                move_cursor_abs(original_pos[0], original_pos[1])

    def _reset_all_states(self) -> None:
        """Reset completo di tutti gli stati interni"""
        self._pressed_keys.clear()
        self._active_modifiers.clear()
        self._modifier_balance.clear()
        self._key_sequence_timing.clear()
        self._mouse_button_states.clear()

    def _emergency_cleanup_modifiers(self) -> None:
        """
        CORREZIONE CRITICA PROBLEMA 1: Cleanup di emergenza per modificatori bloccati
        """
        logger.debug("Esecuzione cleanup di emergenza modificatori")
        
        # Lista completa modificatori Windows
        all_modifiers = [
            'shift', 'left shift', 'right shift',
            'ctrl', 'left ctrl', 'right ctrl', 'control',
            'alt', 'left alt', 'right alt', 'alt gr',
            'win', 'windows', 'left windows', 'right windows', 'cmd'
        ]
        
        # Rilascio forzato multiplo per garantire pulizia
        for modifier in all_modifiers:
            for attempt in range(3):  # Tre tentativi per sicurezza
                try:
                    keyboard.release(modifier)
                    time.sleep(0.002)  # Micro-pausa tra rilasci
                except Exception:
                    continue
        
        # Pausa finale per stabilizzazione sistema
        time.sleep(0.03)
        logger.debug("Cleanup modificatori completato")

    def _optimize_repeated_key_timing(self, events_list: list, with_pauses: bool) -> None:
        """
        CORREZIONE PROBLEMA 2: Preprocessing per ottimizzare timing tasti ripetuti
        """
        if with_pauses:
            return  # Non modificare se con pause originali
        
        # Identifica sequenze di tasti ripetuti
        for i in range(len(events_list) - 1):
            if isinstance(events_list[i], KeyEvent) and isinstance(events_list[i + 1], KeyEvent):
                current_key = events_list[i].key
                next_key = events_list[i + 1].key
                
                # Se stesso tasto consecutivo, marca per timing speciale
                if current_key == next_key:
                    self._key_sequence_timing[f"{current_key}_{i}"] = time.time()

    def _apply_intelligent_delay(self, ev: Event) -> None:
        """
        CORREZIONE PROBLEMA 2: Applica ritardi intelligenti per evitare perdita tasti
        """
        if isinstance(ev, KeyEvent):
            key = ev.key
            current_time = time.time()
            
            # Calcola ritardo basato su tipo di evento e storia
            base_delay = 0.003  # Ritardo base ridotto
            
            # CORREZIONE: Ritardo maggiore per tasti ripetuti consecutivi
            if key in self._key_sequence_timing:
                last_time = self._key_sequence_timing.get(key, 0)
                if current_time - last_time < 0.05:  # Se molto vicino nel tempo
                    if ev.action == "press":
                        time.sleep(0.020)  # 20ms per press di tasti ripetuti
                    else:
                        time.sleep(0.010)  # 10ms per release
                else:
                    time.sleep(base_delay)
            else:
                time.sleep(base_delay)
            
            # Aggiorna timing
            self._key_sequence_timing[key] = current_time
        else:
            # Ritardo standard per eventi mouse
            time.sleep(0.005)

    def _is_modifier_key(self, key: str) -> bool:
        """Controlla se un tasto è un modificatore"""
        key_lower = key.lower().strip()
        modifier_keywords = [
            'shift', 'ctrl', 'control', 'alt', 'win', 'windows', 
            'cmd', 'command', 'maiusc', 'altgr', 'alt gr'
        ]
        return any(keyword in key_lower for keyword in modifier_keywords)

    def _normalize_modifier_name(self, key: str) -> str:
        """Normalizza nomi modificatori per tracciamento coerente"""
        key_lower = key.lower().strip()
        
        # Mappatura completa normalizzazione
        if any(s in key_lower for s in ['shift', 'maiusc']):
            if 'left' in key_lower:
                return 'left shift'
            elif 'right' in key_lower:
                return 'right shift'
            return 'shift'
        
        if any(c in key_lower for c in ['ctrl', 'control']):
            if 'left' in key_lower:
                return 'left ctrl'
            elif 'right' in key_lower:
                return 'right ctrl'
            return 'ctrl'
        
        if 'alt' in key_lower:
            if 'gr' in key_lower:
                return 'alt gr'
            elif 'left' in key_lower:
                return 'left alt'
            elif 'right' in key_lower:
                return 'right alt'
            return 'alt'
        
        if any(w in key_lower for w in ['win', 'windows', 'cmd']):
            if 'left' in key_lower:
                return 'left windows'
            elif 'right' in key_lower:
                return 'right windows'
            return 'windows'
        
        return key

    def _play_event(self, ev: Event, preserve_cursor: bool) -> None:
        """Riproduce un singolo evento"""
        if isinstance(ev, KeyEvent):
            self._play_key_event(ev)
        elif isinstance(ev, MouseEvent):
            self._play_mouse_event(ev, preserve_cursor)

    def _play_key_event(self, ev: KeyEvent) -> None:
        """
        CORREZIONE PROBLEMA 1: Gestione bilanciata modificatori con tracking preciso
        """
        key = ev.key.strip()
        
        if self._is_modifier_key(key):
            key = self._normalize_modifier_name(key)
        
        try:
            if ev.action == "press":
                # TRACKING MODIFICATORI
                if self._is_modifier_key(key):
                    self._active_modifiers.add(key)
                    self._modifier_balance[key] = self._modifier_balance.get(key, 0) + 1
                    logger.debug(f"Modificatore premuto: {key} (balance: {self._modifier_balance[key]})")
                
                keyboard.press(key)
                self._pressed_keys.add(key)
                time.sleep(0.002)  # Pausa per stabilità
                
            elif ev.action == "release":
                keyboard.release(key)
                self._pressed_keys.discard(key)
                
                # GESTIONE BILANCIAMENTO MODIFICATORI
                if self._is_modifier_key(key):
                    if key in self._modifier_balance:
                        self._modifier_balance[key] = max(0, self._modifier_balance[key] - 1)
                        if self._modifier_balance[key] == 0:
                            self._active_modifiers.discard(key)
                    
                    # CORREZIONE: Rilascio di sicurezza per modificatori
                    time.sleep(0.003)
                    try:
                        keyboard.release(key)  # Rilascio doppio per sicurezza
                        logger.debug(f"Modificatore rilasciato: {key} (balance: {self._modifier_balance.get(key, 0)})")
                    except Exception:
                        pass
                else:
                    time.sleep(0.001)
                
        except Exception as exc:
            logger.debug(f"Errore evento tastiera {key}: {exc}")

    def _play_mouse_event(self, ev: MouseEvent, preserve_cursor: bool) -> None:
        """Riproduce eventi mouse con gestione corretta press/release"""
        if ev.action == "move":
            self._safe_move(ev.x, ev.y, preserve_cursor)
            return
        
        if ev.action == "press":
            btn = _normalize_button_name(ev.button)
            if not preserve_cursor:
                move_cursor_abs(ev.x, ev.y)
                time.sleep(0.015)
            
            try:
                mouse_down(btn)
                self._mouse_button_states[btn] = True
                time.sleep(0.008)
            except Exception as exc:
                logger.debug(f"Errore press mouse: {exc}")
            return
        
        if ev.action == "release":
            btn = _normalize_button_name(ev.button)
            if not preserve_cursor:
                move_cursor_abs(ev.x, ev.y)
                time.sleep(0.015)
            
            try:
                mouse_up(btn)
                self._mouse_button_states[btn] = False
                time.sleep(0.008)
            except Exception as exc:
                logger.debug(f"Errore release mouse: {exc}")
            return
        
        if ev.action == "click":
            btn = _normalize_button_name(ev.button)
            
            if preserve_cursor and _HAS_WINMSG:
                try:
                    if post_click_at_screen(ev.x, ev.y, btn):
                        return
                except Exception:
                    pass
            
            if not preserve_cursor:
                move_cursor_abs(ev.x, ev.y)
                time.sleep(0.015)
            
            try:
                mouse_click(btn)
                time.sleep(0.020)
            except Exception as exc:
                logger.debug(f"Errore click mouse: {exc}")
            return
        
        if ev.action == "scroll":
            try:
                mouse_wheel(ev.dy or 0)
            except Exception as exc:
                logger.debug(f"Errore scroll: {exc}")

    def _safe_move(self, x: int, y: int, preserve_cursor: bool) -> None:
        """Movimento sicuro cursore"""
        if not preserve_cursor:
            move_cursor_abs(x, y)
            time.sleep(0.003)

    def _complete_state_reset(self) -> None:
        """
        CORREZIONE PROBLEMA 1: Reset completo dello stato con cleanup forzato
        """
        # Rilascio tutti i tasti tracciati
        for key in list(self._pressed_keys):
            try:
                keyboard.release(key)
            except Exception:
                pass
        
        # Rilascio pulsanti mouse
        for btn, is_pressed in list(self._mouse_button_states.items()):
            if is_pressed:
                try:
                    mouse_up(btn)
                except Exception:
                    pass
        
        # CORREZIONE: Cleanup specifico modificatori bloccati
        for modifier in list(self._active_modifiers):
            balance = self._modifier_balance.get(modifier, 0)
            for _ in range(max(1, balance)):  # Rilascia tante volte quanto premuto
                try:
                    keyboard.release(modifier)
                    time.sleep(0.002)
                except Exception:
                    pass
        
        # Reset completo stati
        self._reset_all_states()
        
        # Cleanup di emergenza finale
        if self._forced_cleanup_enabled:
            self._emergency_cleanup_modifiers()

    def _guaranteed_cleanup(self) -> None:
        """Cleanup garantito alla fine della riproduzione"""
        logger.debug("Esecuzione cleanup garantito finale")
        self._complete_state_reset()
        time.sleep(0.02)  # Pausa finale per stabilizzazione
        logger.debug("Cleanup garantito completato")

    # Metodi legacy per compatibilità
    def _force_release_all_keys(self) -> None:
        """Compatibilità - chiama il nuovo metodo"""
        self._complete_state_reset()

    def _release_all_keys(self) -> None:
        """Compatibilità - chiama il nuovo metodo"""
        self._complete_state_reset()