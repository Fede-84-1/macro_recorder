# Macro Recorder (Windows)

Desktop app to record and replay keyboard and mouse macros on Windows. GUI built with PySide6, global hotkeys via pynput. Stores macros in JSON under your user AppData using `platformdirs`.

## Quick start

1. Install Python 3.10+ (64-bit).
2. In PowerShell:

```powershell
python -m venv .venv
. .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m app.main
```

## Default global hotkeys

- Ctrl+Alt+R: Start/stop recording
- Ctrl+Alt+M: Show/hide main window
- Ctrl+Alt+E: Execute last saved macro

These can be changed in Settings inside the app.

## Build portable .exe

```powershell
pyinstaller --name MacroRecorder --noconsole --onefile --add-data "assets;assets" app\start.pyw
```

The generated executable will be in `dist/`.

## Notes

- Recording captures key presses/releases and mouse moves/clicks with timestamps.
- Playback can run with original pauses or without pauses.
- All data is saved to `%LOCALAPPDATA%/MacroRecorder/`.

