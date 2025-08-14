# Macro Recorder (Windows)

Desktop app to record and replay keyboard and mouse macros on Windows. GUI built with PySide6. Stores macros in JSON under your user AppData using `platformdirs`.

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

## Features

- **Record macros**: Click the "Registra" button or use the stop overlay during recording
- **Stop recording**: Click the Stop button (right-click to drag the button)
- **Execute macros**: Double-click a macro or use "Esegui selezionata" button
- **Quick execute**: Use "Esegui ultimo" button to run the last saved macro
- **Toggle pause mode**: Switch between playback with original timing or without pauses
- **Favorites**: Mark macros as favorites to keep them at the top of the list
- **Import/Export**: Save and load macros as JSON files
- **Theme support**: Switch between light and dark themes

## Build portable .exe

```powershell
pyinstaller --name MacroRecorder --noconsole --onefile --add-data "assets;assets" app\start.pyw
```

The generated executable will be in `dist/`.

## Notes

- Recording captures key presses/releases and mouse moves/clicks with timestamps.
- Playback can run with original pauses or without pauses.
- Multiple repetitions can be configured for each macro.
- All data is saved to `%LOCALAPPDATA%/MacroRecorder/`.
- Favorite macros appear at the top of the list for quick access.