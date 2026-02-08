# Versionierungs-Leitfaden

Dieses Dokument erklärt, wie die Versionsnummern in dieser App verwaltet werden.

## Zwei unabhängige Versionen

### 1. App-Version (`APP_VERSION`)
**Aktuell:** `0.4.0`  
**Zweck:** Release-Tracking, Bug-Reports, Changelog

**Format:** `MAJOR.MINOR.PATCH` (Semantic Versioning)

### 2. Export-Schema-Version (`EXPORT_SCHEMA_VERSION`)
**Aktuell:** `1.0`  
**Zweck:** Import/Export-Kompatibilität von CSV/Excel-Dateien

**Format:** `MAJOR.MINOR`

---

## Wann welche Version hochzählen?

### App-Version hochzählen

#### Pre-Release (0.x.y)
Solange die App noch nicht produktiv läuft:

| Änderung | Neue Version | Beispiel |
|----------|--------------|----------|
| **Bugfix** | `0.x.PATCH++` | `0.1.0` → `0.1.1` |
| **Neues Feature** | `0.MINOR++.0` | `0.1.1` → `0.2.0` |
| **Breaking Change** | `0.MINOR++.0` | `0.2.0` → `0.3.0` |

**Erster Release:**
```python
APP_VERSION = "1.0.0"  # Produktiver Einsatz
```

#### Nach 1.0.0 (Production)
| Änderung | Neue Version | Beispiel |
|----------|--------------|----------|
| **Bugfix** (nur Code) | `x.y.PATCH++` | `1.2.3` → `1.2.4` |
| **Neues Feature** (abwärtskompatibel) | `x.MINOR++.0` | `1.2.4` → `1.3.0` |
| **Breaking Change** (DB-Schema, API-Änderung) | `MAJOR++.0.0` | `1.3.0` → `2.0.0` |

---

### Export-Schema-Version hochzählen

**NUR bei Änderungen der CSV/Excel-Export-Struktur!**

| Änderung | Neue Version | Beispiel |
|----------|--------------|----------|
| **Neue Spalte hinzugefügt** (kompatibel) | `x.MINOR++` | `1.0` → `1.1` |
| **Spalte umbenannt/entfernt** (inkompatibel) | `MAJOR++.0` | `1.1` → `2.0` |

**Wichtig:** Alte Exporte müssen noch importierbar sein!

---

## Schritt-für-Schritt: Version ändern

### Beispiel: Bugfix (0.1.0 → 0.1.1)

1. **Code anpassen** (z.B. CSRF-Token-Fix)

2. **Version in `version.py` hochzählen:**
   ```python
   # version.py
   APP_VERSION = "0.1.1"  # PATCH hochgezählt
   EXPORT_SCHEMA_VERSION = "1.0"  # Unverändert (Export nicht betroffen)
   
   # Kommentar-Historie aktualisieren:
   # - 0.1.1 (2026-02-08): CSRF-Token-Fix für Export
   # - 0.1.0 (2026-02-07): Initial Release
   ```

3. **README aktualisieren:**
   ```markdown
   **Version:** 0.1.1 (Pre-Release)
   ```

4. **Changelog in README erweitern:**
   ```markdown
   **0.1.1** (2026-02-08) - Bugfix
   - 🐛 CSRF-Token für Export-Formulare repariert
   
   **0.1.0** (2026-02-07) - Initial Pre-Release
   - ✅ Export/Import-Funktion mit Schema-Versionierung
   ```

5. **Git Commit:**
   ```bash
   git add version.py README.md
   git commit -m "chore: Bump version to 0.1.1 (CSRF-Token fix)"
   git tag v0.1.1
   git push --tags
   ```

---

### Beispiel: Neues Feature (0.1.1 → 0.2.0)

1. **Feature implementiert** (z.B. Email-Feld für Teilnehmer)

2. **Datenbank-Migration:**
   ```bash
   flask db migrate -m "Add email field to participants"
   flask db upgrade
   ```

3. **Export erweitert (neue Spalte):**
   ```python
   # data_io.py
   participant_export = {
       # ...
       "Email": participant.email or "",  # Neu!
   }
   ```

4. **Beide Versionen hochzählen:**
   ```python
   # version.py
   APP_VERSION = "0.2.0"  # MINOR hochgezählt (neues Feature)
   EXPORT_SCHEMA_VERSION = "1.1"  # MINOR hochgezählt (neue Spalte)
   
   # Historie:
   # - 0.2.0 (2026-02-10): Email-Feld hinzugefügt
   # Schema-Historie:
   # - 1.1 (2026-02-10): Email-Spalte hinzugefügt (kompatibel)
   ```

5. **Import-Logik erweitern (für alte Exporte):**
   ```python
   # data_import.py
   def _import_schema_v1_0(df):
       # ALT: Schema v1.0 ohne Email
       participant.email = None
   
   def _import_schema_v1_1(df):
       # NEU: Schema v1.1 mit Email
       participant.email = row.get('Email', None)
   
   # In import_participants_from_export():
   if schema_version == "1.0":
       return _import_schema_v1_0(df)
   elif schema_version == "1.1":
       return _import_schema_v1_1(df)
   ```

6. **README & Commit (wie oben)**

---

## Export-Schema-Änderungen: Best Practices

### ✅ Kompatible Änderungen (MINOR++)
- Neue Spalten hinzufügen
- Bestehende Spalten beibehalten
- Import-Logik: Fallback für fehlende Spalten

```python
# Alte Exporte funktionieren weiter
participant.email = row.get('Email', None) or ""  # ← Fallback
```

### ❌ Inkompatible Änderungen (MAJOR++)
- Spalten umbenennen
- Spalten entfernen
- Datentyp ändern (String → Number)

**Dann:** Neue Import-Funktion schreiben, die alte Struktur konvertiert!

```python
def _import_schema_v1_0(df):
    # ALT: "Leitung" (eine Spalte)
    leitung = row.get('Leitung', '')
    group.leitung_fremdeinschatzung = leitung

def _import_schema_v2_0(df):
    # NEU: "Leitung (Fremd)" + "Leitung (Selbst)" (zwei Spalten)
    group.leitung_fremdeinschatzung = row.get('Leitung (Fremd)', '')
    group.leitung_selbsteinschatzung = row.get('Leitung (Selbst)', '')
```

---

## Automatisierung (für später)

Aktuell: **Manuell** in `version.py` ändern.

**Optional:** CLI-Tool für automatisches Version-Bump:

```bash
# Zukünftig möglich:
flask version bump patch   # 0.1.0 → 0.1.1
flask version bump minor   # 0.1.1 → 0.2.0
flask version bump export-minor  # Export-Schema 1.0 → 1.1
```

---

## FAQ

**Q: Muss ich bei jedem Commit die Version ändern?**  
A: Nein! Nur bei:
- Neuen Features (MINOR)
- Bugfixes die deployed werden (PATCH)
- Breaking Changes (MAJOR)

**Q: Was ist mit Git-Tags?**  
A: Empfohlen! Erstelle einen Tag pro Version:
```bash
git tag v0.1.0
git push --tags
```

**Q: Wie erkenne ich welche Version läuft?**  
A: Im Footer der App steht: `Version 0.1.0`

**Q: Was wenn ich die Version vergesse zu ändern?**  
A: Nicht schlimm im Pre-Release! Nach 1.0.0 solltest du aber konsequent sein.

---

## Weiterführende Infos

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Flask-Migrate Dokumentation](https://flask-migrate.readthedocs.io/)
---

## Versions-Historie

### v0.4.0 (2026-02-08) - Report-Konfiguration & Backup-System
**Neue Features:**
- ✅ Report-Konfiguration UI mit Tailwind CSS Accordions
- ✅ Backup-System für SQLite-Datenbank (automatisch + manuell)
- ✅ Prompts-Export als JSON mit Metadaten
- ✅ Retention-Management für Backups (max. 50)
- ✅ Default-Prompts-Loader (`load_default_prompts.py`)
- ✅ Prompt-Unique-Constraint Migration

**Bugfixes:**
- 🐛 CSRF-Token in Report-Konfiguration behoben
- 🐛 Verschachtelte Forms in Configure-Template entfernt
- 🐛 Unterschriften-Upload in Abschlussblatt-Bereich integriert

**Breaking Changes:** Keine

---

### v0.3.0 (2026-02-07) - Test-Suite & CI/CD
**Neue Features:**
- ✅ 91 Tests (Unit + Integration), 46.90% Coverage
- ✅ GitHub Actions Workflows (Tests, Code Quality)
- ✅ ReportGenerator Service mit Sidebar-Layout
- ✅ HTML-Vorschau mit iframe-Isolation
- ✅ Standalone-Routes für SE/FE-PDFs

**Bugfixes:** -

**Breaking Changes:** Keine

---

### v0.2.0 (2026-02-07) - Report-System
**Neue Features:**
- ✅ ReportGenerator Service
- ✅ WeasyPrint PDF-Export
- ✅ Template-System für flexible Reports
- ✅ Signature-Image-Model

**Bugfixes:** -

**Breaking Changes:** Keine

---

### v0.1.0 (2026-01-31) - Initial Pre-Release
**Neue Features:**
- ✅ Export/Import mit Schema-Versionierung
- ✅ CSRF-Schutz für alle Formulare
- ✅ Modernisiertes UI (Tailwind CSS)
- ✅ Datenbank-Migrationen

**Bugfixes:** -

**Breaking Changes:** -