from __future__ import annotations

import sys

from loguru import logger
from PySide6 import QtWidgets, QtCore

from .gui import MainWindow


def main() -> int:
    logger.add(sys.stderr, level="INFO")

    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()

    # collega stop richiesto dal recorder al toggle
    win.recorder.set_on_stop_requested(lambda: QtCore.QTimer.singleShot(0, win.toggle_recording))

    exit_code = app.exec()
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
