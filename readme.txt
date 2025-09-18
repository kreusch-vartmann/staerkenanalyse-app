# Timo's Stärkenanalysetool

> **Hinweis:** Dieses Tool befindet sich in der aktiven Entwicklung und ist noch nicht für den produktiven Einsatz bereit. Es dient als Prototyp und kann Fehler enthalten.

## Projektbeschreibung
Timo's Stärkenanalysetool ist eine lokal laufende Webanwendung, die den Prozess der Stärkenanalyse basierend auf Assessment-Center-Beobachtungen automatisiert. Die Anwendung ermöglicht es, Teilnehmerdaten und Beobachtungen zu verwalten, KI-gestützt Berichte zu erstellen und die Ergebnisse als standardisierte HTML-Dokumente zu exportieren.

Die Anwendung nutzt fortschrittliche Sprachmodelle wie Mistral AI oder Google Gemini, um qualitative Beobachtungsdaten in strukturierte, stärkebasierte Berichte zu übersetzen.

## Funktionen
- **Gruppen- & Teilnehmerverwaltung**: Hinzufügen, Bearbeiten und Löschen von Gruppen und Teilnehmern.
- **KI-gestützte Analyse**: Verarbeitung von Beobachtungsdaten mithilfe von KI-Modellen.
- **Flexibler Prompting-Ansatz**: Möglichkeit, Prompts und zusätzliche Dokumente (z. B. PDF, DOCX) für eine präzisere Analyse bereitzustellen.
- **Lokale Datenspeicherung**: Alle sensiblen Daten werden lokal in einer `data.json`-Datei gespeichert.

## Installation
### 1. Projekt klonen
```bash
git clone [https://github.com/dein-benutzername/timo-staerkenanalysetool.git](https://github.com/dein-benutzername/timo-staerkenanalysetool.git)
cd timo-staerkenanalysetool

### 2. Virtuelle Umgebung einrichten
python -m venv venv
source venv/bin/activate  # macOS/Linux
.\venv\Scripts\activate   # Windows

### 3. Abhängigkeiten installieren
pip install -r requirements.txt

### 4. API Schlüssel konigurieren.
Ordner .env im Hauptverzeichnis des Projekts anlegen.
GOOGLE_API_KEY=IHR_SCHLUESSEL_HIER
MISTRAL_API_KEY=IHR_SCHLUESSEL_HIER

### 5. Anwendung starten
python app.py -> Die Anwendung wird im Browser unter http://127.0.0.1:5001 verfügbar sein.

#### Mitwirkung
Timo Kreusch-Vartmann
timo@kreusch-vartmann.de

Dieses Programm wurde mit Unterstützung von künstlicher Intelligenz (Google Gemini, Mistral AI) umgesetzt.