"""
Modulo per l'interazione con le API Windows native per mouse e tastiera
MIGLIORAMENTO: Gestione più robusta degli eventi mouse per il problema press/release
"""

import time
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

# Compatibilità ULONG_PTR
try:
    ULONG_PTR = wintypes.ULONG_PTR  # type: ignore[attr-defined]
except AttributeError:
    ULONG_PTR = ctypes.c_uint64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_uint32

# Mouse event flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_ABSOLUTE = 0x8000

WHEEL_DELTA = 120

# Virtual screen metrics indices
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]

class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

INPUT_MOUSE = 0

# Configure SendInput signature
user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wintypes.UINT

# mouse_event prototype (legacy API)
user32.mouse_event.argtypes = (wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ULONG_PTR)
user32.mouse_event.restype = None

class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

user32.GetCursorPos.argtypes = (ctypes.POINTER(POINT),)
user32.GetCursorPos.restype = wintypes.BOOL

# Configurazione per SetCursorPos (alternativa a SendInput per alcuni casi)
user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
user32.SetCursorPos.restype = wintypes.BOOL


def _send_mouse_input(flags: int, data: int = 0, dx: int = 0, dy: int = 0, retry_count: int = 3) -> bool:
    """
    Invia input mouse usando SendInput API con retry automatico per maggiore affidabilità
    
    Args:
        flags: Flag dell'evento mouse
        data: Dati aggiuntivi (per scroll wheel)
        dx, dy: Coordinate relative
        retry_count: Numero di tentativi in caso di fallimento
        
    Returns:
        True se l'input è stato inviato con successo, False altrimenti
    """
    for attempt in range(retry_count):
        inp = INPUT()
        inp.type = INPUT_MOUSE
        inp.mi = MOUSEINPUT(dx, dy, data, flags, 0, 0)
        
        sent = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        
        if sent > 0:
            return True
        elif attempt < retry_count - 1:
            # Breve pausa prima di riprovare
            time.sleep(0.001)
    
    # Fallback alla legacy API se SendInput continua a fallire
    try:
        user32.mouse_event(flags, dx, dy, data, 0)
        return True
    except Exception:
        return False


def _virtual_screen_metrics():
    """Ottiene le metriche dello schermo virtuale per coordinate assolute"""
    vx = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    vy = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    vw = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    vh = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return vx, vy, vw, vh


def _normalize_abs_coordinates(x: int, y: int) -> tuple[int, int]:
    """
    Converte coordinate fisiche in coordinate assolute normalizzate per SendInput
    
    Args:
        x, y: Coordinate fisiche dello schermo
        
    Returns:
        Tupla delle coordinate normalizzate (0-65535)
    """
    vx, vy, vw, vh = _virtual_screen_metrics()
    
    # Proteggi da divisione per zero
    vw = max(1, vw)
    vh = max(1, vh)
    
    # Clamp le coordinate entro i limiti dello schermo virtuale
    x = max(vx, min(x, vx + vw - 1))
    y = max(vy, min(y, vy + vh - 1))
    
    # Normalizza a 0-65535
    nx = int((x - vx) * 65535 / max(1, vw - 1))
    ny = int((y - vy) * 65535 / max(1, vh - 1))
    
    return nx, ny


def move_cursor_abs(x: int, y: int) -> None:
    """
    Muove il cursore alle coordinate assolute specificate
    MIGLIORAMENTO: Metodo dual con fallback per maggiore affidabilità
    
    Args:
        x, y: Coordinate di destinazione
    """
    x, y = int(x), int(y)
    
    # Metodo 1: Prova con SendInput (preferito)
    nx, ny = _normalize_abs_coordinates(x, y)
    success = _send_mouse_input(
        MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, 
        0, nx, ny
    )
    
    if success:
        time.sleep(0.005)  # Breve pausa per assicurare il movimento
        return
    
    # Metodo 2: Fallback a SetCursorPos (più diretto ma meno flessibile)
    try:
        user32.SetCursorPos(x, y)
        time.sleep(0.005)
    except Exception:
        # Ultimo tentativo con coordinate normalizzate tramite legacy mouse_event
        try:
            user32.mouse_event(
                MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, 
                nx, ny, 0, 0
            )
            time.sleep(0.005)
        except Exception:
            pass  # Se anche questo fallisce, non c'è altro da fare


def set_cursor_pos(x: int, y: int) -> None:
    """Alias per move_cursor_abs per compatibilità"""
    move_cursor_abs(x, y)


def get_cursor_pos() -> tuple[int, int]:
    """
    Ottiene la posizione corrente del cursore
    
    Returns:
        Tupla (x, y) della posizione corrente
    """
    pt = POINT()
    if user32.GetCursorPos(ctypes.byref(pt)):
        return int(pt.x), int(pt.y)
    return 0, 0


def mouse_down(button: str) -> None:
    """
    Preme un pulsante del mouse senza rilasciarlo
    CORREZIONE CRITICA: Implementazione migliorata per eventi press
    
    Args:
        button: Nome del pulsante ('left', 'right', 'middle')
    """
    btn = button.lower().strip()
    
    flag_map = {
        "left": MOUSEEVENTF_LEFTDOWN,
        "right": MOUSEEVENTF_RIGHTDOWN, 
        "middle": MOUSEEVENTF_MIDDLEDOWN
    }
    
    flag = flag_map.get(btn, MOUSEEVENTF_LEFTDOWN)
    
    # Invio dell'evento con retry per affidabilità
    success = _send_mouse_input(flag, 0, 0, 0, retry_count=2)
    
    if success:
        # Breve pausa per assicurare che l'evento sia processato
        time.sleep(0.005)
    else:
        # Log del fallimento per debug (se logger disponibile)
        try:
            from loguru import logger
            logger.debug(f"mouse_down fallito per pulsante: {button}")
        except ImportError:
            pass


def mouse_up(button: str) -> None:
    """
    Rilascia un pulsante del mouse precedentemente premuto
    CORREZIONE CRITICA: Implementazione migliorata per eventi release
    
    Args:
        button: Nome del pulsante ('left', 'right', 'middle')
    """
    btn = button.lower().strip()
    
    flag_map = {
        "left": MOUSEEVENTF_LEFTUP,
        "right": MOUSEEVENTF_RIGHTUP,
        "middle": MOUSEEVENTF_MIDDLEUP
    }
    
    flag = flag_map.get(btn, MOUSEEVENTF_LEFTUP)
    
    # Invio dell'evento con retry per affidabilità
    success = _send_mouse_input(flag, 0, 0, 0, retry_count=2)
    
    if success:
        # Breve pausa per assicurare che l'evento sia processato
        time.sleep(0.005)
    else:
        # Log del fallimento per debug (se logger disponibile)
        try:
            from loguru import logger
            logger.debug(f"mouse_up fallito per pulsante: {button}")
        except ImportError:
            pass


def mouse_click(button: str, click_duration: float = 0.015) -> None:
    """
    Esegue un click completo (press + pausa + release)
    MIGLIORAMENTO: Durata del click personalizzabile per diversi scenari
    
    Args:
        button: Nome del pulsante ('left', 'right', 'middle')
        click_duration: Durata della pressione in secondi (default: 15ms)
    """
    btn = button.lower().strip()
    
    # Mappa dei flag per down e up
    flag_maps = {
        "left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
        "right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
        "middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP)
    }
    
    down_flag, up_flag = flag_maps.get(btn, flag_maps["left"])
    
    # Press
    success_down = _send_mouse_input(down_flag, 0, 0, 0, retry_count=2)
    
    # Pausa configurabile per la durata del click
    time.sleep(max(0.01, click_duration))
    
    # Release
    success_up = _send_mouse_input(up_flag, 0, 0, 0, retry_count=2)
    
    if not (success_down and success_up):
        # Log del fallimento per debug (se logger disponibile)
        try:
            from loguru import logger
            logger.debug(f"mouse_click parzialmente fallito per pulsante: {button} (down: {success_down}, up: {success_up})")
        except ImportError:
            pass
    
    # Pausa finale per evitare eventi troppo rapidi
    time.sleep(0.005)


def mouse_wheel(delta_steps: int) -> None:
    """
    Simula il movimento della rotella del mouse
    MIGLIORAMENTO: Gestione migliorata per scroll più fluidi
    
    Args:
        delta_steps: Numero di "tacche" di scroll (positivo = su, negativo = giù)
    """
    if delta_steps == 0:
        return
    
    # Converti in unità Windows (WHEEL_DELTA = 120 per ogni tacca)
    wheel_data = int(delta_steps * WHEEL_DELTA)
    
    # Invia evento scroll
    success = _send_mouse_input(MOUSEEVENTF_WHEEL, wheel_data, 0, 0, retry_count=2)
    
    if success:
        time.sleep(0.005)  # Breve pausa per fluidità
    else:
        # Log del fallimento per debug (se logger disponibile)
        try:
            from loguru import logger
            logger.debug(f"mouse_wheel fallito per delta: {delta_steps}")
        except ImportError:
            pass


def mouse_double_click(button: str, click_interval: float = 0.05) -> None:
    """
    Esegue un doppio click
    FUNZIONE AGGIUNTIVA: Per compatibilità con eventi di doppio click registrati
    
    Args:
        button: Nome del pulsante ('left', 'right', 'middle')
        click_interval: Intervallo tra i due click in secondi
    """
    mouse_click(button)
    time.sleep(max(0.01, click_interval))
    mouse_click(button)