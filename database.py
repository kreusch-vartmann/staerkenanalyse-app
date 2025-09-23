"""
Datenbankmodul für die Stärkenanalyse-Anwendung.

Verwaltet die Verbindung und alle Abfragen zur SQLite-Datenbank.
"""
import sqlite3
import json
from math import ceil
from flask import g

DATABASE = 'database.db'
PER_PAGE = 10  # Definiert, wie viele Einträge pro Seite angezeigt werden

def get_db():
    """Öffnet eine neue DB-Verbindung oder gibt die bestehende aus dem Kontext zurück."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(_e=None):
    """Schließt die Datenbankverbindung am Ende des Requests."""
    db_conn = g.pop('db', None)
    if db_conn is not None:
        db_conn.close()

def query_db(query, args=(), one=False):
    """Führt eine Datenbankabfrage aus und gibt die Ergebnisse zurück."""
    cur = get_db().execute(query, args)
    results = cur.fetchall()
    cur.close()
    return (results[0] if results else None) if one else results

# --- Paginierungs- und Suchfunktionen ---

def get_paginated_groups(page=1):
    """Holt eine paginierte Liste von Gruppen."""
    offset = (page - 1) * PER_PAGE
    count_query = "SELECT COUNT(id) FROM groups"
    total_items = query_db(count_query, one=True)[0]

    query = "SELECT * FROM groups ORDER BY name ASC LIMIT ? OFFSET ?"
    groups = query_db(query, (PER_PAGE, offset))

    pagination = {
        'page': page,
        'pages': int(ceil(total_items / PER_PAGE)),
        'total_items': total_items,
        'has_prev': page > 1,
        'has_next': page * PER_PAGE < total_items,
        'prev_num': page - 1,
        'next_num': page + 1
    }
    return pagination, groups

def get_paginated_participants(page=1, search_query='', sort_order='name_asc'):
    """Holt eine paginierte, suchbare und sortierbare Liste von Teilnehmern."""
    offset = (page - 1) * PER_PAGE
    base_query = """
        SELECT p.id, p.name, g.name as group_name
        FROM participants p JOIN groups g ON p.group_id = g.id
    """
    count_base_query = (
        "SELECT COUNT(p.id) FROM participants p JOIN groups g ON p.group_id = g.id"
    )
    args = []
    count_args = []

    if search_query:
        search_term = f"%{search_query}%"
        base_query += " WHERE p.name LIKE ? OR g.name LIKE ?"
        count_base_query += " WHERE p.name LIKE ? OR g.name LIKE ?"
        args.extend([search_term, search_term])
        count_args.extend([search_term, search_term])

    sort_map = {
        'name_asc': 'p.name ASC',
        'name_desc': 'p.name DESC',
        'group_asc': 'g.name ASC, p.name ASC',
        'group_desc': 'g.name DESC, p.name ASC',
    }
    order_clause = sort_map.get(sort_order, 'p.name ASC')
    base_query += f" ORDER BY {order_clause} LIMIT ? OFFSET ?"
    args.extend([PER_PAGE, offset])

    total_items = query_db(count_base_query, tuple(count_args), one=True)[0]
    participants = query_db(base_query, tuple(args))

    pagination = {
        'page': page,
        'pages': int(ceil(total_items / PER_PAGE)),
        'total_items': total_items,
        'has_prev': page > 1,
        'has_next': page * PER_PAGE < total_items,
        'prev_num': page - 1,
        'next_num': page + 1
    }
    return pagination, participants

# --- Getter-Funktionen ---

def get_all_groups():
    """Holt alle Gruppen (nicht paginiert) aus der Datenbank."""
    return query_db('SELECT id, name FROM groups ORDER BY name ASC')

def get_group_by_id(group_id):
    """Holt eine einzelne Gruppe anhand ihrer ID."""
    return query_db('SELECT * FROM groups WHERE id = ?', (group_id,), one=True)

def get_participant_by_id(participant_id):
    """Holt einen Teilnehmer und parst alle JSON-Felder korrekt."""
    participant_row = query_db(
        'SELECT * FROM participants WHERE id = ?', (participant_id,), one=True
    )
    if not participant_row:
        return None

    participant = dict(participant_row)
    # Definierte Liste von Spalten, die JSON-Daten enthalten
    json_columns = ['general_data', 'observations', 'sk_ratings', 'vk_ratings', 'ki_texts', 'ki_raw_response', 'footer_data']    
    for key, value in participant.items():
        if key in json_columns:
            try:
                # Stellt sicher, dass der Wert ein String ist und nicht nur aus Leerzeichen besteht
                if value and isinstance(value, str) and value.strip():
                    participant[key] = json.loads(value)
                else:
                    participant[key] = {}  # Leeres Dict für None, leere Strings etc.
            except (json.JSONDecodeError, TypeError):
                participant[key] = {}  # Fallback bei ungültigem JSON
    return participant


def get_participants_by_group(group_id):
    """Holt alle Teilnehmer einer bestimmten Gruppe."""
    return query_db('SELECT * FROM participants WHERE group_id = ? ORDER BY name', (group_id,))

def get_prompt_by_name(prompt_name):
    """Holt einen Prompt aus einer Datei."""
    try:
        with open(f"prompts/{prompt_name}.txt", "r", encoding="utf-8") as f:
            return {"name": prompt_name, "content": f.read()}
    except FileNotFoundError:
        return None

# --- Setter/Writer-Funktionen ---

# pylint: disable=too-many-arguments
def add_group(name, date, location, leitung, beobachter1, beobachter2):
    """Fügt eine neue Gruppe zur Datenbank hinzu."""
    db_conn = get_db()
    db_conn.execute(
        (
            'INSERT INTO groups (name, date, location, leitung, beobachter1, beobachter2) '
            'VALUES (?, ?, ?, ?, ?, ?)'
        ),
        (name, date, location, leitung, beobachter1, beobachter2)
    )
    db_conn.commit()

def update_group_details(group_id, details):
    """Aktualisiert die Details einer Gruppe."""
    db_conn = get_db()
    set_clause = ", ".join([f"{key} = ?" for key in details.keys()])
    query = f"UPDATE groups SET {set_clause} WHERE id = ?"
    values = list(details.values()) + [group_id]
    db_conn.execute(query, tuple(values))
    db_conn.commit()

def delete_group_by_id(group_id):
    """Löscht eine Gruppe und alle zugehörigen Teilnehmer."""
    db_conn = get_db()
    db_conn.execute('DELETE FROM participants WHERE group_id = ?', (group_id,))
    db_conn.execute('DELETE FROM groups WHERE id = ?', (group_id,))
    db_conn.commit()

def add_participant_to_group(group_id, name):
    """Fügt einen neuen Teilnehmer zu einer Gruppe hinzu."""
    db_conn = get_db()
    empty_json = json.dumps({})
    db_conn.execute(
        (
            'INSERT INTO participants (group_id, name, general_data, observations, '
            'sk_ratings, vk_ratings, ki_texts, ki_raw_response, footer_data) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
        ),
        (
            group_id, name, empty_json, empty_json,
            json.dumps({"flexibility": 0.0, "team_orientation": 0.0,
                        "process_orientation": 0.0, "results_orientation": 0.0}),
            json.dumps({"flexibility": 0.0, "consulting": 0.0,
                        "objectivity": 0.0, "goal_orientation": 0.0}),
            empty_json, "{}", empty_json
        )
    )
    db_conn.commit()

def add_multiple_participants_to_group(group_id, names):
    """Fügt eine Liste von neuen Teilnehmern zu einer Gruppe hinzu."""
    db_conn = get_db()
    cursor = db_conn.cursor()
    empty_json = json.dumps({})
    
    # Bereite die Daten für das Einfügen vor
    participants_to_add = []
    for name in names:
        # Ignoriere leere Zeilen
        if name.strip():
            participants_to_add.append((
                group_id, name.strip(), empty_json, empty_json,
                json.dumps({"flexibility": 0.0, "team_orientation": 0.0,
                            "process_orientation": 0.0, "results_orientation": 0.0}),
                json.dumps({"flexibility": 0.0, "consulting": 0.0,
                            "objectivity": 0.0, "goal_orientation": 0.0}),
                empty_json, "{}", empty_json
            ))

    # Führe das Einfügen für alle neuen Teilnehmer aus
    if participants_to_add:
        cursor.executemany(
            (
                'INSERT INTO participants (group_id, name, general_data, observations, '
                'sk_ratings, vk_ratings, ki_texts, ki_raw_response, footer_data) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
            ),
            participants_to_add
        )
        db_conn.commit()
    return len(participants_to_add)

def update_participant_name(participant_id, new_name):
    """Aktualisiert den Namen eines Teilnehmers."""
    db_conn = get_db()
    db_conn.execute(
        'UPDATE participants SET name = ? WHERE id = ?', (new_name, participant_id)
    )
    db_conn.commit()

def delete_participant_by_id(participant_id):
    """Löscht einen Teilnehmer anhand seiner ID."""
    db_conn = get_db()
    db_conn.execute('DELETE FROM participants WHERE id = ?', (participant_id,))
    db_conn.commit()

def save_participant_data(participant_id, data_dict):
    """Speichert verschiedene JSON-Daten für einen Teilnehmer."""
    db_conn = get_db()
    updates = {key: json.dumps(value) for key, value in data_dict.items()}
    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])

    query = f"UPDATE participants SET {set_clause} WHERE id = ?"
    values = list(updates.values()) + [participant_id]
    db_conn.execute(query, tuple(values))
    db_conn.commit()

def update_observations(participant_id, social_obs, verbal_obs):
    """Speichert die Beobachtungen für einen Teilnehmer explizit."""
    db_conn = get_db()
    observations_json = json.dumps({'social': social_obs, 'verbal': verbal_obs})
    db_conn.execute(
        'UPDATE participants SET observations = ? WHERE id = ?',
        (observations_json, participant_id)
    )
    db_conn.commit()

def save_ki_raw_response(participant_id, raw_response):
    """Speichert die rohe Antwort der KI."""
    db_conn = get_db()
    db_conn.execute(
        'UPDATE participants SET ki_raw_response = ? WHERE id = ?',
        (raw_response, participant_id)
    )
    db_conn.commit()

def save_report_details(participant_id, group_details, footer_data):
    """Speichert aktualisierte Gruppen- und Fußzeilendetails."""
    db_conn = get_db()
    # Speichere die Gruppendetails in der 'groups' Tabelle
    group_id = query_db('SELECT group_id FROM participants WHERE id = ?', (participant_id,), one=True)['group_id']
    set_clause_group = ", ".join([f"{key} = ?" for key in group_details.keys()])
    query_group = f"UPDATE groups SET {set_clause_group} WHERE id = ?"
    values_group = list(group_details.values()) + [group_id]
    db_conn.execute(query_group, tuple(values_group))

    # Speichere die Fußzeilendaten in der 'participants' Tabelle
    footer_json = json.dumps(footer_data)
    db_conn.execute(
        'UPDATE participants SET footer_data = ? WHERE id = ?',
        (footer_json, participant_id)
    )
    db_conn.commit()