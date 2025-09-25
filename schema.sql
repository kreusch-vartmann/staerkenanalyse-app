-- Löscht bestehende Tabellen, um einen sauberen Neuaufbau zu gewährleisten.
DROP TABLE IF EXISTS groups;
DROP TABLE IF EXISTS participants;

-- Erstellt die Tabelle für die Assessment-Gruppen.
CREATE TABLE groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date TEXT,
    location TEXT,
    leitung TEXT,
    beobachter1 TEXT,
    beobachter2 TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Erstellt die Tabelle für die Teilnehmer.
CREATE TABLE participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    general_data TEXT, -- JSON-String für allgemeine Daten
    observations TEXT, -- JSON-String für Beobachtungen
    sk_ratings TEXT,   -- JSON-String für Bewertungen der sozialen Kompetenzen
    vk_ratings TEXT,   -- JSON-String für Bewertungen der verbalen Kompetenzen
    ki_texts TEXT,     -- JSON-String für die von der KI generierten und vom User bearbeiteten Texte
    ki_raw_response TEXT, -- NEU: JSON-String für die rohe, unveränderte KI-Antwort
    footer_data TEXT,  -- JSON-String für Footer-Daten
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES groups (id)
);

-- Erstellt die Tabelle für die KI-Prompts.
CREATE TABLE prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);