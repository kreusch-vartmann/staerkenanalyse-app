"""
Datenbankmodul für die Stärkenanalyse-Anwendung.

Verwaltet die Verbindung und alle Abfragen zur SQLite-Datenbank.
"""
import sqlite3
import json
import os
from math import ceil
from flask import g

# FINALE KORREKTUR 1: Absoluter Pfad zur Datenbank, um sicherzustellen, dass immer die richtige Datei gefunden wird.
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(APP_ROOT, 'database.db')

PER_PAGE = 10  # Definiert, wie viele Einträge pro Seite angezeigt werden

# --- Dashboard Statistik-Funktionen ---

def get_dashboard_stats():
    """Holt die aggregierten Statistiken für das Dashboard."""
    db_conn = get_db()
    
    total_groups = db_conn.execute("SELECT COUNT(id) FROM groups").fetchone()[0]
    total_participants = db_conn.execute("SELECT COUNT(id) FROM participants").fetchone()[0]
    
    completed_analyses = db_conn.execute(
        "SELECT COUNT(id) FROM participants WHERE ki_texts IS NOT NULL AND ki_texts != '{}'"
    ).fetchone()[0]

    return {
        'total_groups': total_groups,
        'total_participants': total_participants,
        'completed_analyses': completed_analyses
    }

def get_recently_updated_participants(limit=5):
    """Holt die zuletzt bearbeiteten Teilnehmer."""
    query = """
        SELECT p.id, p.name, g.name as group_name
        FROM participants p
        JOIN groups g ON p.group_id = g.id
        ORDER BY p.updated_at DESC
        LIMIT ?
    """
    return query_db(query, (limit,))

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

def get_paginated_groups(page, per_page=10):
    """Holt eine paginierte Liste aller Gruppen."""
    offset = (page - 1) * per_page
    db = get_db()
    groups = db.execute(
        'SELECT * FROM groups ORDER BY name LIMIT ? OFFSET ?', (per_page, offset)
    ).fetchall()
    total_groups = db.execute('SELECT COUNT(id) FROM groups').fetchone()[0]
    
    # KORREKTUR: Ersetzt die nicht definierte Pagination-Klasse durch ein Dictionary,
    # konsistent mit get_paginated_participants.
    pagination = {
        'page': page,
        'pages': int(ceil(total_groups / per_page)) if per_page > 0 else 0,
        'total_items': total_groups,
        'has_prev': page > 1,
        'has_next': page * per_page < total_groups,
        'prev_num': page - 1,
        'next_num': page + 1
    }
    return pagination, groups

def get_paginated_participants(page, search_query, sort_order, per_page=10):
    """Holt eine paginierte, durchsuchbare und sortierbare Liste aller Teilnehmer."""
    offset = (page - 1) * per_page
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
    args.extend([per_page, offset])

    total_items = query_db(count_base_query, tuple(count_args), one=True)[0]
    participants = query_db(base_query, tuple(args))

    pagination = {
        'page': page,
        'pages': int(ceil(total_items / per_page)),
        'total_items': total_items,
        'has_prev': page > 1,
        'has_next': page * per_page < total_items,
        'prev_num': page - 1,
        'next_num': page + 1
    }
    return pagination, participants

# --- Getter-Funktionen ---

def get_all_groups():
    """Holt alle Gruppen (nicht paginiert) aus der Datenbank."""
    # FINALE KORREKTUR 3: Alle relevanten Spalten explizit abfragen
    return query_db('SELECT id, name, date, location, leitung, beobachter1, beobachter2, created_at FROM groups ORDER BY name ASC')

def get_group_by_id(group_id):
    """Holt eine einzelne Gruppe anhand ihrer ID."""
    # FINALE KORREKTUR 4: Explizite Spaltenauswahl statt 'SELECT *'
    return query_db('SELECT id, name, date, location, leitung, beobachter1, beobachter2, created_at FROM groups WHERE id = ?', (group_id,), one=True)

def get_participant_by_id(participant_id):
    """Holt einen Teilnehmer und parst alle JSON-Felder korrekt."""
    participant_row = query_db(
        'SELECT * FROM participants WHERE id = ?', (participant_id,), one=True
    )
    if not participant_row:
        return None

    participant = dict(participant_row)
    json_columns = ['general_data', 'observations', 'sk_ratings', 'vk_ratings', 'ki_texts', 'ki_raw_response', 'footer_data']    
    for key, value in participant.items():
        if key in json_columns:
            try:
                if value and isinstance(value, str) and value.strip():
                    participant[key] = json.loads(value)
                else:
                    participant[key] = {}
            except (json.JSONDecodeError, TypeError):
                participant[key] = {}
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

def add_group_and_get_id(name, date=None, location=None, leitung=None, beobachter1=None, beobachter2=None):
    """Fügt eine neue Gruppe hinzu und gibt die ID der neuen Gruppe zurück."""
    db_conn = get_db()
    cursor = db_conn.cursor()
    cursor.execute(
        (
            'INSERT INTO groups (name, date, location, leitung, beobachter1, beobachter2) '
            'VALUES (?, ?, ?, ?, ?, ?)'
        ),
        (name, date, location, leitung, beobachter1, beobachter2)
    )
    new_group_id = cursor.lastrowid
    db_conn.commit()
    return new_group_id

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

def add_multiple_participants_to_group(group_id, names):
    """Fügt eine Liste von neuen Teilnehmern zu einer Gruppe hinzu."""
    db_conn = get_db()
    cursor = db_conn.cursor()
    empty_json = json.dumps({})
    
    participants_to_add = []
    for name in names:
        if name.strip():
            participants_to_add.append((
                group_id, name.strip(), empty_json, empty_json,
                json.dumps({"flexibility": 0.0, "team_orientation": 0.0,
                            "process_orientation": 0.0, "results_orientation": 0.0}),
                json.dumps({"flexibility": 0.0, "consulting": 0.0,
                            "objectivity": 0.0, "goal_orientation": 0.0}),
                empty_json, "{}", empty_json
            ))

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
        'UPDATE participants SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (new_name, participant_id)
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
    set_clause = ", ".join([f"{key} = ?" for key in updates.keys()]) + ", updated_at = CURRENT_TIMESTAMP"

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
    group_id = query_db('SELECT group_id FROM participants WHERE id = ?', (participant_id,), one=True)['group_id']
    set_clause_group = ", ".join([f"{key} = ?" for key in group_details.keys()])
    query_group = f"UPDATE groups SET {set_clause_group} WHERE id = ?"
    values_group = list(group_details.values()) + [group_id]
    db_conn.execute(query_group, tuple(values_group))

    footer_json = json.dumps(footer_data)
    db_conn.execute(
        'UPDATE participants SET footer_data = ? WHERE id = ?',
        (footer_json, participant_id)
    )
    db_conn.commit()
  
def get_all_participants_for_export():
    """
    Holt alle Teilnehmer mit zugehörigen Gruppendaten für den Export.
    """
    query = """
        SELECT
            p.id,
            g.name as group_name,
            g.date as group_date,
            g.location as group_location
        FROM participants p
        JOIN groups g ON p.group_id = g.id
        ORDER BY g.name, p.name
    """
    participant_rows = query_db(query)
    if not participant_rows:
        return []

    participants = []
    for row in participant_rows:
        clean_participant = get_participant_by_id(row['id'])
        if clean_participant:
            clean_participant['group_name'] = row['group_name']
            clean_participant['group_date'] = row['group_date']
            clean_participant['group_location'] = row['group_location']
            participants.append(clean_participant)

    return participants 

# --- Prompt Management Funktionen ---

def get_all_prompts():
    """Holt alle Prompts, sortiert nach Name."""
    return query_db("SELECT * FROM prompts ORDER BY name ASC")

def get_prompt_by_id(prompt_id):
    """Holt einen einzelnen Prompt anhand seiner ID."""
    return query_db("SELECT * FROM prompts WHERE id = ?", (prompt_id,), one=True)

def add_prompt(name, description, content):
    """Fügt einen neuen Prompt zur Datenbank hinzu."""
    db_conn = get_db()
    db_conn.execute(
        "INSERT INTO prompts (name, description, content, created_at, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        (name, description, content)
    )
    db_conn.commit()

def update_prompt(prompt_id, name, description, content):
    """Aktualisiert einen bestehenden Prompt."""
    db_conn = get_db()
    db_conn.execute(
        "UPDATE prompts SET name = ?, description = ?, content = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (name, description, content, prompt_id)
    )
    db_conn.commit()

def delete_prompt_by_id(prompt_id):
    """Löscht einen Prompt anhand seiner ID."""
    db_conn = get_db()
    db_conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
    db_conn.commit()

def get_all_participants():
    """Gibt alle Teilnehmer aus der Datenbank zurück."""
    db = get_db()
    participants = db.execute('SELECT * FROM participants ORDER BY name').fetchall()
    return [dict(row) for row in participants]  # Wichtig: Umwandlung in Dictionaries
