"""
Script per copiare i plugin Qt necessari per il funzionamento dell'eseguibile AutoKey
CORREZIONE PROBLEMA 4: Risolve gli errori PowerShell e migliora la robustezza dello script
"""

import os
import shutil
import sys
from pathlib import Path


def find_pyside6_plugins_path(venv_path: str) -> str:
    """
    Trova il percorso corretto dei plugin PySide6 nell'ambiente virtuale
    
    Args:
        venv_path: Percorso dell'ambiente virtuale
        
    Returns:
        Percorso dei plugin PySide6 o None se non trovato
    """
    
    # Possibili percorsi relativi per i plugin PySide6
    possible_paths = [
        os.path.join(venv_path, 'Lib', 'site-packages', 'PySide6', 'plugins'),
        os.path.join(venv_path, 'Lib', 'site-packages', 'PySide6', 'Qt', 'plugins'),
        os.path.join(venv_path, 'lib', 'python3.10', 'site-packages', 'PySide6', 'plugins'),
        os.path.join(venv_path, 'lib', 'python3.11', 'site-packages', 'PySide6', 'plugins'),
        os.path.join(venv_path, 'lib', 'python3.12', 'site-packages', 'PySide6', 'plugins'),
    ]
    
    for path in possible_paths:
        platforms_path = os.path.join(path, 'platforms')
        if os.path.isdir(platforms_path):
            print(f"✓ Plugin PySide6 trovati in: {path}")
            return path
    
    return None


def copy_qt_plugins(base_dir: str) -> bool:
    """
    Copia i plugin Qt necessari nella directory di distribuzione
    
    Args:
        base_dir: Directory base del progetto
        
    Returns:
        True se la copia è avvenuta con successo, False altrimenti
    """
    
    print("=== AUTOKEY - COPIA PLUGIN QT ===")
    print(f"Directory base progetto: {base_dir}")
    
    # Trova la directory dell'ambiente virtuale
    venv_path = os.path.join(base_dir, '.venv')
    if not os.path.isdir(venv_path):
        print("❌ ERRORE: Directory ambiente virtuale non trovata!")
        print(f"   Cercato in: {venv_path}")
        print("   Assicurarsi che l'ambiente virtuale sia attivato nella directory corretta.")
        return False
    
    print(f"✓ Ambiente virtuale trovato: {venv_path}")
    
    # Trova i plugin PySide6
    plugins_base_path = find_pyside6_plugins_path(venv_path)
    if not plugins_base_path:
        print("❌ ERRORE: Plugin PySide6 non trovati!")
        print("   Possibili cause:")
        print("   1. PySide6 non è installato nell'ambiente virtuale")
        print("   2. Versione di PySide6 non compatibile")
        print("   Eseguire: pip install PySide6")
        return False
    
    # Percorso sorgente delle piattaforme
    src_platforms = os.path.join(plugins_base_path, 'platforms')
    if not os.path.isdir(src_platforms):
        print(f"❌ ERRORE: Directory platforms non trovata in {plugins_base_path}")
        return False
    
    print(f"✓ Directory platforms trovata: {src_platforms}")
    
    # Verifica che la directory dist/AutoKey esista
    dist_autokey = os.path.join(base_dir, 'dist', 'AutoKey')
    if not os.path.exists(dist_autokey):
        print(f"❌ ERRORE: Directory di distribuzione non trovata!")
        print(f"   Cercato in: {dist_autokey}")
        print("   Assicurarsi di eseguire PyInstaller prima di questo script.")
        return False
    
    print(f"✓ Directory di distribuzione trovata: {dist_autokey}")
    
    # Directory di destinazione per i plugin
    dst_platforms = os.path.join(dist_autokey, 'platforms')
    
    try:
        # Crea la directory di destinazione se non esiste
        os.makedirs(dst_platforms, exist_ok=True)
        print(f"✓ Directory destinazione creata: {dst_platforms}")
        
        # Copia tutti i file dalla directory platforms
        copied_files = []
        for file_name in os.listdir(src_platforms):
            src_file = os.path.join(src_platforms, file_name)
            dst_file = os.path.join(dst_platforms, file_name)
            
            # Copia solo i file, non le sottodirectory
            if os.path.isfile(src_file):
                shutil.copy2(src_file, dst_file)
                copied_files.append(file_name)
                print(f"  → {file_name}")
        
        print(f"\n✓ SUCCESSO: {len(copied_files)} file copiati con successo!")
        
        # Verifica che i file essenziali siano presenti
        essential_files = ['qwindows.dll']  # File essenziale per Windows
        missing_files = []
        
        for essential_file in essential_files:
            if essential_file not in copied_files:
                missing_files.append(essential_file)
        
        if missing_files:
            print(f"⚠️  ATTENZIONE: File essenziali mancanti: {', '.join(missing_files)}")
            print("   L'eseguibile potrebbe non funzionare correttamente.")
            return False
        
        print("✓ Tutti i file essenziali sono stati copiati correttamente.")
        
        # Copia anche altri plugin utili se disponibili
        other_plugins = ['imageformats', 'iconengines', 'styles']
        for plugin_dir in other_plugins:
            src_plugin = os.path.join(plugins_base_path, plugin_dir)
            if os.path.isdir(src_plugin):
                dst_plugin = os.path.join(dist_autokey, plugin_dir)
                try:
                    if os.path.exists(dst_plugin):
                        shutil.rmtree(dst_plugin)
                    shutil.copytree(src_plugin, dst_plugin)
                    plugin_files = len([f for f in os.listdir(dst_plugin) if os.path.isfile(os.path.join(dst_plugin, f))])
                    print(f"✓ Plugin aggiuntivo copiato: {plugin_dir} ({plugin_files} file)")
                except Exception as e:
                    print(f"⚠️  Impossibile copiare plugin {plugin_dir}: {e}")
        
        print("\n=== RIEPILOGO COPIA PLUGIN ===")
        print(f"Sorgente: {src_platforms}")
        print(f"Destinazione: {dst_platforms}")
        print(f"File copiati: {len(copied_files)}")
        print("Plugin essenziali: ✓ Presenti")
        print("\n✅ Copia plugin completata con successo!")
        print("   L'eseguibile AutoKey.exe dovrebbe ora funzionare correttamente.")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRORE durante la copia dei plugin: {e}")
        return False


def main():
    """Funzione principale dello script"""
    try:
        # Ottieni la directory base del progetto
        base_dir = os.path.abspath(os.path.dirname(__file__))
        
        # Esegui la copia dei plugin
        success = copy_qt_plugins(base_dir)
        
        if success:
            print("\n🎉 Script completato con successo!")
            sys.exit(0)
        else:
            print("\n💥 Script terminato con errori!")
            print("\nSuggerimenti per la risoluzione:")
            print("1. Verificare che l'ambiente virtuale sia attivo")
            print("2. Verificare che PySide6 sia installato: pip list | findstr PySide6")
            print("3. Verificare che PyInstaller sia stato eseguito correttamente")
            print("4. Controllare i permessi di scrittura nella directory dist/")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  Script interrotto dall'utente.")
        sys.exit(2)
    except Exception as e:
        print(f"\n💥 Errore inaspettato: {e}")
        sys.exit(3)


if __name__ == "__main__":
    main()