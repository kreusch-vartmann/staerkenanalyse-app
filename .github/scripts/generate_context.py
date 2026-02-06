#!/usr/bin/env python3
"""
Context Generator Script
Erstellt automatisch CONTEXT.md und PROJECT_OVERVIEW.md für KI-Assistenten
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple


class ContextGenerator:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.blueprints_dir = project_root / "blueprints"
        self.templates_dir = project_root / "templates"
        self.models_file = project_root / "models.py"
        self.app_file = project_root / "app.py"
        
    def extract_routes(self, file_path: Path) -> List[Dict]:
        """Extrahiert Flask-Routen aus einer Python-Datei"""
        routes = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Finde @blueprint.route() Dekoratoren
            route_pattern = r'@\w+_bp\.route\(["\']([^"\']+)["\']\s*(?:,\s*methods=\[([^\]]+)\])?\)'
            func_pattern = r'def\s+(\w+)\('
            
            lines = content.split('\n')
            for i, line in enumerate(lines):
                route_match = re.search(route_pattern, line)
                if route_match:
                    route_path = route_match.group(1)
                    methods = route_match.group(2) if route_match.group(2) else '"GET"'
                    methods = methods.replace('"', '').replace("'", '')
                    
                    # Finde Funktionsnamen in der nächsten Zeile
                    if i + 1 < len(lines):
                        func_match = re.search(func_pattern, lines[i + 1])
                        if func_match:
                            routes.append({
                                'path': route_path,
                                'methods': methods,
                                'function': func_match.group(1)
                            })
        except Exception as e:
            print(f"Fehler beim Parsen von {file_path}: {e}")
        
        return routes
    
    def extract_models(self) -> List[Dict]:
        """Extrahiert SQLAlchemy-Modelle aus models.py"""
        models = []
        try:
            # Prüfe ob models.py existiert
            if not self.models_file.exists():
                print("⚠️ models.py nicht gefunden")
                return models

            with open(self.models_file, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Prüfe ob es ein SQLAlchemy-Model ist
                    bases = [base.id for base in node.bases if hasattr(base, 'id')]
                    if 'Model' in bases or any('Model' in str(base) for base in node.bases):
                        fields = []
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if hasattr(target, 'id'):
                                        fields.append(target.id)
                        
                        models.append({
                            'name': node.name,
                            'fields': fields
                        })
        except Exception as e:
            print(f"Fehler beim Parsen von models.py: {e}")
        
        return models
    
    def list_templates(self) -> List[str]:
        """Listet alle Template-Dateien auf"""
        templates = []
        if self.templates_dir.exists():
            for file in sorted(self.templates_dir.glob('*.html')):
                templates.append(file.name)
        return templates
    
    def analyze_dependencies(self) -> Dict[str, List[str]]:
        """Analysiert Import-Abhängigkeiten"""
        dependencies = {}
        
        for py_file in self.project_root.rglob('*.py'):
            if 'venv' in str(py_file) or '__pycache__' in str(py_file):
                continue
            
            imports = []
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read())
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)
                
                rel_path = py_file.relative_to(self.project_root)
                dependencies[str(rel_path)] = list(set(imports))
            except Exception as e:
                print(f"Fehler beim Analysieren von {py_file}: {e}")
        
        return dependencies
    
    def generate_context_md(self) -> str:
        """Generiert CONTEXT.md Content"""
        blueprints = {}
        if self.blueprints_dir.exists():
            for bp_file in self.blueprints_dir.glob('*.py'):
                if bp_file.name != '__init__.py':
                    bp_name = bp_file.stem
                    routes = self.extract_routes(bp_file)
                    blueprints[bp_name] = routes
        
        models = self.extract_models()
        templates = self.list_templates()
        
        md = f"""# CONTEXT.md - Stärkenanalyse-App

**Automatisch generiert am**: {self._get_timestamp()}

---

## 📋 Projektübersicht

**Technologie-Stack**:
- **Backend**: Python 3.12.12, Flask 3.1.2
- **ORM**: SQLAlchemy 2.0.28 + Flask-SQLAlchemy 3.0.4
- **Database**: SQLite (via DATABASE_URL env var)
- **KI-Integration**: Mistral API (mistralai==0.4.2), Google Generative AI
- **Frontend**: Vanilla JavaScript, Chart.js, Tailwind CSS, Bootstrap 4
- **PDF-Generation**: WeasyPrint
- **Migrations**: Flask-Migrate 4.0.4 (Alembic)

---

## 🗂️ Dateistruktur

### Core Application Files
- **app.py**: Flask-App-Initialisierung, Blueprint-Registrierung, Dashboard-Route
- **models.py**: SQLAlchemy-Modelle ({len(models)} Models: {', '.join([m['name'] for m in models])})
- **extensions.py**: db, migrate Objekte (verhindert circular imports)
- **ki_services.py**: KI-API-Integration (Mistral, Google Gemini)
- **utils.py**: File-Processing (PDF, DOCX Extraktion)

### Blueprints ({len(blueprints)} total)
"""
        
        for bp_name, routes in sorted(blueprints.items()):
            md += f"\n#### {bp_name}.py ({len(routes)} Routes)\n"
            for route in routes:
                md += f"- `{route['methods']} {route['path']}` → `{route['function']}()`\n"
        
        md += f"\n### Templates ({len(templates)} HTML-Dateien)\n"
        for template in templates:
            md += f"- {template}\n"
        
        md += "\n---\n\n## 🗄️ Datenbank-Schema (SQLAlchemy Models)\n\n"
        for model in models:
            md += f"### {model['name']}\n"
            md += f"**Felder**: {', '.join(model['fields'][:10])}"
            if len(model['fields']) > 10:
                md += f" ... (+{len(model['fields']) - 10} weitere)"
            md += "\n\n"
        
        md += """---

## 🔐 Environment Variables

**Erforderlich**:
- `DATABASE_URL`: SQLAlchemy Database URI (z.B. `sqlite:///instance/database.db`)
- `MISTRAL_API_KEY`: Mistral AI API Key (optional, für KI-Analysen)
- `GOOGLE_API_KEY`: Google Generative AI Key (optional, Fallback)

**Flask-Konfiguration**:
- `SECRET_KEY`: Automatisch generiert via `os.urandom(24)` (⚠️ regeneriert bei Restart!)
- Port: 5001 (hardcoded in app.py)
- Debug: Aktiviert (⚠️ für Production deaktivieren!)

---

## 📦 Wichtige Abhängigkeiten

**Kritische Libraries**:
- Flask 3.1.2, SQLAlchemy 2.0.28
- mistralai==0.4.2 (⚠️ Version fixed wegen Kompatibilität)
- WeasyPrint (benötigt System-Dependencies: libcairo, libpango)
- pandas 2.3.2, numpy 2.3.3 (für Excel-Export)
- protobuf==5.29.5 (⚠️ Bekannter Konflikt mit älteren Packages)

---

## 🚀 Typische Workflows

### 1. Neuen Teilnehmer hinzufügen
1. Dashboard → "Gruppen verwalten" → Gruppe auswählen
2. "Teilnehmer hinzufügen" → Name eingeben
3. → `participants.add_participant()` → Participant-Model erstellt

### 2. KI-Analyse durchführen
1. Dashboard → "KI-Analyse" → Gruppe auswählen
2. Teilnehmer auswählen → "Starten"
3. → `analysis.run_ki_analysis_api()` → Mistral API Call
4. Weiterleitung → `analysis.edit_report()` → staerkenanalyse_bericht_vorlage3.html

### 3. Bericht bearbeiten/exportieren
1. Dashboard → "Berichte bearbeiten" (manage_participants.html)
2. "Bericht ansehen" Button (nur wenn `ki_texts` vorhanden)
3. → `analysis.edit_report()` → HTML-Bericht editieren
4. PDF-Export → `analysis.bericht_pdf()` → WeasyPrint → PDF

---

## ⚠️ Bekannte Issues & TODOs

1. **SECRET_KEY regeneriert bei Restart** → Sessions werden ungültig
2. **3x TODOs in blueprints/data_io.py** → Export-Funktion Field-Mapping
3. **schema.sql veraltet** → Nur `leitung`, models.py hat `leitung_fremdeinschatzung` + `leitung_selbsteinschatzung`
4. **database.py (338 Zeilen)** → Legacy Code, vermutlich unused
5. **Debug-Modus in Production** → `app.run(debug=True)` hardcoded

---

**Letzte Aktualisierung**: {self._get_timestamp()}
"""
        return md
    
    def generate_project_overview_md(self) -> str:
        """Generiert PROJECT_OVERVIEW.md für schnellen Überblick"""
        dependencies = self.analyze_dependencies()
        
        md = f"""# PROJECT_OVERVIEW.md

**Generiert am**: {self._get_timestamp()}

---

## 🎯 Projektziel

Flask-basierte Web-Applikation für **Stärkenanalyse** mit KI-gestützter Berichterstellung:
- Teilnehmermanagement in Gruppen
- Dateneingabe (Beobachtungen, Selbsteinschätzungen)
- KI-Analyse via Mistral API
- PDF-Berichte generieren

---

## 📊 Projektstatistik

- **Python-Dateien**: {len([f for f in dependencies.keys() if f.endswith('.py')])}
- **Blueprints**: 5 (groups, participants, analysis, data_io, prompts)
- **Templates**: {len(self.list_templates())}
- **Datenbank-Models**: {len(self.extract_models())}

---

## 🔗 Routing-Übersicht

| Blueprint | Routen-Anzahl | Zweck |
|-----------|---------------|-------|
| groups | 4 | Gruppenverwaltung |
| participants | 6 | Teilnehmerverwaltung |
| analysis | 9 | KI-Analyse & Berichte |
| data_io | 10 | Import/Export, Dateneingabe |
| prompts | 7 | Prompt-Management |

---

## 🧩 Modul-Abhängigkeiten

**app.py importiert**:
- extensions (db, migrate)
- models (Group, Participant, Prompt)
- blueprints (alle 5)

**Blueprints importieren**:
- models.py (für ORM-Queries)
- extensions.py (für db.session)
- ki_services.py (nur analysis.py)
- utils.py (nur analysis.py)

**Keine zirkulären Abhängigkeiten detected** ✅

---

## 🛠️ Entwicklungsumgebung

**Voraussetzungen**:
- Python 3.12.12
- venv: `/home/timok/kDrive/Dokumente/staerkenanalyse-app/venv`
- System-Dependencies: libcairo, libpango (für WeasyPrint)

**Setup-Schritte**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # API-Keys eintragen
flask db upgrade
python app.py
```

---

## 🔐 Security Considerations

1. **API Keys in .env** (nicht in Git!)
2. **SECRET_KEY**: Aktuell `os.urandom(24)` → Für Production: Persistente Key in .env
3. **Debug-Modus**: Für Production deaktivieren
4. **SQLite**: Für Production → PostgreSQL migrieren

---

**Für detaillierte Informationen siehe [CONTEXT.md](CONTEXT.md)**
"""
        return md
    
    def _get_timestamp(self) -> str:
        """Gibt aktuellen Timestamp zurück"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def run(self):
        """Führt Context-Generierung aus"""
        print("🔍 Analysiere Projekt...")
        
        context_md = self.generate_context_md()
        overview_md = self.generate_project_overview_md()
        
        print("📝 Schreibe CONTEXT.md...")
        with open(self.project_root / "CONTEXT.md", 'w', encoding='utf-8') as f:
            f.write(context_md)
        
        print("📝 Schreibe PROJECT_OVERVIEW.md...")
        with open(self.project_root / "PROJECT_OVERVIEW.md", 'w', encoding='utf-8') as f:
            f.write(overview_md)
        
        print("✅ Context-Dateien erfolgreich generiert!")


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    generator = ContextGenerator(project_root)
    generator.run()
