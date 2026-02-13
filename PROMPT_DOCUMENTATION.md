# Prompt Documentation (Sprint 4.1)

**Stand:** 2026-02-13  
**Zweck:** Übersicht der Prompt-Quellen, Ladewege, Platzhalter und Pflegeprozesse.

---

## 1) Prompt-Quellen

### 1.1 Dateien im Repository (`/prompts`)
Diese Dateien dienen als **Source of Truth** für Standard‑Prompts und werden über CLI in die Datenbank geladen.

| Datei | Name (DB) | Zweck |
|---|---|---|
| `staerkenanalyse_prompt_final.txt` | Stärkenanalyse Final | Finaler, optimierter Stärkenanalyse‑Prompt |
| `bestsofar2.txt` | Best Performing v2 | Experimentell, hohe Analysequalität (v2) |
| `bestsofar.txt` | Best Performing v1 | Experimentell, hohe Analysequalität (v1) |
| `structured_report_mistral.txt` | Strukturierter Report (Mistral) | Mistral‑optimierter Report‑Prompt |
| `structured_report_json.txt` | Strukturierter Report (JSON) | JSON‑Output für maschinelle Verarbeitung |
| `structured_report.txt` | Strukturierter Report | Klar strukturierter Report‑Prompt |
| `staerkenanalyse_prompt.txt` | Stärkenanalyse Original | Historischer Ausgangspunkt |
| `mistralsozverb4.txt` | MistralSozVerb4 | Rekonstruiertes Prompt‑Template (JSON‑Output) |

**Quelle der Zuordnung:** `load_default_prompts.py` (PROMPT_FILES).

---

## 2) Prompt‑Ladevorgang (DB Sync)

### 2.1 CLI‑Import
Prompts werden aus `/prompts` in die DB geladen:

- **Command:** `flask load-default-prompts`
- **Optional:** `flask load-default-prompts --clear`

**Hinweise:**
- Existierende Prompts werden übersprungen (Name‑Match).
- `--clear` löscht alle Prompts vor dem Import.

---

## 3) Prompt‑Verwendung in der App

### 3.1 Analyse (Einzel‑Analyse)
Prompt‑Text wird in `blueprints/analysis.py` verwendet und Platzhalter ersetzt:

**Unterstützte Platzhalter:**
- `{{name}}`, `{{vorname}}`, `{{first_name}}`
- `{{ganzer_name}}`
- `{{social_observations}}`
- `{{verbal_observations}}`
- `{{additional_content}}`
- `{{context}}` (wenn vorhanden, wird kompletter Kontextblock ersetzt)

Der Kontextblock enthält u. a.:
- Teilnehmer‑Name
- Beobachtungen (Sozial/Verbal)
- Aufgabenbeschreibungen (wenn Gruppe Aufgaben zugeordnet hat)
- Zusatzinhalte (z. B. Upload‑Dateien)

### 3.2 Analyse (Batch)
Batch‑Analyse nutzt `{{context}}` und injiziert einen vollständigen Kontextblock.

### 3.3 JSON‑Output (wenn strukturierter Output erwartet wird)

Wenn ein Prompt JSON liefern soll, **muss** er exakt JSON zurückgeben (ohne Markdown‑Codeblöcke). Empfohlenes Minimal‑Schema:

```json
{
	"sk_ratings": {
		"flexibility": 0,
		"team_orientation": 0,
		"process_orientation": 0,
		"results_orientation": 0
	},
	"vk_ratings": {
		"flexibility": 0,
		"consulting": 0,
		"objectivity": 0,
		"goal_orientation": 0
	},
	"ki_texts": {
		"social_text": "",
		"verbal_text": "",
		"summary_text": ""
	}
}
```

**Hinweis:** Abweichende Schlüssel werden in `analysis.py` teilw. gemappt, sollten aber **nicht** als Standard genutzt werden.

---

## 4) Prompt‑Verwaltung (UI)

- Prompts können unter `/prompts` verwaltet werden.
- Name ist **unique** (DB‑Constraint).
- Inhalte werden in der Tabelle `Prompt` gespeichert.
- Ein Prompt kann als **Standard** markiert werden (Checkbox). Dieser wird in der KI‑Analyse vorausgewählt.
- Es kann immer nur **ein** Standard‑Prompt aktiv sein.

---

## 5) Export / Backup

Prompts werden zusätzlich über die Backup‑Logik exportiert:
- **Command:** `flask export-prompts`
- **Ziel:** `backups/prompts_export/`

Diese Export‑Dateien dienen als zusätzliche Sicherung außerhalb der DB.

---

## 6) Prompt‑Qualität & Pflege

**Empfohlene Regeln:**
1. **Klare Struktur:** System/Instruktionen/Output‑Format trennen.
2. **Stabile Platzhalter:** Nur definierte Variablen verwenden (siehe Abschnitt 3).
3. **Output‑Format:** Wenn JSON erwartet wird, strikt JSON (ohne Markdown‑Codeblöcke).
4. **Regression vermeiden:** Änderungen nur mit begleitenden Tests/Logs.

### 6.1 Naming‑Konventionen (empfohlen)

**Schema:** `<Zweck> – <Provider/Format> – vX` (Kurz, eindeutig, versioniert)

Beispiele:
- `Stärkenanalyse Final – Mistral – v1`
- `Strukturierter Report – JSON – v1`
- `Batch Analyse – Generic – v2`

**Hinweise:**
- Provider‑Spezifika (Mistral/Gemini) im Namen sichtbar machen.
- Bei Breaking‑Änderungen: Version hochzählen und alten Prompt behalten.
- Kurzbeschreibung im `description` Feld pflegen (Zweck + Outputformat).

---

## 7) KI‑Gym (Prompt Learning)

Das System kann aus Nutzer‑Edits lernen:
- `AIRawResponse` speichert Original‑KI‑Antwort
- `ContentEdit` speichert Diff‑Metriken
- `LearnedPromptRule` speichert abgeleitete Regeln

Diese Regeln können perspektivisch die Prompt‑Qualität verbessern.

---

## 8) Schnell‑Checkliste

- [ ] Prompt liegt in `/prompts` und ist im `PROMPT_FILES`‑Mapping
- [ ] `flask load-default-prompts` ausgeführt
- [ ] Platzhalter entsprechen den unterstützten Variablen
- [ ] JSON‑Prompts liefern exakt das definierte Schema (ohne Markdown‑Codeblöcke)
- [ ] Export/Backup geprüft

---

## 9) Nächste Schritte (Sprint 4.1)

- Prompt‑Library konsolidieren (Dublettenkontrolle)
- Prompt‑Naming‑Konventionen definieren
- JSON‑Outputs stabilisieren (Schema‑Checks)

---

## 10) Prompt‑Library Konsolidierung (Stand 2026-02-13)

**Ziel:** Dubletten reduzieren, Legacy‑Prompts markieren, aktive Prompts klar kennzeichnen.

| Prompt | Status | Empfehlung |
|---|---|---|
| Stärkenanalyse Final | ✅ Aktiv | **Bevorzugen** als Default‑Prompt |
| Strukturierter Report (Mistral) | ✅ Aktiv | Mistral‑optimiert, behalten |
| Strukturierter Report (JSON) | ✅ Aktiv | Für JSON‑Output verwenden |
| Strukturierter Report | ✅ Aktiv | Provider‑neutral, fallback |
| Best Performing v2 | 🟡 Experimentell | Weiter testen, optional als Alternative |
| Best Performing v1 | 🟡 Experimentell | **Konsolidieren** → v2 bevorzugen |
| Stärkenanalyse Original | 🔶 Legacy | **Beibehalten** als historische Referenz |
| MistralSozVerb4 | 🟡 Rekonstruiert | **Testen** und bei Bedarf iterieren |

**Empfohlene Aktionen:**
1. **Default‑Prompt** explizit festlegen (z. B. “Stärkenanalyse Final”).
2. **Best Performing v1** als Legacy markieren (oder zusammenführen in v2).
3. **Naming** nach Abschnitt 6.1 standardisieren.

---

## 11) Schema‑Checks (Prompt‑Qualität)

Wenn ein Prompt JSON liefern soll, sind folgende Checks Pflicht:

### 11.1 Struktur‑Check (manuell)
- Enthält alle Schlüssel aus dem Minimal‑Schema (Abschnitt 3.3)
- Keine zusätzlichen Root‑Keys ohne Mapping
- Werte sind valide Typen (Zahl/String)

### 11.2 Output‑Check (manuell)
- **Kein** Markdown (` ``` `, `**`, `#`)
- **Nur** JSON (keine Erklärtexte)

### 11.3 Mapping‑Check (Code)
`analysis.py` mappt alternative Keys (z. B. Copilot‑Varianten). Neue Keys **müssen** dort ergänzt werden, wenn ein Prompt abweicht.

### 11.4 Checkliste (Kurzform)
- [ ] JSON ohne Markdown
- [ ] Minimal‑Schema vollständig
- [ ] Keine unbekannten Root‑Keys
- [ ] Mapping in `analysis.py` geprüft
