"""
CORREZIONE PROBLEMA 3: Script potenziato per copia plugin Qt con gestione errori robusta
Risolve i problemi di fallimento PowerShell e migliora l'affidabilità del processo di build
"""

import os
import shutil
import sys
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Tuple


class PluginCopyError(Exception):
    """Eccezione personalizzata per errori nella copia dei plugin"""
    pass


def get_python_version() -> str:
    """Ottiene la versione Python corrente per path dinamici"""
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def find_all_pyside6_paths(venv_path: str) -> List[str]:
    """
    CORREZIONE: Ricerca più robusta dei percorsi PySide6 con versioni Python dinamiche
    
    Returns:
        Lista di tutti i possibili percorsi dove potrebbero essere i plugin
    """
    python_version = get_python_version()
    
    # Percorsi per Windows (più comuni)
    windows_paths = [
        os.path.join(venv_path, 'Lib', 'site-packages', 'PySide6', 'plugins'),
        os.path.join(venv_path, 'Lib', 'site-packages', 'PySide6', 'Qt', 'plugins'),
        os.path.join(venv_path, 'Scripts', 'Lib', 'site-packages', 'PySide6', 'plugins'),
    ]
    
    # Percorsi per Unix-like (per compatibilità)
    unix_paths = [
        os.path.join(venv_path, 'lib', f'python{python_version}', 'site-packages', 'PySide6', 'plugins'),
        os.path.join(venv_path, 'lib', f'python{python_version}', 'site-packages', 'PySide6', 'Qt', 'plugins'),
    ]
    
    # Percorsi globali di sistema (fallback)
    system_paths = []
    try:
        # Prova a trovare PySide6 nel sistema
        import PySide6
        pyside_path = os.path.dirname(PySide6.__file__)
        system_paths.extend([
            os.path.join(pyside_path, 'plugins'),
            os.path.join(pyside_path, 'Qt', 'plugins'),
        ])
    except ImportError:
        pass
    
    return windows_paths + unix_paths + system_paths


def verify_pyside6_installation(venv_path: str) -> Dict[str, str]:
    """
    CORREZIONE: Verifica installazione PySide6 con diagnostica avanzata
    
    Returns:
        Dizionario con informazioni su PySide6 o errore
    """
    python_exe = os.path.join(venv_path, 'Scripts', 'python.exe')
    if not os.path.exists(python_exe):
        # Fallback per Linux/macOS
        python_exe = os.path.join(venv_path, 'bin', 'python')
    
    if not os.path.exists(python_exe):
        return {"error": f"Eseguibile Python non trovato nell'ambiente virtuale: {venv_path}"}
    
    try:
        # Verifica PySide6 tramite subprocess per sicurezza
        result = subprocess.run(
            [python_exe, '-c', 'import PySide6; print(PySide6.__version__); print(PySide6.__file__)'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            return {
                "version": lines[0] if len(lines) > 0 else "sconosciuta",
                "path": lines[1] if len(lines) > 1 else "sconosciuto"
            }
        else:
            return {"error": f"PySide6 non installato o non importabile: {result.stderr}"}
            
    except subprocess.TimeoutExpired:
        return {"error": "Timeout durante verifica PySide6"}
    except Exception as e:
        return {"error": f"Errore durante verifica PySide6: {e}"}


def find_pyside6_plugins_path(venv_path: str) -> Optional[str]:
    """
    CORREZIONE: Ricerca più robusta e intelligente dei plugin PySide6
    
    Returns:
        Percorso dei plugin PySide6 o None se non trovato
    """
    print("🔍 Ricerca plugin PySide6...")
    
    # Prima verifica che PySide6 sia installato
    pyside_info = verify_pyside6_installation(venv_path)
    if "error" in pyside_info:
        print(f"❌ {pyside_info['error']}")
        return None
    
    print(f"✓ PySide6 {pyside_info['version']} trovato")
    
    # Ottieni tutti i possibili percorsi
    possible_paths = find_all_pyside6_paths(venv_path)
    
    # Aggiungi percorso basato su __file__ se disponibile
    if "path" in pyside_info and pyside_info["path"] != "sconosciuto":
        pyside_dir = os.path.dirname(pyside_info["path"])
        possible_paths.insert(0, os.path.join(pyside_dir, 'plugins'))
        possible_paths.insert(1, os.path.join(pyside_dir, 'Qt', 'plugins'))
    
    print(f"🔍 Controllo {len(possible_paths)} possibili percorsi...")
    
    # Cerca il primo percorso valido
    for i, path in enumerate(possible_paths, 1):
        print(f"  [{i}/{len(possible_paths)}] {path}")
        
        platforms_path = os.path.join(path, 'platforms')
        if os.path.isdir(platforms_path):
            # Verifica che contenga file DLL essenziali
            essential_files = ['qwindows.dll']
            missing_files = []
            
            for essential_file in essential_files:
                if not os.path.exists(os.path.join(platforms_path, essential_file)):
                    missing_files.append(essential_file)
            
            if not missing_files:
                print(f"✓ Plugin completi trovati in: {path}")
                return path
            else:
                print(f"⚠️  Plugin incompleti (mancano: {', '.join(missing_files)})")
    
    print("❌ Plugin PySide6 non trovati in nessun percorso")
    return None


def ensure_dist_structure(base_dir: str) -> Tuple[str, str]:
    """
    CORREZIONE: Gestisce sia struttura --onefile che --onedir di PyInstaller
    
    Returns:
        Tupla (percorso_eseguibile, percorso_directory_plugin)
    """
    dist_dir = os.path.join(base_dir, 'dist')
    
    if not os.path.exists(dist_dir):
        raise PluginCopyError(f"Directory dist non trovata: {dist_dir}")
    
    # Cerca AutoKey.exe (modalità onefile)
    exe_path = os.path.join(dist_dir, 'AutoKey.exe')
    
    # Cerca directory AutoKey (modalità onedir)  
    dir_path = os.path.join(dist_dir, 'AutoKey')
    
    if os.path.exists(exe_path) and os.path.exists(dir_path):
        # Entrambi esistono - probabile modalità onedir
        print("✓ Rilevata modalità PyInstaller: onedir")
        return exe_path, dir_path
    elif os.path.exists(exe_path):
        # Solo exe - modalità onefile (i plugin vanno nella stessa directory)
        print("✓ Rilevata modalità PyInstaller: onefile")
        return exe_path, dist_dir
    elif os.path.exists(dir_path):
        # Solo directory - modalità onedir senza exe nella root
        print("✓ Rilevata modalità PyInstaller: onedir (directory only)")
        exe_in_dir = os.path.join(dir_path, 'AutoKey.exe')
        return exe_in_dir, dir_path
    else:
        raise PluginCopyError(
            f"Nessuna build PyInstaller trovata in {dist_dir}. "
            f"Eseguire prima: pyinstaller ... app\\main.py"
        )


def copy_plugin_directory(src_dir: str, dst_dir: str, plugin_name: str) -> int:
    """
    Copia una directory di plugin con gestione errori robusta
    
    Returns:
        Numero di file copiati
    """
    if not os.path.isdir(src_dir):
        print(f"⚠️  Directory sorgente non trovata: {plugin_name}")
        return 0
    
    try:
        # Rimuovi directory destinazione se esiste
        if os.path.exists(dst_dir):
            shutil.rmtree(dst_dir)
        
        # Copia directory completa
        shutil.copytree(src_dir, dst_dir)
        
        # Conta file copiati
        file_count = sum(1 for root, _, files in os.walk(dst_dir) for _ in files)
        
        print(f"✓ Plugin {plugin_name}: {file_count} file copiati")
        return file_count
        
    except Exception as e:
        print(f"❌ Errore copia plugin {plugin_name}: {e}")
        return 0


def copy_qt_plugins(base_dir: str) -> bool:
    """
    CORREZIONE PROBLEMA 3: Funzione principale di copia plugin potenziata
    
    Args:
        base_dir: Directory base del progetto
        
    Returns:
        True se successo, False se errore
    """
    print("=" * 60)
    print("🚀 AUTOKEY - COPIA PLUGIN QT POTENZIATA")
    print("=" * 60)
    print(f"📁 Directory progetto: {base_dir}")
    
    try:
        # FASE 1: Verifica ambiente virtuale
        venv_path = os.path.join(base_dir, '.venv')
        if not os.path.isdir(venv_path):
            print(f"❌ Ambiente virtuale non trovato: {venv_path}")
            print("💡 Suggerimenti:")
            print("   1. Assicurarsi di essere nella directory corretta del progetto")
            print("   2. Creare l'ambiente virtuale: python -m venv .venv")
            print("   3. Attivare l'ambiente: .venv\\Scripts\\activate")
            return False
        
        print(f"✓ Ambiente virtuale trovato: {venv_path}")
        
        # FASE 2: Trova plugin PySide6
        plugins_base_path = find_pyside6_plugins_path(venv_path)
        if not plugins_base_path:
            print("❌ Plugin PySide6 non trovati!")
            print("💡 Suggerimenti:")
            print("   1. Reinstallare PySide6: pip uninstall PySide6 && pip install PySide6")
            print("   2. Verificare l'ambiente virtuale attivo")
            print("   3. Controllare versione Python compatibile (3.8+)")
            return False
        
        # FASE 3: Verifica struttura PyInstaller
        try:
            exe_path, plugin_base_dir = ensure_dist_structure(base_dir)
            print(f"✓ Eseguibile: {exe_path}")
            print(f"✓ Directory plugin: {plugin_base_dir}")
        except PluginCopyError as e:
            print(f"❌ {e}")
            return False
        
        # FASE 4: Copia plugin essenziali
        print("\n📦 Copia plugin essenziali...")
        
        essential_plugins = {
            'platforms': 'Plugin piattaforma (essenziale)',
            'imageformats': 'Formati immagine', 
            'iconengines': 'Motori icone',
            'styles': 'Stili interfaccia'
        }
        
        total_files = 0
        success_count = 0
        
        for plugin_name, description in essential_plugins.items():
            src_plugin_dir = os.path.join(plugins_base_path, plugin_name)
            dst_plugin_dir = os.path.join(plugin_base_dir, plugin_name)
            
            print(f"\n🔄 Copia {plugin_name} ({description})...")
            files_copied = copy_plugin_directory(src_plugin_dir, dst_plugin_dir, plugin_name)
            
            if files_copied > 0:
                success_count += 1
                total_files += files_copied
            elif plugin_name == 'platforms':
                # Platforms è essenziale - errore se non trovato
                print("❌ ERRORE CRITICO: Plugin platforms non copiato!")
                return False
        
        # FASE 5: Verifica file essenziali
        print(f"\n🔍 Verifica file essenziali...")
        platforms_dir = os.path.join(plugin_base_dir, 'platforms')
        essential_files = ['qwindows.dll', 'qminimal.dll']
        missing_essential = []
        
        for essential_file in essential_files:
            file_path = os.path.join(platforms_dir, essential_file)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"✓ {essential_file} ({file_size:,} bytes)")
            else:
                missing_essential.append(essential_file)
                print(f"❌ {essential_file} - MANCANTE!")
        
        if missing_essential:
            print(f"\n⚠️  ATTENZIONE: File essenziali mancanti: {', '.join(missing_essential)}")
            print("   L'eseguibile potrebbe non avviarsi correttamente.")
            return False
        
        # FASE 6: Crea file di verifica
        try:
            verification_file = os.path.join(plugin_base_dir, 'qt_plugins_info.txt')
            with open(verification_file, 'w', encoding='utf-8') as f:
                f.write("AutoKey - Plugin Qt Information\n")
                f.write("=" * 40 + "\n")
                f.write(f"Data copia: {__import__('datetime').datetime.now()}\n")
                f.write(f"Sorgente: {plugins_base_path}\n")
                f.write(f"Plugin copiati: {success_count}/{len(essential_plugins)}\n")
                f.write(f"File totali: {total_files}\n")
                f.write("\nPlugin presenti:\n")
                for plugin_name in essential_plugins:
                    plugin_dir = os.path.join(plugin_base_dir, plugin_name)
                    if os.path.exists(plugin_dir):
                        file_count = sum(1 for root, _, files in os.walk(plugin_dir) for _ in files)
                        f.write(f"  - {plugin_name}: {file_count} file\n")
                    else:
                        f.write(f"  - {plugin_name}: NON PRESENTE\n")
            
            print(f"✓ File verifica creato: qt_plugins_info.txt")
        except Exception as e:
            print(f"⚠️  Impossibile creare file verifica: {e}")
        
        # FASE 7: Test rapido
        print(f"\n🧪 Test rapido eseguibile...")
        if os.path.exists(exe_path):
            try:
                # Test molto rapido per vedere se l'exe si avvia
                result = subprocess.run(
                    [exe_path, '--version'], 
                    capture_output=True, 
                    timeout=5,
                    text=True
                )
                
                if result.returncode == 0:
                    print("✓ Test eseguibile superato")
                else:
                    print(f"⚠️  Test eseguibile fallito (codice: {result.returncode})")
                    
            except subprocess.TimeoutExpired:
                print("⚠️  Test eseguibile timeout (normale per GUI)")
            except Exception as e:
                print(f"⚠️  Impossibile testare eseguibile: {e}")
        
        # FASE 8: Riepilogo finale
        print("\n" + "=" * 60)
        print("🎉 COPIA PLUGIN COMPLETATA CON SUCCESSO!")
        print("=" * 60)
        print(f"📊 Statistiche:")
        print(f"   • Plugin copiati: {success_count}/{len(essential_plugins)}")
        print(f"   • File totali: {total_files:,}")
        print(f"   • File essenziali: ✓ Tutti presenti")
        print(f"\n📁 Percorsi:")
        print(f"   • Sorgente: {plugins_base_path}")
        print(f"   • Destinazione: {plugin_base_dir}")
        print(f"   • Eseguibile: {exe_path}")
        print(f"\n💡 L'eseguibile AutoKey.exe dovrebbe ora funzionare correttamente!")
        
        return True
        
    except Exception as e:
        print(f"\n💥 ERRORE INASPETTATO: {e}")
        print(f"\n🔧 Informazioni debug:")
        print(f"   • Python: {sys.version}")
        print(f"   • Directory lavoro: {os.getcwd()}")
        print(f"   • Directory progetto: {base_dir}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Funzione principale con gestione errori completa
    """
    print("🚀 Avvio script copia plugin Qt...")
    
    try:
        # Ottieni directory base del progetto
        base_dir = os.path.abspath(os.path.dirname(__file__))
        print(f"📁 Directory script: {base_dir}")
        
        # Verifica prerequisiti di base
        if not os.path.exists(os.path.join(base_dir, 'app')):
            print("❌ Directory 'app' non trovata!")
            print("   Assicurarsi di eseguire lo script dalla root del progetto AutoKey")
            return 1
        
        # Esegui copia plugin
        success = copy_qt_plugins(base_dir)
        
        if success:
            print("\n🎉 Script completato con SUCCESSO!")
            print("\n🔧 Prossimi passi:")
            print("   1. Testare l'eseguibile: .\\dist\\AutoKey.exe")
            print("   2. Se funziona, copiare nella cartella release")
            print("   3. Distribuire insieme ai plugin copiati")
            return 0
        else:
            print("\n💥 Script terminato con ERRORI!")
            print("\n🔧 Risoluzione problemi:")
            print("   1. Verificare ambiente virtuale attivo: .venv\\Scripts\\activate")
            print("   2. Reinstallare PySide6: pip install --force-reinstall PySide6")
            print("   3. Ricompilare con PyInstaller: seguire COMANDI_CREAZIONE_ESEGUIBILE.md")
            print("   4. Verificare permessi directory dist/")
            return 2
            
    except KeyboardInterrupt:
        print("\n⏹️  Script interrotto dall'utente")
        return 3
    except Exception as e:
        print(f"\n💥 Errore critico inaspettato: {e}")
        import traceback
        traceback.print_exc()
        return 4


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)