import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

# Structures
class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

# Messages and flags
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208

MK_LBUTTON = 0x0001
MK_RBUTTON = 0x0002
MK_MBUTTON = 0x0010

# Prototypes
user32.WindowFromPoint.argtypes = (POINT,)
user32.WindowFromPoint.restype = wintypes.HWND

user32.ScreenToClient.argtypes = (wintypes.HWND, ctypes.POINTER(POINT))
user32.ScreenToClient.restype = wintypes.BOOL

user32.PostMessageW.argtypes = (wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
user32.PostMessageW.restype = wintypes.BOOL


def _make_lparam(x: int, y: int) -> int:
    return (y & 0xFFFF) << 16 | (x & 0xFFFF)


def _btn_msgs(button: str):
    b = button.lower()
    if b == "left":
        return WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON
    if b == "right":
        return WM_RBUTTONDOWN, WM_RBUTTONUP, MK_RBUTTON
    return WM_MBUTTONDOWN, WM_MBUTTONUP, MK_MBUTTON


def post_click_at_screen(x: int, y: int, button: str = "left") -> bool:
    pt = POINT(int(x), int(y))
    hwnd = user32.WindowFromPoint(pt)
    if not hwnd:
        return False
    # convert to client coords
    client = POINT(pt.x, pt.y)
    if not user32.ScreenToClient(hwnd, ctypes.byref(client)):
        return False
    down_msg, up_msg, wbtn = _btn_msgs(button)
    lparam = _make_lparam(client.x, client.y)
    # Optional move
    user32.PostMessageW(hwnd, WM_MOUSEMOVE, 0, lparam)
    # Down/Up
    user32.PostMessageW(hwnd, down_msg, wbtn, lparam)
    user32.PostMessageW(hwnd, up_msg, 0, lparam)
    return True
