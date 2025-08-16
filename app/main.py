from __future__ import annotations

import sys
import os
import ctypes

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
from PySide6 import QtWidgets, QtCore, QtGui

# Import assoluti invece di relativi
from app.gui import MainWindow


def configure_dpi_awareness() -> None:
    """
    CORREZIONE PROBLEMA 3: Configurazione DPI awareness robusta per eliminare errori
    Risolve il problema "SetProcessDpiAwarenessContext() failed: Accesso negato"
    """
    try:
        # Solo su Windows
        if sys.platform == "win32":
            # Metodo 1: Prova SetProcessDpiAwarenessContext (Windows 10 1703+)
            try:
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                
                # Costanti DPI_AWARENESS_CONTEXT
                DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
                DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE = -3
                DPI_AWARENESS_CONTEXT_SYSTEM_AWARE = -2
                
                # Prova il metodo più avanzato per primo
                success = user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
                if success:
                    logger.debug("DPI awareness impostata: PER_MONITOR_AWARE_V2")
                    return
                
                # Fallback al metodo precedente
                success = user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE)
                if success:
                    logger.debug("DPI awareness impostata: PER_MONITOR_AWARE")
                    return
                
                # Ulteriore fallback
                success = user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_SYSTEM_AWARE)
                if success:
                    logger.debug("DPI awareness impostata: SYSTEM_AWARE")
                    return
                
            except Exception as e:
                logger.debug(f"SetProcessDpiAwarenessContext non disponibile: {e}")
            
            # Metodo 2: SetProcessDpiAwareness (Windows 8.1+)
            try:
                shcore = ctypes.windll.shcore
                # PROCESS_PER_MONITOR_DPI_AWARE = 2
                result = shcore.SetProcessDpiAwareness(2)
                if result == 0:  # S_OK
                    logger.debug("DPI awareness impostata: SetProcessDpiAwareness")
                    return
            except Exception as e:
                logger.debug(f"SetProcessDpiAwareness non disponibile: {e}")
            
            # Metodo 3: SetProcessDPIAware (Windows Vista+) - legacy
            try:
                user32 = ctypes.windll.user32
                result = user32.SetProcessDPIAware()
                if result:
                    logger.debug("DPI awareness impostata: SetProcessDPIAware (legacy)")
                    return
            except Exception as e:
                logger.debug(f"SetProcessDPIAware non disponibile: {e}")
        
        # Se tutti i metodi falliscono, non è critico
        logger.debug("DPI awareness non configurata - continuo senza")
        
    except Exception as e:
        logger.debug(f"Errore configurazione DPI awareness: {e}")


def configure_application_attributes() -> None:
    """
    CORREZIONE PROBLEMA 3: Configurazione attributi Qt migliorata per eliminare warning
    Risolve i DeprecationWarning per attributi Qt deprecati
    """
    try:
        # CORREZIONE: Verifica disponibilità attributi prima dell'uso
        
        # Attributi per High DPI (verifica deprecation)
        if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
            try:
                QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
            except Exception:
                logger.debug("AA_EnableHighDpiScaling deprecato o non supportato")
        
        if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
            try:
                QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
            except Exception:
                logger.debug("AA_UseHighDpiPixmaps deprecato o non supportato")
        
        # Attributi per stabilità e performance (sempre supportati)
        if hasattr(QtCore.Qt, 'AA_SynthesizeMouseForUnhandledTouchEvents'):
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_SynthesizeMouseForUnhandledTouchEvents, False)
        
        if hasattr(QtCore.Qt, 'AA_SynthesizeTouchForUnhandledMouseEvents'):
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_SynthesizeTouchForUnhandledMouseEvents, False)
        
        # Nuovo attributo per DPI (sostituisce i deprecati)
        if hasattr(QtCore.Qt, 'AA_Use96Dpi'):
            QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_Use96Dpi, False)
        
        logger.debug("Attributi applicazione Qt configurati")
        
    except Exception as e:
        logger.debug(f"Errore configurazione attributi Qt: {e}")


def setup_application_properties(app: QtWidgets.QApplication) -> None:
    """
    CORREZIONE PROBLEMA 3: Configurazione proprietà applicazione migliorata
    """
    try:
        # Proprietà base applicazione
        app.setApplicationName("AutoKey")
        app.setOrganizationName("AutoKey")
        app.setApplicationDisplayName("AutoKey - Macro Recorder")
        app.setApplicationVersion("1.0.1")
        
        # CORREZIONE: Configurazione icona con fallback robusti
        icon_paths = [
            # Percorso specificato nel prompt
            "C:\\Users\\Administrator\\Desktop\\Icona_Minimalista_AutoKey.ico",
            # Percorso relativo assets
            os.path.join(application_path, "assets", "icon.ico"),
            os.path.join(application_path, "assets", "autokey.ico"),
            # Percorso nella directory corrente
            os.path.join(os.getcwd(), "Icona_Minimalista_AutoKey.ico")
        ]
        
        icon_set = False
        for icon_path in icon_paths:
            if os.path.exists(icon_path):
                try:
                    icon = QtGui.QIcon(icon_path)
                    if not icon.isNull():
                        app.setWindowIcon(icon)
                        icon_set = True
                        logger.debug(f"Icona caricata da: {icon_path}")
                        break
                except Exception as e:
                    logger.debug(f"Errore caricamento icona da {icon_path}: {e}")
        
        if not icon_set:
            # Usa icona predefinita del sistema
            style = app.style()
            if style:
                icon = style.standardIcon(QtWidgets.QStyle.SP_ComputerIcon)
                app.setWindowIcon(icon)
                logger.debug("Icona predefinita sistema utilizzata")
        
        # CORREZIONE: Stile applicazione con fallback
        styles_to_try = ["Fusion", "Windows", "WindowsVista"]
        style_set = False
        
        for style_name in styles_to_try:
            try:
                app.setStyle(style_name)
                style_set = True
                logger.debug(f"Stile applicazione impostato: {style_name}")
                break
            except Exception:
                continue
        
        if not style_set:
            logger.debug("Stile predefinito mantenuto")
        
    except Exception as e:
        logger.debug(f"Errore configurazione proprietà applicazione: {e}")


def configure_qt_logging() -> None:
    """
    CORREZIONE PROBLEMA 3: Configura logging Qt per ridurre warning
    """
    try:
        # Imposta variabili ambiente per Qt logging
        os.environ.setdefault("QT_LOGGING_RULES", 
                             "qt.qpa.window.debug=false;"
                             "qt.qpa.window.warning=false;"
                             "*.debug=false")
        
        # Imposta configurazione DPI tramite qt.conf se possibile
        qt_conf_content = """[Platforms]
WindowsArguments = dpiawareness=1
"""
        
        try:
            qt_conf_path = os.path.join(application_path, "qt.conf")
            if not os.path.exists(qt_conf_path):
                with open(qt_conf_path, 'w', encoding='utf-8') as f:
                    f.write(qt_conf_content)
                logger.debug("File qt.conf creato per configurazione DPI")
        except Exception:
            pass  # Non critico se fallisce
        
    except Exception as e:
        logger.debug(f"Errore configurazione Qt logging: {e}")


def main() -> int:
    """
    CORREZIONE PROBLEMA 3: Funzione main migliorata per risolvere errori PyInstaller
    """
    try:
        # FASE 1: Configurazione DPI prima di tutto
        configure_dpi_awareness()
        
        # FASE 2: Configurazione Qt logging
        configure_qt_logging()
        
        # FASE 3: Configurazione attributi Qt
        configure_application_attributes()
        
        # FASE 4: Setup logging
        logger.add(sys.stderr, level="INFO")
        logger.info("Avvio AutoKey - Macro Recorder v1.0.1")
        
        # FASE 5: Creazione applicazione Qt
        app = QtWidgets.QApplication(sys.argv)
        
        # FASE 6: Configurazione proprietà applicazione
        setup_application_properties(app)
        
        # FASE 7: Creazione e setup finestra principale
        try:
            win = MainWindow()
            win.show()

            # Collega il callback di stop del recorder
            if hasattr(win, 'recorder') and win.recorder:
                win.recorder.set_on_stop_requested(
                    lambda: QtCore.QTimer.singleShot(0, win.toggle_recording)
                )
            
            logger.info("AutoKey avviato con successo")
            
            # FASE 8: Avvio loop eventi
            exit_code = app.exec()
            
            logger.info("AutoKey terminato con codice: {}", exit_code)
            return int(exit_code)
            
        except Exception as e:
            logger.exception("Errore durante creazione finestra principale: {}", e)
            return 2
        
    except Exception as e:
        logger.exception("Errore critico durante avvio applicazione: {}", e)
        
        # Tentativo di mostrare errore all'utente se possibile
        try:
            error_app = QtWidgets.QApplication(sys.argv)
            QtWidgets.QMessageBox.critical(
                None, 
                "Errore AutoKey", 
                f"Errore critico durante l'avvio:\n{str(e)}\n\nControllare i log per maggiori dettagli."
            )
        except Exception:
            # Se anche questo fallisce, stampa su console
            print(f"ERRORE CRITICO: {e}")
        
        return 1


if __name__ == "__main__":
    # CORREZIONE PROBLEMA 3: Gestione exit code robusta
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("Applicazione interrotta dall'utente")
        sys.exit(130)  # Standard Unix exit code per SIGINT
    except SystemExit:
        raise  # Lascia passare SystemExit normale
    except Exception as e:
        logger.exception("Errore inaspettato: {}", e)
        sys.exit(1)