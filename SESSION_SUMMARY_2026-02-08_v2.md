# Session-Zusammenfassung — 08. Februar 2026 (Teil 2)

## Was passiert ist

Während einer vorherigen Session zur Datenbank-Reparatur wurde die **root-level `database.db`** gelöscht, die die wertvollen **KI-Prompts** (MistralSozVerb4 etc.) enthielt — Ergebnis hunderter Testiterationen. Diese Prompts existierten **ausschließlich in der SQLite-Datenbank** und waren weder in Git noch anderswo gesichert.

### Wiederherstellungs-Versuche (alle gescheitert)

| Quelle | Ergebnis |
|--------|----------|
| kDrive Papierkorb (2x `database.db`) | Beide identisch, nur heutige Standard-Prompts (MD5: `1395cbab...`) |
| kDrive `database(1).db` | Nur leere `alembic_version`-Tabelle |
| kDrive Versionsverlauf | Nur Versionen ab heute 08:36 |
| Git-Historie | DB war in `.gitignore`, nie versioniert |
| Docker PostgreSQL (neu) | Leere Prompts-Tabelle |
| Docker PostgreSQL (alt, 4 Monate) | 0 Prompts |
| VS Code Snap Trash | 2 DBs von September 2025 (vor Prompts-Tabelle) |
| BTRFS Snapshots | Keine Snapshot-Tools installiert |

### Ursache

- App wurde von `sqlite:///app.db` auf `sqlite:///database.db` umgestellt
- Die `.env`-Datei wurde heute um 08:33 geändert
- Die alte `database.db` im Projekt-Root wurde gelöscht
- Eine neue `instance/database.db` wurde um 08:36 erstellt (enthält nur 7 Standard-Prompts)

## Was implementiert wurde

### 1. Automatisches Backup-System (`backup_database.py`)

Neues Modul mit folgenden Funktionen:

- **`flask backup-db`** — Manuelles Backup der Datenbank
  - Erstellt Kopie in `backups/database_YYYYMMDD_HHMMSS_reason.db`
  - Option `--keep N` für Rotation (Standard: 50 Backups)
- **`flask export-prompts`** — Exportiert alle Prompts als:
  - Einzelne `.txt`-Dateien (pro Prompt)
  - Gesamt-`alle_prompts.json` mit allen Metadaten
  - Gespeichert in `backups/prompts_export/export_YYYYMMDD_HHMMSS/`
- **`flask restore-db [datei]`** — Stellt DB aus Backup wieder her
  - Zeigt verfügbare Backups zur Auswahl
  - Erstellt Sicherheitsbackup vor dem Restore
- **Automatisches Startup-Backup** — Bei jedem App-Start wird geprüft, ob sich die DB geändert hat, und ggf. ein Backup erstellt

### 2. Integration in `app.py`

- `register_backup_commands(app)` registriert die CLI-Befehle
- `startup_backup()` wird beim ersten Request automatisch ausgeführt
- Fehler beim Backup stoppen die App NICHT (try/except mit Warning)

### 3. `.gitignore`-Anpassung

- `backups/*.db` wird ignoriert (DB-Kopien sind groß und binär)
- `backups/prompts_export/` wird **NICHT** ignoriert → Prompt-Exports werden in Git versioniert

## Aktueller Systemzustand

| Komponente | Status |
|------------|--------|
| App-Import | ✅ Funktioniert |
| `flask backup-db` | ✅ Getestet, Backup erstellt (112 KB) |
| `flask export-prompts` | ✅ 7 Prompts exportiert (JSON + TXT) |
| `flask restore-db` | ✅ Registriert, Hilfe funktioniert |
| Startup-Backup | ✅ Integriert in `_before_first_request` |
| Prompts-Dropdown | ✅ Zeigt 7 Standard-Prompts |

## Vorhandene Prompts (Standard)

1. Best Performing v1
2. Best Performing v2
3. Strukturierter Report
4. Strukturierter Report (JSON)
5. Strukturierter Report (Mistral)
6. Stärkenanalyse Final
7. Stärkenanalyse Original

**Die benutzerdefinierten MistralSozVerb4-Prompts sind verloren und müssen neu erstellt werden.**

Die Basis-Datei `prompts/structured_report_mistral.txt` kann als Ausgangspunkt dienen.

## Empfohlenes Vorgehen

### Sofort
1. **Nach jeder Prompt-Änderung**: `flask export-prompts` ausführen
2. **Git-Commit**: `git add backups/prompts_export/ && git commit -m "Prompt-Export"`
3. Neue Prompts erstellen (mit anderer KI) basierend auf `prompts/structured_report_mistral.txt`

### Regelmäßig
- `flask backup-db` vor größeren Änderungen
- `flask export-prompts` nach jeder Prompt-Bearbeitung
- Prompt-Exports in Git committen

### Langfristig
- BTRFS-Snapshots einrichten (z.B. Snapper): `sudo pacman -S snapper`
- Alternativ: `testdisk` installieren für Notfall-Recovery: `sudo pacman -S testdisk`

## Noch möglich: BTRFS-Daten-Recovery

Falls die alten Prompts doch noch auf der Festplatte liegen (BTRFS, 64% frei):

```bash
# Schnelltest — sucht nach dem String "MistralSozVerb" auf der Partition
sudo grep -boa 'MistralSozVerb' /dev/nvme0n1p2

# Wenn Treffer: testdisk installieren und Recovery versuchen
sudo pacman -S testdisk
sudo photorec /dev/nvme0n1p2
```

## Technische Details

- **DB-Pfad**: `instance/database.db` (114.688 Bytes)
- **Backup-Pfad**: `backups/` (Projekt-Root)
- **App-Port**: 5001 (lokal), 5000 (Docker)
- **Python**: 3.12.12, venv
- **Filesystem**: BTRFS auf `/dev/nvme0n1p2`
- **Cloud-Sync**: Infomaniak kDrive (DB wird mitgesynct)
