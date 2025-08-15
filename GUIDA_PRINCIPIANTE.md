# 🎯 AUTOKEY - GUIDA PER PRINCIPIANTI

**Benvenuto in AutoKey!** Questa guida ti accompagnerà passo dopo passo nell'uso del registratore di macro più semplice e potente per Windows.

## 📋 Cosa Imparerai

- ✅ Come installare e avviare AutoKey  
- ✅ Come registrare le tue prime macro
- ✅ Come riprodurre e gestire le macro salvate
- ✅ Come risolvere i problemi più comuni
- ✅ Trucchi e consigli per un uso avanzato

---

## 🚀 PRIMA INSTALLAZIONE

### Passaggio 1: Verifica i Requisiti
**Cosa ti serve:**
- Computer con Windows 10 o 11 (64-bit)
- Permessi di amministratore
- 5 minuti di tempo

### Passaggio 2: Download dell'Applicazione
1. Vai nella cartella **AutoKey_Release** 
2. Vedrai il file **AutoKey.exe** 
3. Fai doppio click per avviare l'applicazione

⚠️ **IMPORTANTE**: Se Windows Defender blocca l'applicazione:
- Clicca "Maggiori informazioni" 
- Clicca "Esegui comunque"
- Questo è normale per applicazioni non firmate

---

## 🎬 REGISTRARE LA PRIMA MACRO

### Cosa è una Macro?
Una **macro** è semplicemente una sequenza registrata di:
- Movimenti del mouse
- Click del mouse  
- Pressione di tasti sulla tastiera

AutoKey "ricorda" tutto quello che fai e può ripeterlo identicamente!

### Registrazione Passo-Passo

#### 1️⃣ Avvia la Registrazione
- Apri AutoKey
- Clicca il pulsante **"Registra"** nella barra degli strumenti
- L'applicazione si nasconderà automaticamente
- Vedrai apparire un pulsante **"Stop"** rosso nell'angolo in basso a destra dello schermo

#### 2️⃣ Esegui le Azioni che Vuoi Registrare
Ora AutoKey sta registrando TUTTO quello che fai:
- **Movimenti del mouse** → Registrati con precisione millimetrica
- **Click sinistro/destro** → Registrati con posizione esatta
- **Digitazione testo** → Ogni lettera viene memorizzata
- **Tasti speciali** → Ctrl, Alt, Shift, Frecce, ecc.
- **Scroll della rotella** → Direzione e intensità

**Esempio pratico**: Registriamo l'apertura del Blocco Note
1. Clicca su **"Registra"**
2. Premi **Windows + R** (si apre Esegui)
3. Digita **"notepad"**
4. Premi **Invio**
5. Digita **"Ciao, questa è la mia prima macro!"**
6. Clicca **"Stop"** (pulsante rosso)

#### 3️⃣ Ferma la Registrazione
- Clicca il pulsante **"Stop"** rosso quando hai finito
- **TRUCCO**: Fai click destro sul pulsante Stop per trascinarlo se ti dà fastidio

#### 4️⃣ Salva la Macro
Si aprirà una finestra che ti chiede:
- **Nome della macro**: Scrivi un nome descrittivo (es. "Apri Blocco Note")
- **Modalità di riproduzione**:
  - **"Con pause"** = Riproduce rispettando i tempi originali
  - **"Senza pause"** = Riproduce tutto velocemente

**Consiglio**: Inizia sempre con "Con pause" per i primi test!

---

## ▶️ RIPRODURRE LE MACRO

### Metodo 1: Doppio Click
- Nella lista delle macro, fai **doppio click** su quella che vuoi riprodurre
- L'applicazione si nasconderà e la macro partirà automaticamente

### Metodo 2: Pulsante "Esegui selezionata"  
- Seleziona una macro dalla lista (un solo click)
- Clicca il pulsante **"Esegui selezionata"**

### Metodo 3: "Esegui ultimo" (Scorciatoia)
- Clicca **"Esegui ultimo"** per riprodurre l'ultima macro registrata
- Perfetto per testare rapidamente le macro appena create

### ⚠️ Cosa Succede Durante la Riproduzione
1. **L'applicazione si nasconde** automaticamente
2. **La macro viene eseguita** esattamente come l'hai registrata
3. **L'applicazione ricompare** quando la macro è finita
4. **NON TOCCARE NULLA** durante la riproduzione per evitare interferenze

---

## 🛠️ GESTIONE DELLE MACRO

### Modificare una Macro Esistente
**Cambiare nome:**
1. Seleziona la macro nella lista
2. Fai doppio click sul nome
3. Scrivi il nuovo nome
4. Premi Invio

**Cambiare ripetizioni:**
1. Seleziona la macro
2. Fai doppio click nella colonna "Ripetizioni"
3. Scrivi quante volte vuoi che si ripeta (es. 5)

**Cambiare modalità pause:**
- Seleziona la macro
- Clicca "Toggle Con/Senza pause"

### Organizzare le Macro
**Preferiti (★):**
- Seleziona una macro importante
- Clicca "Aggiungi/Rimuovi preferiti"
- Le macro preferite appariranno in cima alla lista con una stellina ★

**Eliminare macro:**
- Seleziona la macro da eliminare
- Clicca "Elimina" oppure premi il tasto **Canc**

### Esportare e Importare
**Esportare** (per backup o condivisione):
- Seleziona la macro
- Clicca "Esporta JSON"
- Salva il file dove preferisci

**Importare** (ricevuto da altri o backup):
- Clicca "Importa JSON"
- Seleziona il file da caricare

---

## 🎨 PERSONALIZZAZIONE

### Cambiare Tema
- Clicca su **"Tema: Chiaro"** nella barra degli strumenti
- Si alternerà tra tema chiaro e scuro
- La preferenza viene salvata automaticamente

### Aiuto Integrato
- Clicca su **"Aiuto"** per vedere i comandi rapidi

---

## 🚨 RISOLUZIONE PROBLEMI COMUNI

### ❌ "L'applicazione non si avvia"
**Possibili soluzioni:**
1. **Windows Defender**: Aggiungi AutoKey.exe alle eccezioni antivirus
2. **Permessi**: Fai click destro → "Esegui come amministratore"  
3. **File corrotti**: Riscarica AutoKey.exe

### ❌ "La macro non riproduce correttamente i tasti"
**Possibili cause:**
- **Tasti bloccati**: Dopo la riproduzione, premi manualmente Shift, Ctrl, Alt per sbloccarli
- **Layout tastiera**: Verifica che il layout di tastiera sia lo stesso di quando hai registrato
- **Velocità eccessiva**: Registra la macro "Con pause" invece che "Senza pause"

### ❌ "Il click del mouse non funziona" 
**Possibili soluzioni:**
- **Risoluzione schermo**: Registra e riproduci alla stessa risoluzione schermo
- **Finestre spostate**: Assicurati che le finestre siano nella stessa posizione
- **Modalità amministratore**: Avvia AutoKey come amministratore

### ❌ "La registrazione è troppo sensibile"
**Per ridurre movimenti mouse eccessivi:**
- Muovi il mouse più lentamente durante la registrazione
- Registra solo i movimenti essenziali
- Usa "Senza pause" per riproduzione più fluida

### ❌ "Caratteri duplicati o mancanti"
**Soluzioni:**
- Registra con "Con pause" attivo
- Digita più lentamente durante la registrazione
- Verifica che non ci siano altri software di input attivi

---

## 💡 TRUCCHI E CONSIGLI

### 🎯 Per Registrazioni Perfette
1. **Pianifica prima**: Pensa a tutti i passaggi prima di iniziare a registrare
2. **Movimenti precisi**: Muovi il mouse lentamente e con precisione
3. **Pause naturali**: Fai piccole pause tra le azioni per registrazioni più pulite
4. **Test immediati**: Prova sempre la macro subito dopo averla registrata

### ⚡ Per Riproduzione Efficace  
1. **Chiudi applicazioni inutili**: Meno interferenze = migliore riproduzione
2. **Stessa configurazione**: Riproduci nelle stesse condizioni della registrazione
3. **Non muovere il mouse**: Durante la riproduzione, tieni le mani ferme
4. **Usa i preferiti**: Marca le macro più usate come preferite

### 🔧 Per Gestione Avanzata
1. **Nomi descrittivi**: Usa nomi che descrivono chiaramente cosa fa la macro
2. **Backup regolari**: Esporta le macro importanti regolarmente
3. **Test su dati sicuri**: Testa sempre su dati di prova, mai su file importanti
4. **Documentazione**: Tieni nota di cosa fa ogni macro complessa

### 🚀 Esempi di Macro Utili
**Macro di automazione ufficio:**
- Aprire applicazioni specifiche
- Compilare moduli ripetitivi
- Inviare email standard
- Organizzare file e cartelle

**Macro per gaming:**
- Sequenze di comandi complesse
- Combinazioni di tasti rapide
- Azioni ripetitive nei giochi

**Macro per sviluppo:**
- Compilare e testare codice
- Aprire ambienti di sviluppo
- Eseguire sequenze di comandi

---

## 📞 SUPPORTO E RISORSE

### Se Hai Ancora Problemi
1. **Riavvia l'applicazione** e riprova
2. **Riavvia il computer** per reset completo  
3. **Reinstalla AutoKey** scaricando una nuova copia
4. **Controlla gli aggiornamenti** per versioni più recenti

### Ricorda
- ✅ AutoKey è progettato per essere **semplice**
- ✅ Con un po' di pratica diventerà **naturale**
- ✅ Inizia con macro **semplici** e poi passa a quelle complesse
- ✅ **Testa sempre** prima di usare su dati importanti

---

## 🎉 CONGRATULAZIONI!

Ora hai tutte le conoscenze necessarie per usare AutoKey efficacemente!

**Ricorda i punti chiave:**
1. 🎬 **Registra** cliccando "Registra" e fermandoti con "Stop"
2. ▶️ **Riproduci** con doppio click o "Esegui selezionata"  
3. ⭐ **Organizza** usando preferiti e nomi descrittivi
4. 💾 **Salva** le macro importanti esportandole
5. 🚨 **Risolvi** i problemi consultando questa guida

**Divertiti con AutoKey e automatizza la tua produttività!** 🚀