import time
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

# Compatibilità ULONG_PTR
try:
    ULONG_PTR = wintypes.ULONG_PTR  # type: ignore[attr-defined]
except AttributeError:
    ULONG_PTR = ctypes.c_uint64 if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_uint32

# mouse event flags
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


def _send_mouse(flags: int, data: int = 0, dx: int = 0, dy: int = 0) -> None:
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.mi = MOUSEINPUT(dx, dy, data, flags, 0, 0)
    sent = user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
    if sent == 0:
        user32.mouse_event(flags, dx, dy, data, 0)


def _virtual_screen_metrics():
    vx = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    vy = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    vw = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    vh = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    return vx, vy, vw, vh


def _normalize_abs(x: int, y: int) -> tuple[int, int]:
    vx, vy, vw, vh = _virtual_screen_metrics()
    vw = max(1, vw)
    vh = max(1, vh)
    nx = int((max(vx, min(x, vx + vw)) - vx) * 65535 / (vw - 1 if vw > 1 else 1))
    ny = int((max(vy, min(y, vy + vh)) - vy) * 65535 / (vh - 1 if vh > 1 else 1))
    return nx, ny


def move_cursor_abs(x: int, y: int) -> None:
    nx, ny = _normalize_abs(int(x), int(y))
    _send_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, 0, nx, ny)
    time.sleep(0.01)


def set_cursor_pos(x: int, y: int) -> None:
    move_cursor_abs(x, y)


def get_cursor_pos() -> tuple[int, int]:
    pt = POINT()
    if user32.GetCursorPos(ctypes.byref(pt)):
        return int(pt.x), int(pt.y)
    return 0, 0


def mouse_down(button: str) -> None:
    btn = button.lower()
    if btn == "left":
        _send_mouse(MOUSEEVENTF_LEFTDOWN)
    elif btn == "right":
        _send_mouse(MOUSEEVENTF_RIGHTDOWN)
    elif btn == "middle":
        _send_mouse(MOUSEEVENTF_MIDDLEDOWN)


def mouse_up(button: str) -> None:
    btn = button.lower()
    if btn == "left":
        _send_mouse(MOUSEEVENTF_LEFTUP)
    elif btn == "right":
        _send_mouse(MOUSEEVENTF_RIGHTUP)
    elif btn == "middle":
        _send_mouse(MOUSEEVENTF_MIDDLEUP)


def mouse_click(button: str) -> None:
    mouse_down(button)
    time.sleep(0.02)
    mouse_up(button)


def mouse_wheel(delta_steps: int) -> None:
    _send_mouse(MOUSEEVENTF_WHEEL, int(delta_steps) * WHEEL_DELTA)
