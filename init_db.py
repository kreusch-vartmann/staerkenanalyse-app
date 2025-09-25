# init_db.py
import sqlite3

# Stellt eine Verbindung zur Datenbank her (erstellt die Datei, wenn sie nicht existiert)
connection = sqlite3.connect('database.db')

# Öffnet die schema.sql-Datei und liest den Inhalt
with open('schema.sql') as f:
    # Führt das SQL-Skript aus, um die Tabellen zu erstellen
    connection.executescript(f.read())

# Schließt die Verbindung zur Datenbank
connection.close()

print("Datenbank wurde erfolgreich initialisiert.")