# =============================================================================
# AUTOKEY - COMANDI DI BUILD CORRETTI
# CORREZIONE PROBLEMA 4: Script di build migliorato per risolvere tutti gli errori
# =============================================================================

# IMPORTANTE: Eseguire tutti i comandi in PowerShell come Amministratore
# dalla directory C:\Users\Administrator\Desktop\macro_recorder

Write-Host "=== AUTOKEY - PROCEDURA DI BUILD COMPLETA ===" -ForegroundColor Cyan

# STEP 1: VERIFICA PREREQUISITI
Write-Host "`n--- STEP 1: Verifica prerequisiti ---" -ForegroundColor Yellow

# Verifica Python (deve essere 3.10+ 64-bit)
Write-Host "Verifica versione Python..." -ForegroundColor Gray
python --version
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERRORE: Python non trovato o non nel PATH!" -ForegroundColor Red
    Write-Host "   Installare Python 3.10+ 64-bit da python.org" -ForegroundColor Red
    exit 1
}

# Verifica directory corrente
$currentDir = Get-Location
Write-Host "Directory corrente: $currentDir" -ForegroundColor Gray
if (-not (Test-Path "app\main.py")) {
    Write-Host "❌ ERRORE: Directory errata! Spostarsi in C:\Users\Administrator\Desktop\macro_recorder" -ForegroundColor Red
    exit 1
}

# STEP 2: CONFIGURAZIONE AMBIENTE VIRTUALE
Write-Host "`n--- STEP 2: Configurazione ambiente virtuale ---" -ForegroundColor Yellow

# Rimuovi ambiente virtuale precedente se esiste
if (Test-Path ".venv") {
    Write-Host "Rimozione ambiente virtuale precedente..." -ForegroundColor Gray
    Remove-Item -Recurse -Force ".venv" -ErrorAction SilentlyContinue
}

# Crea nuovo ambiente virtuale
Write-Host "Creazione ambiente virtuale..." -ForegroundColor Gray
python -m venv .venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERRORE: Impossibile creare ambiente virtuale!" -ForegroundColor Red
    exit 1
}

# Configura policy di esecuzione se necessario
Write-Host "Configurazione policy di esecuzione..." -ForegroundColor Gray
try {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
    Write-Host "✓ Policy di esecuzione configurata" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Impossibile modificare policy di esecuzione" -ForegroundColor Orange
}

# Attiva ambiente virtuale
Write-Host "Attivazione ambiente virtuale..." -ForegroundColor Gray
& ".\.venv\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERRORE: Impossibile attivare ambiente virtuale!" -ForegroundColor Red
    Write-Host "   Provare: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Ambiente virtuale attivato con successo" -ForegroundColor Green

# STEP 3: INSTALLAZIONE DIPENDENZE
Write-Host "`n--- STEP 3: Installazione dipendenze ---" -ForegroundColor Yellow

# Aggiorna pip
Write-Host "Aggiornamento pip..." -ForegroundColor Gray
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️ Errore aggiornamento pip, continuando..." -ForegroundColor Orange
}

# Installa dipendenze
Write-Host "Installazione dipendenze dal requirements.txt..." -ForegroundColor Gray
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERRORE: Installazione dipendenze fallita!" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Dipendenze installate con successo" -ForegroundColor Green

# STEP 4: TEST APPLICAZIONE
Write-Host "`n--- STEP 4: Test applicazione ---" -ForegroundColor Yellow

Write-Host "Avvio test applicazione (si chiuderà automaticamente dopo 5 secondi)..." -ForegroundColor Gray
$testProcess = Start-Process python -ArgumentList "-m", "app.main" -NoNewWindow -PassThru
Start-Sleep -Seconds 5
if (-not $testProcess.HasExited) {
    $testProcess.Kill()
}

if ($testProcess.ExitCode -eq 0 -or $testProcess.HasExited) {
    Write-Host "✓ Test applicazione superato" -ForegroundColor Green
} else {
    Write-Host "⚠️ Test applicazione con possibili problemi, continuando..." -ForegroundColor Orange
}

# STEP 5: PULIZIA FILE PRECEDENTI
Write-Host "`n--- STEP 5: Pulizia build precedenti ---" -ForegroundColor Yellow

Write-Host "Rimozione file di build precedenti..." -ForegroundColor Gray
Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "dist" -ErrorAction SilentlyContinue
Remove-Item "*.spec" -ErrorAction SilentlyContinue

Write-Host "✓ Pulizia completata" -ForegroundColor Green

# STEP 6: VERIFICA ICONA
Write-Host "`n--- STEP 6: Verifica icona ---" -ForegroundColor Yellow

$iconPath = "C:\Users\Administrator\Desktop\Icona_Minimalista_AutoKey.ico"
if (Test-Path $iconPath) {
    Write-Host "✓ Icona trovata: $iconPath" -ForegroundColor Green
} else {
    Write-Host "⚠️ Icona non trovata: $iconPath" -ForegroundColor Orange
    Write-Host "   Il build continuerà senza icona personalizzata" -ForegroundColor Orange
    $iconPath = ""
}

# STEP 7: BUILD CON PYINSTALLER
Write-Host "`n--- STEP 7: Build con PyInstaller ---" -ForegroundColor Yellow

Write-Host "Inizio build eseguibile..." -ForegroundColor Gray

# Comando PyInstaller corretto e completo
$pyinstallerArgs = @(
    "--onefile"
    "--windowed"
    "--name", "AutoKey"
    "--add-data", "assets;assets"
    "app\main.py"
)

# Aggiungi icona solo se disponibile
if ($iconPath -ne "") {
    $pyinstallerArgs += "--icon", $iconPath
}

# Esegui PyInstaller
Write-Host "Esecuzione PyInstaller con parametri:" -ForegroundColor Gray
Write-Host "  " ($pyinstallerArgs -join " ") -ForegroundColor Gray

& ".\.venv\Scripts\python.exe" -m PyInstaller @pyinstallerArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERRORE: Build PyInstaller fallito!" -ForegroundColor Red
    Write-Host "`nDiagnostica errori comuni:" -ForegroundColor Yellow
    Write-Host "1. Controllare che tutte le dipendenze siano installate" -ForegroundColor Gray
    Write-Host "2. Verificare permessi di scrittura nella directory" -ForegroundColor Gray
    Write-Host "3. Controllare che l'antivirus non blocchi PyInstaller" -ForegroundColor Gray
    exit 1
}

Write-Host "✓ Build PyInstaller completato" -ForegroundColor Green

# STEP 8: COPIA PLUGIN QT (CRITICO)
Write-Host "`n--- STEP 8: Copia plugin Qt ---" -ForegroundColor Yellow

Write-Host "Esecuzione script copia plugin (versione migliorata)..." -ForegroundColor Gray
python copy_plugins.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ ERRORE: Copia plugin fallita!" -ForegroundColor Red
    Write-Host "`nPossibili soluzioni:" -ForegroundColor Yellow
    Write-Host "1. Verificare che PySide6 sia installato: pip show PySide6" -ForegroundColor Gray
    Write-Host "2. Controllare permessi directory dist/" -ForegroundColor Gray
    Write-Host "3. Reinstallare PySide6: pip uninstall PySide6 && pip install PySide6" -ForegroundColor Gray
    exit 1
}

Write-Host "✓ Plugin Qt copiati con successo" -ForegroundColor Green

# STEP 9: VERIFICA BUILD
Write-Host "`n--- STEP 9: Verifica build ---" -ForegroundColor Yellow

$exePath = "dist\AutoKey.exe"
if (Test-Path $exePath) {
    $fileSize = (Get-Item $exePath).Length / 1MB
    Write-Host "✓ AutoKey.exe creato con successo" -ForegroundColor Green
    Write-Host "  Dimensione: $([math]::Round($fileSize, 1)) MB" -ForegroundColor Gray
    Write-Host "  Percorso: $(Resolve-Path $exePath)" -ForegroundColor Gray
} else {
    Write-Host "❌ ERRORE: AutoKey.exe non trovato!" -ForegroundColor Red
    exit 1
}

# Verifica plugin
$pluginsPath = "dist\AutoKey\platforms"
if (Test-Path $pluginsPath) {
    $pluginCount = (Get-ChildItem $pluginsPath).Count
    Write-Host "✓ Plugin Qt presenti: $pluginCount file" -ForegroundColor Green
} else {
    Write-Host "⚠️ Plugin Qt non trovati, potrebbero verificarsi errori di avvio" -ForegroundColor Orange
}

# STEP 10: TEST ESEGUIBILE
Write-Host "`n--- STEP 10: Test eseguibile ---" -ForegroundColor Yellow

Write-Host "Test avvio eseguibile (si chiuderà dopo 8 secondi)..." -ForegroundColor Gray
try {
    $testExeProcess = Start-Process $exePath -PassThru
    Start-Sleep -Seconds 8
    
    if (-not $testExeProcess.HasExited) {
        $testExeProcess.Kill()
        Write-Host "✓ Eseguibile avviato correttamente" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Eseguibile terminato prematuramente, controllare log" -ForegroundColor Orange
    }
} catch {
    Write-Host "⚠️ Impossibile testare eseguibile: $_" -ForegroundColor Orange
}

# STEP 11: CREAZIONE RELEASE
Write-Host "`n--- STEP 11: Creazione cartella release ---" -ForegroundColor Yellow

$releasePath = "C:\Users\Administrator\Desktop\AutoKey_Release"
Write-Host "Creazione cartella release: $releasePath" -ForegroundColor Gray

# Crea directory release
New-Item -ItemType Directory -Path $releasePath -Force | Out-Null

# Copia eseguibile
Copy-Item $exePath $releasePath -Force
Write-Host "✓ AutoKey.exe copiato nella release" -ForegroundColor Green

# Copia icona se disponibile
if ($iconPath -ne "" -and (Test-Path $iconPath)) {
    Copy-Item $iconPath $releasePath -Force
    Write-Host "✓ Icona copiata nella release" -ForegroundColor Green
}

# Crea file README per la release
$readmeContent = @"
AUTOKEY - MACRO RECORDER
========================

Istruzioni per l'uso:
1. Eseguire AutoKey.exe per avviare l'applicazione
2. Cliccare "Registra" per iniziare a registrare macro
3. Cliccare "Stop" per terminare la registrazione
4. Usare "Esegui selezionata" per riprodurre le macro

Requisiti di sistema:
- Windows 10/11 (64-bit)
- Permessi amministratore per alcune funzioni avanzate

Risoluzione problemi:
- Se l'applicazione non si avvia, controllare Windows Defender
- Aggiungere eccezione antivirus per AutoKey.exe se necessario
- Per supporto tecnico, controllare i log nella directory AppData

Versione build: $(Get-Date -Format "yyyy-MM-dd HH:mm")
"@

$readmeContent | Out-File -FilePath "$releasePath\README.txt" -Encoding UTF8
Write-Host "✓ README.txt creato nella release" -ForegroundColor Green

# STEP 12: RIEPILOGO FINALE
Write-Host "`n=== RIEPILOGO BUILD AUTOKEY ===" -ForegroundColor Cyan
Write-Host "✅ Build completato con SUCCESSO!" -ForegroundColor Green
Write-Host "`nFile generati:" -ForegroundColor White
Write-Host "  📁 Eseguibile: $exePath" -ForegroundColor Gray
Write-Host "  📁 Release: $releasePath" -ForegroundColor Gray
Write-Host "  📄 README: $releasePath\README.txt" -ForegroundColor Gray

Write-Host "`nComandi di test rapidi:" -ForegroundColor White
Write-Host "  Test eseguibile: .\dist\AutoKey.exe" -ForegroundColor Gray
Write-Host "  Apri release: explorer '$releasePath'" -ForegroundColor Gray

Write-Host "`n🎉 AutoKey è pronto per l'uso!" -ForegroundColor Green

# COMANDI RAPIDI PER RICOMPILAZIONI FUTURE
Write-Host "`n=== COMANDI RAPIDI PER FUTURE RICOMPILAZIONI ===" -ForegroundColor Cyan
Write-Host "Per ricompilazioni veloci (senza reinstallare dipendenze):" -ForegroundColor Yellow

$quickRebuild = @'
# REBUILD RAPIDO (solo dopo modifiche al codice)
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m PyInstaller --onefile --windowed --name "AutoKey" --icon "C:\Users\Administrator\Desktop\Icona_Minimalista_AutoKey.ico" --add-data "assets;assets" app\main.py
python copy_plugins.py
Copy-Item "dist\AutoKey.exe" "C:\Users\Administrator\Desktop\AutoKey_Release\" -Force
'@

Write-Host $quickRebuild -ForegroundColor Gray

Write-Host "`n✨ Build di AutoKey completato con successo! ✨" -ForegroundColor Magenta