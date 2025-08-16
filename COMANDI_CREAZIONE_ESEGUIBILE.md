# IMPORTANTE: Eseguire tutti i comandi in PowerShell come Amministratore
# dalla directory C:\Users\Administrator\Desktop\macro_recorder

Write-Host "=== AUTOKEY - PROCEDURA DI BUILD POTENZIATA ===" -ForegroundColor Cyan
Write-Host "Correzioni implementate per tutti i problemi identificati" -ForegroundColor Green

# STEP 1: VERIFICA PREREQUISITI AVANZATA
Write-Host "`n--- STEP 1: Verifica prerequisiti avanzata ---" -ForegroundColor Yellow

# Verifica Python con controllo versione dettagliato
Write-Host "Verifica versione Python..." -ForegroundColor Gray
$pythonVersion = python --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERRORE: Python non trovato nel PATH!" -ForegroundColor Red
    Write-Host "   Installare Python 3.8+ 64-bit da python.org" -ForegroundColor Red
    Write-Host "   Assicurarsi di selezionare 'Add to PATH' durante l'installazione" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Python trovato: $pythonVersion" -ForegroundColor Green

# Verifica architettura Python (deve essere 64-bit)
$pythonArch = python -c "import platform; print(platform.architecture()[0])" 2>$null
if ($pythonArch -ne "64bit") {
    Write-Host "⚠️  ATTENZIONE: Python $pythonArch rilevato. Raccomandato 64-bit per PyInstaller" -ForegroundColor Orange
}

# Verifica directory corrente
$currentDir = Get-Location
Write-Host "Directory corrente: $currentDir" -ForegroundColor Gray

# Verifica struttura progetto
$requiredFiles = @("app\main.py", "requirements.txt", "copy_plugins.py")
$missingFiles = @()

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "❌ ERRORE: File di progetto mancanti!" -ForegroundColor Red
    Write-Host "   File mancanti: $($missingFiles -join ', ')" -ForegroundColor Red
    Write-Host "   Spostarsi nella directory root del progetto AutoKey" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Struttura progetto verificata" -ForegroundColor Green

# STEP 2: CONFIGURAZIONE AMBIENTE VIRTUALE MIGLIORATA
Write-Host "`n--- STEP 2: Configurazione ambiente virtuale migliorata ---" -ForegroundColor Yellow

# Backup dell'ambiente virtuale esistente se presente
if (Test-Path ".venv") {
    Write-Host "Backup ambiente virtuale esistente..." -ForegroundColor Gray
    if (Test-Path ".venv_backup") {
        Remove-Item -Recurse -Force ".venv_backup" -ErrorAction SilentlyContinue
    }
    Rename-Item ".venv" ".venv_backup" -ErrorAction SilentlyContinue
    Write-Host "✓ Backup creato: .venv_backup" -ForegroundColor Green
}

# Crea nuovo ambiente virtuale
Write-Host "Creazione ambiente virtuale..." -ForegroundColor Gray
python -m venv .venv --clear
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERRORE: Creazione ambiente virtuale fallita!" -ForegroundColor Red
    Write-Host "   Possibili cause:" -ForegroundColor Yellow
    Write-Host "   1. Python non installato correttamente" -ForegroundColor Gray
    Write-Host "   2. Permessi insufficienti" -ForegroundColor Gray
    Write-Host "   3. Spazio disco insufficiente" -ForegroundColor Gray
    exit 1
}

# Configura policy di esecuzione con verifica
Write-Host "Configurazione policy di esecuzione..." -ForegroundColor Gray
try {
    $currentPolicy = Get-ExecutionPolicy -Scope CurrentUser
    Write-Host "Policy corrente: $currentPolicy" -ForegroundColor Gray
    
    if ($currentPolicy -eq "Restricted") {
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
        Write-Host "✓ Policy aggiornata a RemoteSigned" -ForegroundColor Green
    } else {
        Write-Host "✓ Policy adeguata: $currentPolicy" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Impossibile modificare policy: $($_.Exception.Message)" -ForegroundColor Orange
    Write-Host "   Continuare comunque..." -ForegroundColor Orange
}

# Attiva ambiente virtuale con verifica
Write-Host "Attivazione ambiente virtuale..." -ForegroundColor Gray
& ".\.venv\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERRORE: Attivazione ambiente virtuale fallita!" -ForegroundColor Red
    Write-Host "   Provare manualmente:" -ForegroundColor Yellow
    Write-Host "   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Gray
    Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
    exit 1
}

# Verifica attivazione ambiente virtuale
$virtualEnvPath = $env:VIRTUAL_ENV
if ($virtualEnvPath) {
    Write-Host "✓ Ambiente virtuale attivato: $virtualEnvPath" -ForegroundColor Green
} else {
    Write-Host "⚠️  Ambiente virtuale potrebbe non essere attivato correttamente" -ForegroundColor Orange
}

# STEP 3: INSTALLAZIONE DIPENDENZE OTTIMIZZATA
Write-Host "`n--- STEP 3: Installazione dipendenze ottimizzata ---" -ForegroundColor Yellow

# Aggiorna pip alla versione più recente
Write-Host "Aggiornamento pip..." -ForegroundColor Gray
python -m pip install --upgrade pip wheel setuptools
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Aggiornamento pip parzialmente fallito, continuando..." -ForegroundColor Orange
} else {
    Write-Host "✓ Pip aggiornato con successo" -ForegroundColor Green
}

# Mostra versione pip aggiornata
$pipVersion = python -m pip --version
Write-Host "Versione pip: $pipVersion" -ForegroundColor Gray

# CORREZIONE PROBLEMA 3: Installazione dipendenze con versioni specifiche testate
Write-Host "Installazione dipendenze con versioni testate..." -ForegroundColor Gray

# Installa dipendenze critiche singolarmente per debug migliore
$criticalPackages = @(
    "PySide6>=6.8.0,<6.10.0",
    "keyboard==0.13.5",
    "mouse==0.7.1",
    "loguru==0.7.2",
    "platformdirs==4.2.2",
    "pyinstaller>=6.10.0,<6.16.0"
)

foreach ($package in $criticalPackages) {
    Write-Host "  Installazione: $package" -ForegroundColor Gray
    pip install $package
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ ERRORE: Installazione fallita per $package" -ForegroundColor Red
        exit 1
    }
}

# Installa dipendenze opzionali (fallimento non critico)
Write-Host "Installazione dipendenze opzionali..." -ForegroundColor Gray
$optionalPackages = @("pyautogui==0.9.54", "pydirectinput==1.0.4", "psutil==6.0.0")

foreach ($package in $optionalPackages) {
    Write-Host "  Installazione opzionale: $package" -ForegroundColor Gray
    pip install $package
    if ($LASTEXITCODE -ne 0) {
        Write-Host "⚠️  Installazione opzionale fallita per $package (non critico)" -ForegroundColor Orange
    }
}

# Verifica installazioni critiche
Write-Host "Verifica installazioni critiche..." -ForegroundColor Gray
$verificationCommands = @(
    @("PySide6", "import PySide6; print('PySide6:', PySide6.__version__)"),
    @("keyboard", "import keyboard; print('keyboard: OK')"),
    @("mouse", "import mouse; print('mouse: OK')"),
    @("PyInstaller", "import PyInstaller; print('PyInstaller:', PyInstaller.__version__)")
)

foreach ($cmd in $verificationCommands) {
    $packageName = $cmd[0]
    $testCommand = $cmd[1]
    
    $result = python -c $testCommand 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ $packageName: $result" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $packageName: ERRORE" -ForegroundColor Red
        exit 1
    }
}

# STEP 4: TEST APPLICAZIONE MIGLIORATO
Write-Host "`n--- STEP 4: Test applicazione migliorato ---" -ForegroundColor Yellow

Write-Host "Test importazione moduli AutoKey..." -ForegroundColor Gray
$importTest = python -c "
try:
    from app.gui import MainWindow
    from app.recorder import Recorder
    from app.player import Player
    print('✓ Import test superato')
except Exception as e:
    print(f'❌ Import test fallito: {e}')
    exit(1)
"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERRORE: Test import moduli fallito!" -ForegroundColor Red
    Write-Host "   Verificare la struttura del progetto" -ForegroundColor Red
    exit 1
}

Write-Host "Test avvio applicazione (3 secondi)..." -ForegroundColor Gray
$testProcess = Start-Process python -ArgumentList "-m", "app.main" -NoNewWindow -PassThru
Start-Sleep -Seconds 3

if (-not $testProcess.HasExited) {
    $testProcess.Kill()
    Write-Host "✓ Test avvio applicazione superato" -ForegroundColor Green
} else {
    Write-Host "⚠️  Applicazione terminata rapidamente (possibile ma continuiamo)" -ForegroundColor Orange
}

# STEP 5: PULIZIA BUILD PRECEDENTI
Write-Host "`n--- STEP 5: Pulizia build precedenti ---" -ForegroundColor Yellow

Write-Host "Rimozione file di build precedenti..." -ForegroundColor Gray
$cleanupItems = @("build", "dist", "*.spec", "__pycache__", "app\__pycache__")

foreach ($item in $cleanupItems) {
    if (Test-Path $item) {
        Remove-Item -Recurse -Force $item -ErrorAction SilentlyContinue
        Write-Host "  ✓ Rimosso: $item" -ForegroundColor Gray
    }
}

Write-Host "✓ Pulizia completata" -ForegroundColor Green

# STEP 6: VERIFICA ICONA CON FALLBACK
Write-Host "`n--- STEP 6: Verifica icona con fallback ---" -ForegroundColor Yellow

$iconPaths = @(
    "C:\Users\Administrator\Desktop\Icona_Minimalista_AutoKey.ico",
    "assets\icon.ico",
    "icon.ico"
)

$iconPath = ""
foreach ($path in $iconPaths) {
    if (Test-Path $path) {
        $iconPath = $path
        Write-Host "✓ Icona trovata: $iconPath" -ForegroundColor Green
        break
    }
}

if ($iconPath -eq "") {
    Write-Host "⚠️  Nessuna icona trovata, continuo senza icona personalizzata" -ForegroundColor Orange
}

# STEP 7: BUILD CON PYINSTALLER POTENZIATO
Write-Host "`n--- STEP 7: Build con PyInstaller potenziato ---" -ForegroundColor Yellow

Write-Host "Preparazione parametri PyInstaller..." -ForegroundColor Gray

# CORREZIONE PROBLEMA 3: Parametri PyInstaller ottimizzati
$pyinstallerArgs = @(
    "--onefile",
    "--windowed",
    "--name", "AutoKey",
    "--add-data", "assets;assets",
    "--hidden-import", "PySide6.QtCore",
    "--hidden-import", "PySide6.QtGui", 
    "--hidden-import", "PySide6.QtWidgets",
    "--hidden-import", "keyboard",
    "--hidden-import", "mouse",
    "--hidden-import", "loguru",
    "--collect-all", "PySide6",
    "--noconfirm"
)

# Aggiungi icona se disponibile
if ($iconPath -ne "") {
    $pyinstallerArgs += @("--icon", $iconPath)
}

# Aggiungi percorso principale
$pyinstallerArgs += "app\main.py"

Write-Host "Parametri PyInstaller:" -ForegroundColor Gray
Write-Host "