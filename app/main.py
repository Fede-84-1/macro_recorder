from __future__ import annotations

import sys
import os

# Aggiungi il percorso del progetto al path Python per risolvere gli import
# Questo è necessario per PyInstaller
if getattr(sys, 'frozen', False):
    # Se eseguito come eseguibile PyInstaller
    application_path = os.path.dirname(sys.executable)
else:
    # Se eseguito come script Python
    application_path = os.path.dirname(os.path.abspath(__file__))
    # Vai alla directory parent per ottenere la root del progetto
    application_path = os.path.dirname(application_path)

# Aggiungi il percorso al sys.path se non è già presente
if application_path not in sys.path:
    sys.path.insert(0, application_path)

from loguru import logger
from PySide6 import QtWidgets, QtCore

# Import assoluti invece di relativi
from app.gui import MainWindow


def main() -> int:
    """Funzione principale dell'applicazione"""
    logger.add(sys.stderr, level="INFO")

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("AutoKey")
    app.setOrganizationName("AutoKey")
    
    win = MainWindow()
    win.show()

    # Collega lo stop richiesto dal recorder al toggle
    win.recorder.set_on_stop_requested(lambda: QtCore.QTimer.singleShot(0, win.toggle_recording))

    exit_code = app.exec()
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())