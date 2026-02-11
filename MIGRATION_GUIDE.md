# Testdaten-Migration: Schritt-für-Schritt-Anleitung

**Zuletzt geprüft:** 2026-02-11 (v1.3.1)

## ⚠️ Wichtig: Vor dem Start

Diese Anleitung ersetzt **alle realen Nutzerdaten** durch **KI-generierte synthetische Testdaten**.

**Voraussetzungen:**
- ✅ Flask-App läuft
- ✅ API-Key gesetzt (`MISTRAL_API_KEY` oder `GOOGLE_API_KEY` in `.env`)
- ✅ Backup-Strategie überlegt

---

## 📋 Migration durchführen

### **Schritt 1: Realdaten exportieren** (MANUELL)

1. **App starten:**
   ```bash
   python app.py
   ```

2. **Browser öffnen:**
   ```
   http://localhost:5001/export_selection
   ```

3. **Alle Gruppen exportieren:**
   - ☑️ "Alle sichtbaren Teilnehmer auswählen" aktivieren
   - Format: **Excel (.xlsx)** wählen
   - Button: "Exportieren"

4. **Export sichern:**
   ```bash
   # WICHTIG: Außerhalb des Projekts speichern!
   mv ~/Downloads/staerkenanalyse_export_*.xlsx ~/Backups/REALDATEN_$(date +%Y%m%d).xlsx
   ```

   **Optional:** Export verschlüsseln
   ```bash
   # Mit gpg verschlüsseln
   gpg -c ~/Backups/REALDATEN_20260207.xlsx
   ```

---

### **Schritt 2: Alle Gruppen löschen** (MANUELL)

1. **Im Browser:**
   ```
   http://localhost:5001/groups
   ```

2. **Jede Gruppe einzeln löschen:**
   - Gruppe öffnen (Chevron-Icon klicken)
   - Button: "Gruppe löschen"
   - Bestätigen

3. **Verifizieren:**
   - Dashboard sollte zeigen: `0 Gruppen, 0 Teilnehmer`

**Hinweis:** Cascade Delete entfernt automatisch:
- ✅ Alle Teilnehmer der Gruppe
- ✅ Alle Selbsteinschätzungen
- ✅ Keine Prompts/ExplanationBlocks (bleiben erhalten)

---

### **Schritt 3: Testdaten generieren** (AUTOMATISCH)

**Basismodus (Standard):**
```bash
flask generate-test-data
```
- **Erstellt:** 2 Gruppen mit je 8-10 Teilnehmern
- **Dauer:** ~2-3 Minuten (abhängig von API-Geschwindigkeit)

**Erweiterte Optionen:**

```bash
# Mehr Gruppen/Teilnehmer
flask generate-test-data --groups 4 --participants 12-15

# Mit automatischer Löschung (VORSICHT!)
flask generate-test-data --clear

# Hilfe anzeigen
flask generate-test-data --help
```

**Parameter:**
- `--groups N`: Anzahl Gruppen (Standard: 2)
- `--participants X-Y`: Teilnehmer-Range pro Gruppe (Standard: 8-10)
- `--clear`: Löscht ALLE Daten vor Generierung (mit Bestätigung)

**Was wird generiert:**

| Element | Details |
|---------|---------|
| **Gruppen** | Fake-Namen, Städte, Datum-Range |
| **Teilnehmer** | Deutsche Namen via LiteLLM |
| **Beobachtungen** | KI-generierte Texte (50-80 Wörter) |
| **SK/VK Ratings** | Zufällige Werte 0-10 (Summe max 25) |
| **KI-Texte** | HTML-formatiert (100-130 Wörter) |
| **Selbsteinschätzungen** | ~65% der Teilnehmer (180-220 Wörter) |

---

### **Schritt 4: Validierung**

1. **Dashboard prüfen:**
   ```
   http://localhost:5001/
   ```
   - Zeigt neue Gruppen/Teilnehmer an?
   - Statistiken korrekt?

2. **Test-Workflow:**
   - ✅ Teilnehmer-Übersicht öffnen
   - ✅ Fremdeinschätzung bearbeiten
   - ✅ KI-Analyse durchführen (optional)
   - ✅ PDF generieren
   - ✅ Export/Import testen

3. **DB-Check (optional):**
   ```bash
   flask shell
   >>> from models import Group, Participant, SelfAssessment
   >>> Group.query.count()
   2
   >>> Participant.query.count()
   18
   >>> SelfAssessment.query.count()
   12
   ```

---

## 🔄 Bei Problemen

### **API-Fehler (LiteLLM)**

**Symptom:** 
```
⚠️ LiteLLM API Fehler: ... Verwende Fallback-Namen.
```

**Lösung:**
- Prüfe API-Key in `.env`
- Fallback-Daten werden automatisch verwendet
- Daten sind dennoch vollständig (nur generischer)

### **Datenbank-Fehler**

**Symptom:**
```
sqlalchemy.exc.IntegrityError: ...
```

**Lösung:**
```bash
# Datenbank zurücksetzen
rm instance/database.db
flask db upgrade
flask generate-test-data
```

### **Command nicht gefunden**

**Symptom:**
```
Error: No such command 'generate-test-data'
```

**Lösung:**
- Prüfe dass `generate_test_data.py` existiert
- Prüfe dass Command in `app.py` registriert ist
- Flask-App neu starten

---

## 📊 Zu erwartende Ausgabe

```bash
$ flask generate-test-data
======================================================================
🔧 Testdaten-Generator für Stärkenanalyse-App
======================================================================

📊 Konfiguration:
   • Gruppen: 2
   • Teilnehmer pro Gruppe: 8-10
   • Selbsteinschätzungen: ~65% der Teilnehmer

🚀 Starte Generierung...

📁 Gruppe 1/2: Trainingsgruppe Herbst 2025 (München)
   👤 1/9: Anna Schmidt... ✅ (+SE)
   👤 2/9: Max Müller... ✅
   👤 3/9: Sophie Weber... ✅ (+SE)
   ...

📁 Gruppe 2/2: Trainingsgruppe Frühjahr 2026 (Berlin)
   👤 1/10: Leon Fischer... ✅ (+SE)
   ...

======================================================================
✅ Testdaten erfolgreich generiert!
======================================================================
📊 Statistik:
   • 2 Gruppen erstellt
   • 19 Teilnehmer generiert
   • 12 Selbsteinschätzungen erstellt (63%)

🎯 Nächste Schritte:
   1. App starten: python app.py
   2. Dashboard öffnen: http://localhost:5001
   3. Features mit Testdaten testen
```

---

## 🎯 Nächste Schritte

Nach erfolgreicher Migration:

1. **Testen:** Alle Features mit Testdaten durchspielen
2. **Dokumentieren:** Ggf. Screenshots für Doku erstellen
3. **Realdaten:** Backup sicher aufbewahren (verschlüsselt!)

---

## ℹ️ Hinweise

- **Keine realen Daten:** Alle Namen/Texte sind KI-generiert
- **Reproduzierbar:** Command kann mehrfach ausgeführt werden
- **Abwärtskompatibel:** Export-Format bleibt identisch
- **Kein Backup nötig:** Testdaten sind jederzeit neu generierbar

**Bei Fragen:** Siehe `VERSIONING.md` oder `TODO_TESTDATA.md`
