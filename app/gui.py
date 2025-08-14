from __future__ import annotations

from dataclasses import asdict
import threading
from typing import List, Tuple

from loguru import logger
from PySide6 import QtCore, QtGui, QtWidgets

from .models import Macro
from .player import Player
from .recorder import Recorder
from .storage import load_macros, save_macros, next_recording_title, load_settings, save_settings


class RecordingStopButton(QtWidgets.QPushButton):
    def __init__(self, on_stop: callable) -> None:
        super().__init__("Stop", None)
        self._on_stop = on_stop
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setStyleSheet("QPushButton { background:#d32f2f; color:white; border-radius:12px; padding:6px 10px; font-weight:bold; } QPushButton:hover { background:#b71c1c; }")
        self.adjustSize()
        self._dragging = False
        self._drag_offset = QtCore.QPoint(0, 0)
        self._drag_enabled = False

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        if e.button() == QtCore.Qt.RightButton:
            self._drag_enabled = True
            self._dragging = True
            self._drag_offset = e.globalPosition().toPoint() - self.pos()
        elif e.button() == QtCore.Qt.LeftButton:
            self._on_stop()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e: QtGui.QMouseEvent) -> None:
        if self._drag_enabled and self._dragging and (e.buttons() & QtCore.Qt.RightButton):
            new_pos = e.globalPosition().toPoint() - self._drag_offset
            self.move(new_pos)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        if e.button() == QtCore.Qt.RightButton:
            self._dragging = False
            self._drag_enabled = False
        super().mouseReleaseEvent(e)

    def show_bottom_right(self):
        def _show():
            screen = QtWidgets.QApplication.primaryScreen().geometry()
            x = screen.right() - self.width() - 20
            y = screen.bottom() - self.height() - 50
            self.move(x, y)
            self.show()
        QtCore.QTimer.singleShot(0, _show)


class MacroTableModel(QtCore.QAbstractTableModel):
    HEADERS = ["Titolo", "Con pause", "Ripetizioni", "Preferito"]

    def __init__(self, items: List[Macro]) -> None:
        super().__init__()
        self._original_items = items
        self.items = self._sort_items(items)

    def _sort_items(self, items: List[Macro]) -> List[Macro]:
        # Sort with favorites first, then by title
        favorites = [m for m in items if m.favorite]
        non_favorites = [m for m in items if not m.favorite]
        # Sort each group by title
        favorites.sort(key=lambda m: m.title.lower())
        non_favorites.sort(key=lambda m: m.title.lower())
        return favorites + non_favorites

    def refresh_sorting(self):
        self.beginResetModel()
        self.items = self._sort_items(self._original_items)
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self.items)

    def columnCount(self, parent=None):
        return len(self.HEADERS)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        macro = self.items[index.row()]
        col = index.column()
        if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
            if col == 0:
                return macro.title
            if col == 1:
                return "Con pause" if macro.with_pauses else "Senza pause"
            if col == 2:
                return macro.repetitions
            if col == 3:
                return "★" if macro.favorite else "☆"
        if role == QtCore.Qt.TextAlignmentRole:
            if col in (1, 2, 3):
                return QtCore.Qt.AlignCenter
        if role == QtCore.Qt.BackgroundRole:
            # Highlight favorite rows with a subtle background
            if macro.favorite:
                return QtGui.QColor(255, 248, 220)  # Light yellow for light theme
        return None

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def flags(self, index):
        base = super().flags(index)
        if index.column() in (0, 2):
            return base | QtCore.Qt.ItemIsEditable
        return base

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role != QtCore.Qt.EditRole:
            return False
        m = self.items[index.row()]
        if index.column() == 0:
            m.title = str(value)
        elif index.column() == 2:
            try:
                m.repetitions = max(1, int(value))
            except Exception:
                return False
        else:
            return False
        self.dataChanged.emit(index, index, [QtCore.Qt.DisplayRole])
        return True


class SaveRecordingDialog(QtWidgets.QDialog):
    def __init__(self, default_title: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Salva registrazione")
        self.setModal(True)
        self.title = default_title
        self.with_pauses = True

        layout = QtWidgets.QVBoxLayout(self)
        
        # Title input with label
        title_label = QtWidgets.QLabel("Titolo (lascia vuoto per usare il titolo automatico):")
        layout.addWidget(title_label)
        
        self.ed_title = QtWidgets.QLineEdit()
        self.ed_title.setPlaceholderText(default_title)
        layout.addWidget(self.ed_title)

        buttons = QtWidgets.QDialogButtonBox()
        btn_with = buttons.addButton("Con pause", QtWidgets.QDialogButtonBox.AcceptRole)
        btn_without = buttons.addButton("Senza pause", QtWidgets.QDialogButtonBox.DestructiveRole)
        layout.addWidget(buttons)

        btn_with.clicked.connect(self._accept_with)
        btn_without.clicked.connect(self._accept_without)

    def _accept_with(self):
        self.title = self.ed_title.text().strip() or self.ed_title.placeholderText()
        self.with_pauses = True
        self.accept()

    def _accept_without(self):
        self.title = self.ed_title.text().strip() or self.ed_title.placeholderText()
        self.with_pauses = False
        self.accept()


class MainWindow(QtWidgets.QMainWindow):
    recordingStateChanged = QtCore.Signal(bool)
    playbackFinished = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Macro Recorder")
        self.resize(900, 520)

        # State
        self.recorder = Recorder()
        self.player = Player()
        self.macros: List[Macro] = load_macros()
        self.stopOverlay = RecordingStopButton(self._stop_by_overlay)
        self.settings = load_settings()
        self.current_theme = self.settings.get("ui", {}).get("theme", "light")

        # UI
        self.table_model = MacroTableModel(self.macros)
        self.table = QtWidgets.QTableView()
        self.table.setModel(self.table_model)
        self.table.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QTableView.DoubleClicked | QtWidgets.QTableView.SelectedClicked | QtWidgets.QTableView.EditKeyPressed)
        self.table.setAlternatingRowColors(True)

        toolbar = QtWidgets.QToolBar("Actions")
        self.addToolBar(toolbar)

        act_record = QtGui.QAction("Registra", self)
        act_record.triggered.connect(self.toggle_recording)
        toolbar.addAction(act_record)

        act_play = QtGui.QAction("Esegui selezionata", self)
        act_play.triggered.connect(self.execute_selected)
        toolbar.addAction(act_play)

        act_toggle_pause = QtGui.QAction("Toggle Con/Senza pause", self)
        act_toggle_pause.triggered.connect(self.toggle_with_pauses)
        toolbar.addAction(act_toggle_pause)

        act_fav = QtGui.QAction("Aggiungi/Rimuovi preferiti", self)
        act_fav.triggered.connect(self.toggle_favorite)
        toolbar.addAction(act_fav)

        act_delete = QtGui.QAction("Elimina", self)
        act_delete.triggered.connect(self.delete_selected)
        toolbar.addAction(act_delete)

        toolbar.addSeparator()

        act_export = QtGui.QAction("Esporta JSON", self)
        act_export.triggered.connect(lambda: QtCore.QTimer.singleShot(0, self._do_export))
        toolbar.addAction(act_export)

        act_import = QtGui.QAction("Importa JSON", self)
        act_import.triggered.connect(lambda: QtCore.QTimer.singleShot(0, self._do_import))
        toolbar.addAction(act_import)

        toolbar.addSeparator()

        # Theme toggle action
        self.act_theme = QtGui.QAction("Tema: Chiaro", self)
        self.act_theme.triggered.connect(self.toggle_theme)
        toolbar.addAction(self.act_theme)

        act_help = QtGui.QAction("Aiuto", self)
        act_help.triggered.connect(self.show_help)
        toolbar.addAction(act_help)

        central = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central)
        layout.addWidget(self.table)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_quick = QtWidgets.QPushButton("Esegui ultimo")
        self.btn_quick.clicked.connect(self.execute_last)
        btn_row.addWidget(self.btn_quick)
        layout.addLayout(btn_row)

        self.setCentralWidget(central)

        self.statusBar().showMessage("Pronto")

        QtGui.QShortcut(QtGui.QKeySequence("Delete"), self, self.delete_selected)

        self.playbackFinished.connect(self._restore_window)

        # Apply initial theme
        self._apply_theme(self.current_theme)

    def _apply_theme(self, theme: str):
        if theme == "dark":
            # Dark theme stylesheet
            dark_style = """
            QMainWindow {
                background-color: #2b2b2b;
                color: #f0f0f0;
            }
            QToolBar {
                background-color: #3c3c3c;
                border: none;
                spacing: 3px;
            }
            QToolBar::separator {
                background-color: #555;
                width: 1px;
                margin: 3px;
            }
            QTableView {
                background-color: #2b2b2b;
                alternate-background-color: #323232;
                color: #f0f0f0;
                gridline-color: #555;
                selection-background-color: #4a6ea8;
                selection-color: #ffffff;
            }
            QTableView::item:selected {
                background-color: #4a6ea8;
            }
            QHeaderView::section {
                background-color: #3c3c3c;
                color: #f0f0f0;
                padding: 5px;
                border: 1px solid #555;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: #f0f0f0;
                border: 1px solid #555;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #555;
            }
            QLineEdit {
                background-color: #3c3c3c;
                color: #f0f0f0;
                border: 1px solid #555;
                padding: 3px;
                border-radius: 3px;
            }
            QStatusBar {
                background-color: #3c3c3c;
                color: #f0f0f0;
            }
            QMessageBox {
                background-color: #2b2b2b;
                color: #f0f0f0;
            }
            """
            self.setStyleSheet(dark_style)
            self.act_theme.setText("Tema: Scuro")
            # Update table model for dark theme favorite highlighting
            self.table_model.beginResetModel()
            self.table_model.endResetModel()
        else:
            # Light theme (default)
            self.setStyleSheet("")
            self.act_theme.setText("Tema: Chiaro")
            # Reset table model for light theme
            self.table_model.beginResetModel()
            self.table_model.endResetModel()

    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self._apply_theme(self.current_theme)
        # Save theme preference
        if "ui" not in self.settings:
            self.settings["ui"] = {}
        self.settings["ui"]["theme"] = self.current_theme
        save_settings(self.settings)
        self.statusBar().showMessage(f"Tema cambiato in {self.current_theme}", 2000)

    def _selected_index(self) -> int:
        indexes = self.table.selectionModel().selectedRows()
        return indexes[0].row() if indexes else -1

    def _stop_by_overlay(self) -> None:
        if self.recorder.is_recording:
            self.toggle_recording()

    def toggle_recording(self) -> None:
        if not self.recorder.is_recording:
            self.statusBar().showMessage("Registrazione in corso… Cliccare Stop per terminare (tasto destro per trascinare)")
            self.recordingStateChanged.emit(True)
            self.stopOverlay.show_bottom_right()
            self.hide()
            self.recorder.start()
        else:
            events = self.recorder.stop()
            self.stopOverlay.hide()
            self.recordingStateChanged.emit(False)
            self._restore_window()
            if events:
                rec_id, default_title = next_recording_title(self.macros)
                dlg = SaveRecordingDialog(default_title, self)
                if dlg.exec() == QtWidgets.QDialog.Accepted:
                    m = Macro(id=rec_id, title=dlg.title, events=events, with_pauses=dlg.with_pauses, repetitions=1)
                    self.macros.append(m)
                    save_macros(self.macros)
                    self.table_model._original_items = self.macros
                    self.table_model.refresh_sorting()
                    self.statusBar().showMessage(f"Salvata {m.title}")
            else:
                self.statusBar().showMessage("Nessun evento registrato")

    def _do_export(self) -> None:
        idx = self._selected_index()
        if idx < 0:
            return
        m = self.table_model.items[idx]
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Esporta macro", f"{m.title}.json", "JSON (*.json)")
        if not path:
            return
        import json
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(m.to_dict(), indent=2, ensure_ascii=False))

    def _do_import(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Importa macro", "", "JSON (*.json)")
        if not path:
            return
        import json
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        m = Macro.from_dict(d)
        self.macros.append(m)
        save_macros(self.macros)
        self.table_model._original_items = self.macros
        self.table_model.refresh_sorting()

    def execute_selected(self) -> None:
        idx = self._selected_index()
        if idx < 0:
            return
        m = self.table_model.items[idx]
        self.hide()
        self._play_macro_with_restore(m)

    def execute_last(self) -> None:
        if not self.macros:
            return
        m = self.macros[-1]
        self.hide()
        self._play_macro_with_restore(m)

    def _play_macro_with_restore(self, m: Macro) -> None:
        def run_and_notify():
            try:
                self.player.play(m.events, with_pauses=m.with_pauses, repetitions=m.repetitions, macro=m)
            except Exception as exc:
                logger.exception("Playback failed: {}", exc)
            finally:
                self.playbackFinished.emit()
        threading.Thread(target=run_and_notify, daemon=True).start()

    def _restore_window(self) -> None:
        self.setWindowState(self.windowState() & ~QtCore.Qt.WindowMinimized)
        self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    def _play_macro(self, m: Macro) -> None:
        def run():
            try:
                self.player.play(m.events, with_pauses=m.with_pauses, repetitions=m.repetitions, macro=m)
            except Exception as exc:
                logger.exception("Playback failed: {}", exc)
        threading.Thread(target=run, daemon=True).start()

    def toggle_with_pauses(self) -> None:
        idx = self._selected_index()
        if idx < 0:
            return
        m = self.table_model.items[idx]
        m.with_pauses = not m.with_pauses
        save_macros(self.macros)
        self.table_model.dataChanged.emit(self.table_model.index(idx, 1), self.table_model.index(idx, 1))

    def toggle_favorite(self) -> None:
        idx = self._selected_index()
        if idx < 0:
            return
        m = self.table_model.items[idx]
        m.favorite = not m.favorite
        save_macros(self.macros)
        # Refresh sorting to move favorites to top
        self.table_model.refresh_sorting()

    def delete_selected(self) -> None:
        idx = self._selected_index()
        if idx < 0:
            return
        macro_to_delete = self.table_model.items[idx]
        # Remove from original list
        self.macros.remove(macro_to_delete)
        save_macros(self.macros)
        self.table_model._original_items = self.macros
        self.table_model.refresh_sorting()

    def show_help(self) -> None:
        text = (
            "<h3>Guida rapida</h3>"
            "<ul>"
            "<li><b>Registra:</b> usa la toolbar; durante la registrazione clic sinistro Stop per fermare, tasto destro per trascinare</li>"
            "<li><b>Esegui:</b> la finestra si nasconde, esegue e si riapre alla fine</li>"
            "<li><b>Preferiti:</b> marca le macro come preferite per tenerle in cima alla lista</li>"
            "<li><b>Tema:</b> passa dal tema chiaro a quello scuro dal pulsante nella toolbar</li>"
            "</ul>"
        )
        QtWidgets.QMessageBox.information(self, "Aiuto", text)