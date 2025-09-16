from flask import Flask, render_template

# Erstelle eine Instanz der Flask-Anwendung
app = Flask(__name__)

# Definiere eine Route für die Startseite (URL '/')
@app.route('/')
def home():
    # Gib die HTML-Vorlage zurück, die wir später erstellen
    return render_template('staerkenanalyse_bericht_vorlage3.html')

# Starte die Anwendung, wenn das Skript direkt ausgeführt wird
if __name__ == '__main__':
    # Aktiviere den Debug-Modus für die Entwicklung
    app.run(debug=True, host='0.0.0.0')