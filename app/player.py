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
        # Tracciamento specifico e dettagliato dei modificatori
        self._active_modifiers: Set[str] = set()
        self._modifier_press_count: Dict[str, int] = {}
        self._last_key_time: Dict[str, float] = {}  # Per gestire tasti ripetuti
        self._mouse_button_states: Dict[str, bool] = {}  # Tracciamento pulsanti mouse

    def stop(self) -> None:
        """Ferma la riproduzione in corso"""
        self._stop_flag.set()

    def play(self, events: Iterable[Event], with_pauses: bool = True, repetitions: int = 1, macro: Macro | None = None) -> None:
        """
        Riproduce una sequenza di eventi registrati con gestione corretta dei modificatori
        
        Args:
            events: Gli eventi da riprodurre
            with_pauses: Se True, mantiene i tempi originali tra gli eventi
            repetitions: Numero di ripetizioni della macro
            macro: L'oggetto Macro completo (opzionale)
        """
        self._stop_flag.clear()
        self._pressed_keys.clear()
        self._active_modifiers.clear()
        self._modifier_press_count.clear()
        self._last_key_time.clear()
        self._mouse_button_states.clear()
        
        preserve_cursor = bool(getattr(macro, "preserve_cursor", False))
        original_pos = get_cursor_pos() if preserve_cursor else None
        
        try:
            # FASE CRITICA: Assicurati che tutti i modificatori siano rilasciati prima di iniziare
            self._force_release_all_modifiers()
            
            for rep in range(max(1, int(repetitions))):
                logger.info("Inizio ripetizione {} di {}", rep + 1, repetitions)
                
                # Pulisci lo stato tra le ripetizioni per evitare accumulo di tasti bloccati
                if rep > 0:
                    self._force_release_all_keys()
                    time.sleep(0.1)  # Pausa più lunga tra ripetizioni per stabilità
                
                for ev in events:
                    if self._stop_flag.is_set():
                        return
                    
                    # Gestione migliorata dei ritardi temporali
                    if with_pauses and getattr(ev, "time_delta_ms", 0) > 0:
                        delay = max(0, ev.time_delta_ms) / 1000.0
                        time.sleep(delay)
                    elif not with_pauses:
                        # CORREZIONE CRITICA: Gestione migliorata per caratteri ripetuti
                        if isinstance(ev, KeyEvent):
                            key = ev.key
                            current_time = time.time()
                            
                            # Logica migliorata per evitare perdita di caratteri ripetuti
                            if key in self._last_key_time:
                                time_since_last = current_time - self._last_key_time[key]
                                
                                # Se è lo stesso tasto premuto molto di recente, aggiungi ritardo appropriato
                                if ev.action == "press" and time_since_last < 0.02:
                                    # Ritardo specifico per tasti ripetuti: più lungo per sicurezza
                                    time.sleep(0.025)  # 25ms per garantire registrazione dei caratteri
                                elif ev.action == "release" and time_since_last < 0.01:
                                    # Ritardo minimo per rilascio per evitare conflitti
                                    time.sleep(0.01)  # 10ms per rilascio pulito
                            
                            self._last_key_time[key] = current_time
                        else:
                            # Piccolo ritardo base per eventi mouse in modalità senza pause
                            time.sleep(0.005)
                    
                    self._play_event(ev, preserve_cursor)
                    
        except Exception as exc:
            logger.exception("Errore durante la riproduzione della macro: {}", exc)
        finally:
            # FASE CRITICA: Rilascio forzato di tutti i tasti alla fine
            self._force_release_all_keys()
            if preserve_cursor and original_pos is not None:
                move_cursor_abs(original_pos[0], original_pos[1])

    def _play_event(self, ev: Event, preserve_cursor: bool) -> None:
        """Riproduce un singolo evento con gestione corretta"""
        if isinstance(ev, KeyEvent):
            self._play_key_event(ev)
        elif isinstance(ev, MouseEvent):
            self._play_mouse_event(ev, preserve_cursor)

    def _is_modifier_key(self, key: str) -> bool:
        """Controlla se un tasto è un modificatore - versione migliorata"""
        key_lower = key.lower().strip()
        
        # Lista completa dei modificatori con tutte le varianti
        modifier_patterns = [
            # Shift e varianti
            'shift', 'left shift', 'right shift', 'maiusc', 'lshift', 'rshift',
            # Ctrl e varianti  
            'ctrl', 'left ctrl', 'right ctrl', 'control', 'lctrl', 'rctrl',
            # Alt e varianti
            'alt', 'left alt', 'right alt', 'alt gr', 'altgr', 'lalt', 'ralt',
            # Windows/Cmd e varianti
            'win', 'left windows', 'right windows', 'windows', 'cmd', 'command', 'lwin', 'rwin'
        ]
        
        return any(pattern in key_lower for pattern in modifier_patterns)

    def _normalize_modifier_key(self, key: str) -> str:
        """Normalizza i nomi dei tasti modificatori per tracciamento coerente"""
        key_lower = key.lower().strip()
        
        # Normalizzazione Shift
        if any(s in key_lower for s in ['shift', 'maiusc']):
            if any(l in key_lower for l in ['left', 'lshift']):
                return 'left shift'
            elif any(r in key_lower for r in ['right', 'rshift']):
                return 'right shift'
            return 'shift'
        
        # Normalizzazione Ctrl
        if any(c in key_lower for c in ['ctrl', 'control']):
            if any(l in key_lower for l in ['left', 'lctrl']):
                return 'left ctrl'
            elif any(r in key_lower for r in ['right', 'rctrl']):
                return 'right ctrl'
            return 'ctrl'
        
        # Normalizzazione Alt
        if 'alt' in key_lower:
            if 'gr' in key_lower or 'altgr' in key_lower:
                return 'alt gr'
            elif any(l in key_lower for l in ['left', 'lalt']):
                return 'left alt'
            elif any(r in key_lower for r in ['right', 'ralt']):
                return 'right alt'
            return 'alt'
        
        # Normalizzazione Windows/Cmd
        if any(w in key_lower for w in ['win', 'windows', 'cmd', 'command']):
            if any(l in key_lower for l in ['left', 'lwin']):
                return 'left windows'
            elif any(r in key_lower for r in ['right', 'rwin']):
                return 'right windows'
            return 'windows'
        
        return key

    def _play_key_event(self, ev: KeyEvent) -> None:
        """
        Riproduce un evento tastiera con gestione bilanciata dei modificatori
        CORREZIONE: Bilanciamento tra sicurezza modificatori e funzionalità normale
        """
        key = ev.key.strip()
        
        # Normalizza il nome del tasto se è un modificatore
        if self._is_modifier_key(key):
            key = self._normalize_modifier_key(key)
        
        try:
            if ev.action == "press":
                # Tracciamento per modificatori
                if self._is_modifier_key(key):
                    self._active_modifiers.add(key)
                    self._modifier_press_count[key] = self._modifier_press_count.get(key, 0) + 1
                    logger.debug(f"Modificatore attivato: {key}")
                
                keyboard.press(key)
                self._pressed_keys.add(key)
                logger.debug(f"Tasto premuto: {key}")
                
                # Pausa minima per assicurare la registrazione
                time.sleep(0.001)
                
            elif ev.action == "release":
                # Rilascio normale per tutti i tasti
                keyboard.release(key)
                self._pressed_keys.discard(key)
                
                # Gestione speciale SOLO per modificatori
                if self._is_modifier_key(key):
                    # Aggiorna contatori
                    if key in self._modifier_press_count:
                        self._modifier_press_count[key] = max(0, self._modifier_press_count[key] - 1)
                        if self._modifier_press_count[key] == 0:
                            self._active_modifiers.discard(key)
                    
                    # SOLO per modificatori: rilascio di sicurezza singolo
                    time.sleep(0.005)  # Breve pausa
                    try:
                        keyboard.release(key)  # Un solo rilascio aggiuntivo per sicurezza
                        logger.debug(f"Modificatore rilasciato: {key}")
                    except Exception as e:
                        logger.debug(f"Rilascio sicurezza modificatore fallito per {key}: {e}")
                else:
                    # Per tasti normali, solo una breve pausa
                    time.sleep(0.001)
                
                logger.debug(f"Tasto rilasciato: {key}")
                
        except Exception as exc:
            logger.debug(f"Errore durante riproduzione evento tastiera {key}: {exc}")

    def _play_mouse_event(self, ev: MouseEvent, preserve_cursor: bool) -> None:
        """
        Riproduce un evento mouse con gestione corretta dei pulsanti press/release
        CORREZIONE CRITICA: Implementazione corretta degli eventi press/release per trascinamento
        """
        
        # Gestisce eventi di movimento
        if ev.action == "move":
            self._safe_move(ev.x, ev.y, preserve_cursor)
            return
        
        # CORREZIONE CRITICA: Gestione corretta degli eventi press/release per trascinamento
        if ev.action == "press":
            btn = _normalize_button_name(ev.button)
            logger.debug(f"Inizio pressione mouse: {btn} a ({ev.x}, {ev.y})")
            
            # Muovi alla posizione se non preserva il cursore
            if not preserve_cursor:
                move_cursor_abs(ev.x, ev.y)
                time.sleep(0.02)  # Pausa per assicurare il posizionamento
            
            # Esegui la pressione del pulsante
            try:
                mouse_down(btn)
                self._mouse_button_states[btn] = True
                logger.debug(f"Pulsante mouse premuto: {btn}")
                time.sleep(0.01)  # Pausa per stabilità
            except Exception as exc:
                logger.debug(f"Errore durante pressione mouse: {exc}")
            
            return
        
        if ev.action == "release":
            btn = _normalize_button_name(ev.button)
            logger.debug(f"Fine pressione mouse: {btn} a ({ev.x}, {ev.y})")
            
            # Muovi alla posizione finale se non preserva il cursore
            if not preserve_cursor:
                move_cursor_abs(ev.x, ev.y)
                time.sleep(0.02)  # Pausa per assicurare il posizionamento
            
            # Rilascia il pulsante
            try:
                mouse_up(btn)
                self._mouse_button_states[btn] = False
                logger.debug(f"Pulsante mouse rilasciato: {btn}")
                time.sleep(0.01)  # Pausa per stabilità
            except Exception as exc:
                logger.debug(f"Errore durante rilascio mouse: {exc}")
            
            return
        
        # Gestisce eventi click (per compatibility con registrazioni esistenti)
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

    def _safe_move(self, x: int, y: int, preserve_cursor: bool) -> None:
        """Muove il cursore in modo sicuro"""
        if not preserve_cursor:
            move_cursor_abs(x, y)
            time.sleep(0.003)  # Ritardo ottimizzato per movimento fluido

    def _force_release_all_modifiers(self) -> None:
        """
        Rilascio sicuro di tutti i modificatori conosciuti - versione bilanciata
        CORREZIONE: Metodo meno aggressivo per evitare interferenze con tasti normali
        """
        # Lista di modificatori essenziali (solo i più comuni)
        essential_modifiers = [
            'shift', 'left shift', 'right shift',
            'ctrl', 'left ctrl', 'right ctrl', 
            'alt', 'left alt', 'right alt',
            'windows', 'left windows', 'right windows'
        ]
        
        for modifier in essential_modifiers:
            try:
                # Rilascio singolo più sicuro
                keyboard.release(modifier)
                time.sleep(0.001)  # Pausa minima
            except Exception:
                pass
        
        # Pulizia dello stato interno
        self._active_modifiers.clear()
        self._modifier_press_count.clear()
        
        # Pausa ridotta per non rallentare troppo
        time.sleep(0.02)
        logger.debug("Rilascio sicuro modificatori completato")

    def _force_release_all_keys(self) -> None:
        """
        Rilascia in sicurezza tutti i tasti premuti e i pulsanti mouse
        CORREZIONE: Versione bilanciata che non interferisce con l'input normale
        """
        # Rilascia tutti i tasti tracciati
        for key in list(self._pressed_keys):
            try:
                keyboard.release(key)
                logger.debug(f"Rilasciato tasto: {key}")
            except Exception:
                pass
        self._pressed_keys.clear()
        
        # Rilascia tutti i pulsanti mouse premuti
        for btn, is_pressed in list(self._mouse_button_states.items()):
            if is_pressed:
                try:
                    mouse_up(btn)
                    logger.debug(f"Rilasciato pulsante mouse: {btn}")
                except Exception:
                    pass
        self._mouse_button_states.clear()
        
        # Rilascio sicuro dei modificatori (meno aggressivo)
        self._force_release_all_modifiers()
        
        # Pulizia dello stato interno
        self._last_key_time.clear()
        
        logger.debug("Pulizia stato tasti completata")

    def _release_all_keys(self) -> None:
        """Metodo di compatibilità - chiama la versione potenziata"""
        self._force_release_all_keys()

    def _release_stuck_keys(self) -> None:
        """Metodo legacy per compatibilità - chiama la versione potenziata"""
        self._force_release_all_keys()