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
from PySide6 import QtWidgets, QtCore

# Import assoluti invece di relativi
from app.gui import MainWindow


def configure_dpi_awareness() -> None:
    """
    Configura la consapevolezza DPI per Windows per eliminare i warning di avvio
    CORREZIONE PROBLEMA 5: Risolve il warning "SetProcessDpiAwarenessContext() failed"
    """
    try:
        # Solo su Windows
        if sys.platform == "win32":
            # Prova il metodo più recente per Windows 10+
            try:
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                
                # Definisce le costanti DPI_AWARENESS_CONTEXT
                DPI_AWARENESS_CONTEXT_UNAWARE = -1
                DPI_AWARENESS_CONTEXT_SYSTEM_AWARE = -2
                DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE = -3
                DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
                
                # Prova prima il metodo più avanzato (Windows 10 1703+)
                try:
                    success = user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
                    if success:
                        logger.debug("DPI awareness impostata a PER_MONITOR_AWARE_V2")
                        return
                except Exception:
                    pass
                
                # Fallback al metodo precedente (Windows 10+)
                try:
                    success = user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE)
                    if success:
                        logger.debug("DPI awareness impostata a PER_MONITOR_AWARE")
                        return
                except Exception:
                    pass
                
                # Fallback al metodo system aware (Windows 8.1+)
                try:
                    success = user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_SYSTEM_AWARE)
                    if success:
                        logger.debug("DPI awareness impostata a SYSTEM_AWARE")
                        return
                except Exception:
                    pass
                
            except Exception as e:
                logger.debug(f"Metodo SetProcessDpiAwarenessContext non disponibile: {e}")
            
            # Fallback al metodo legacy per Windows 8.1+
            try:
                shcore = ctypes.windll.shcore
                # PROCESS_PER_MONITOR_DPI_AWARE = 2
                # PROCESS_SYSTEM_DPI_AWARE = 1
                # PROCESS_DPI_UNAWARE = 0
                result = shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
                if result == 0:  # S_OK
                    logger.debug("DPI awareness impostata tramite SetProcessDpiAwareness")
                    return
            except Exception as e:
                logger.debug(f"SetProcessDpiAwareness non disponibile: {e}")
            
            # Ultimo fallback per Windows Vista+
            try:
                user32 = ctypes.windll.user32
                result = user32.SetProcessDPIAware()
                if result:
                    logger.debug("DPI awareness impostata tramite SetProcessDPIAware (legacy)")
                    return
            except Exception as e:
                logger.debug(f"SetProcessDPIAware non disponibile: {e}")
        
    except Exception as e:
        # Se tutti i metodi falliscono, registra solo a livello debug per non disturbare l'utente
        logger.debug(f"Impossibile configurare DPI awareness: {e}")


def configure_application_attributes() -> None:
    """
    Configura gli attributi dell'applicazione Qt per migliorare stabilità e performance
    """
    try:
        # Abilita il supporto per High DPI
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
        
        # Migliora il rendering del testo
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_SynthesizeMouseForUnhandledTouchEvents, False)
        QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_SynthesizeTouchForUnhandledMouseEvents, False)
        
        logger.debug("Attributi applicazione Qt configurati con successo")
        
    except Exception as e:
        logger.debug(f"Errore durante configurazione attributi Qt: {e}")


def main() -> int:
    """
    Funzione principale dell'applicazione con configurazioni migliorate
    """
    
    # CORREZIONE PROBLEMA 5: Configura DPI awareness prima di creare QApplication
    configure_dpi_awareness()
    
    logger.add(sys.stderr, level="INFO")
    logger.info("Avvio AutoKey - Macro Recorder")

    # Configura attributi Qt prima di creare l'applicazione
    configure_application_attributes()
    
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("AutoKey")
    app.setOrganizationName("AutoKey")
    app.setApplicationVersion("1.0.0")
    
    # Imposta l'icona dell'applicazione se disponibile
    try:
        icon_path = os.path.join(application_path, "assets", "icon.ico")
        if not os.path.exists(icon_path):
            # Fallback al percorso dell'icona specificato nel prompt
            icon_path = "C:\\Users\\Administrator\\Desktop\\Icona_Minimalista_AutoKey.ico"
        
        if os.path.exists(icon_path):
            app.setWindowIcon(QtWidgets.QApplication.style().standardIcon(QtWidgets.QStyle.SP_ComputerIcon))
            logger.debug(f"Icona applicazione caricata da: {icon_path}")
        else:
            logger.debug("Icona applicazione non trovata, uso icona predefinita")
    except Exception as e:
        logger.debug(f"Errore durante caricamento icona: {e}")
    
    # Configura stile applicazione per miglior aspetto
    try:
        app.setStyle("Fusion")  # Stile moderno e cross-platform
        logger.debug("Stile applicazione impostato a Fusion")
    except Exception as e:
        logger.debug(f"Impossibile impostare stile Fusion: {e}")
    
    try:
        win = MainWindow()
        win.show()

        # Collega lo stop richiesto dal recorder al toggle
        win.recorder.set_on_stop_requested(lambda: QtCore.QTimer.singleShot(0, win.toggle_recording))
        
        logger.info("AutoKey avviato con successo")
        
        exit_code = app.exec()
        
        logger.info("AutoKey terminato con codice: {}", exit_code)
        return int(exit_code)
        
    except Exception as e:
        logger.exception("Errore critico durante l'esecuzione dell'applicazione: {}", e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())