Timo's Stärkenanalysetool

    Status: Das Tool wurde erfolgreich auf eine robuste, modulare Architektur mit einer SQLite-Datenbank umgestellt. Es ist stabil und bereit für die Weiterentwicklung.

Projektbeschreibung

Timo's Stärkenanalysetool ist eine lokal laufende Webanwendung, die den Prozess der Stärkenanalyse basierend auf Assessment-Center-Beobachtungen automatisiert. Die Anwendung ermöglicht es, Teilnehmerdaten und Beobachtungen zu verwalten, KI-gestützt Berichte zu erstellen und die Ergebnisse als standardisierte HTML-Dokumente zu exportieren.

Die Anwendung wurde von einer einfachen JSON-basierten Speicherung auf eine sichere und effiziente SQLite-Datenbank umgestellt. Die Codebasis ist nun in logische Module (database.py, ki_services.py, utils.py) aufgeteilt, was die Wartung und zukünftige Erweiterungen erheblich vereinfacht.
Funktionen

    Gruppen- & Teilnehmerverwaltung: Übersichtliche Verwaltung von Gruppen und Teilnehmern mit Paginierung, Suche und Sortierung.

    KI-gestützte Analyse: Verarbeitung von Beobachtungsdaten mithilfe von Google Gemini oder Mistral AI.

    Flexibler Prompting-Ansatz: Möglichkeit, Prompts aus Textdateien zu laden und zusätzliche Dokumente (PDF, DOCX) für eine präzisere Analyse bereitzustellen.

    Lokale & sichere Datenspeicherung: Alle sensiblen Daten werden lokal in einer database.db-Datei gespeichert.

Installation & Setup
1. Projekt klonen & Abhängigkeiten installieren

git clone [URL_IHRES_PROJEKTS]
cd staerkenanalyse-app
python -m venv venv
source venv/bin/activate  # macOS/Linux | .\venv\Scripts\activate für Windows
pip install -r requirements.txt

2. API-Schlüssel konfigurieren

Erstellen Sie eine Datei namens .env im Hauptverzeichnis des Projekts und fügen Sie Ihre API-Schlüssel ein:

GOOGLE_API_KEY=IHR_GOOGLE_SCHLUESSEL
MISTRAL_API_KEY=IHR_MISTRAL_SCHLUESSEL

3. Datenbank einrichten

Führen Sie die folgenden Skripte in dieser Reihenfolge aus:

a) Datenbank-Struktur erstellen (nur beim allerersten Mal):

python init_db.py

Dies erstellt eine leere database.db-Datei mit den notwendigen Tabellen.

b) (Optional) Alte Daten migrieren:
Wenn Sie eine alte data.json-Datei mit bestehenden Daten haben, können Sie diese mit folgendem Befehl in die neue Datenbank importieren:

python migrate_data.py

4. Anwendung starten

python app.py

Die Anwendung ist nun unter http://127.0.0.1:5001 in Ihrem Browser verfügbar.
Mitwirkung

Timo Kreusch-Vartmann | timo@kreusch-vartmann.de

Dieses Programm wurde mit intensiver Unterstützung von künstlicher Intelligenz umgesetzt.

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz veröffentlicht. Weitere Informationen finden Sie in der Datei `LICENSE`.