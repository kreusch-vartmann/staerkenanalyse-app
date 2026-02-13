# 🚀 WeasyPrint Setup Dokumentation

## Status ✅

**WeasyPrint ist jetzt voll funktionsfähig!**

- ✅ System-Bibliotheken installiert (pango, cairo, gdk-pixbuf2, libffi)
- ✅ Python venv mit WeasyPrint getestet (funktioniert!)
- ✅ PDF-Generierung bereit

## Wichtig: Korrekter Python-Interpreter

**Problem:** `flask run` nutzte Python aus **Anaconda** statt aus dem **venv**.

**Lösung:** Nutze das bereitgestellte Start-Script:

```bash
./run_dev.sh
```

Oder manuell:

```bash
source venv/bin/activate
flask run --port 5002
```

## PDF-Features

Jetzt funktionieren alle PDF-Routes:

| Route | Beschreibung |
|-------|--------------|
| `/reports/standalone/foreign-assessment/<id>/pdf` | Fremdeinschätzungs-PDF |
| `/reports/standalone/self-assessment/<id>/pdf` | Selbsteinschätzungs-PDF |
| `/reports/<group_id>/generate-pdf/<participant_id>` | Vollständiger Abschlussbericht |

## Troubleshooting

### PDF wird nicht generiert?

1. **Überprüfe ob Flask mit venv läuft:**
   ```bash
   source venv/bin/activate
   which python  # sollte .../venv/bin/python sein
   which flask   # sollte .../venv/bin/flask sein
   ```

2. **Teste WeasyPrint:**
   ```bash
   source venv/bin/activate
   python -c "from weasyprint import HTML; print('OK')"
   ```

3. **Starte Flask neu mit venv:**
   ```bash
   source venv/bin/activate
   flask run --port 5002
   ```

## System-Abhängigkeiten

Falls jemals Pango/Cairo problematisch, neu installieren:

```bash
sudo pacman -S pango cairo gdk-pixbuf2 libffi
```

## Requirements.txt

WeasyPrint ist bereits in `requirements.txt`:

```
weasyprint==66.0
```

Alle Abhängigkeiten sind installiert: `pip install -r requirements.txt`
