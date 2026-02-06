"""
Migrations-Script: Überträgt Daten aus der alten SQLite-Datenbank 
in die neue SQLAlchemy-Struktur.
"""

import sqlite3
from datetime import datetime
from app import app
from extensions import db
from models import Group, Participant, Prompt

def migrate_data():
    """Migriert alle Daten aus der alten database.db in die neue Struktur."""
    
    # Verbindung zur alten Datenbank
    old_db = sqlite3.connect('database.db')
    old_db.row_factory = sqlite3.Row  # Ermöglicht Zugriff per Spaltenname
    cursor = old_db.cursor()
    
    with app.app_context():
        print("🔄 Starte Datenmigration...")
        
        # 1. Prompts migrieren
        print("\n📝 Migriere Prompts...")
        cursor.execute("SELECT * FROM prompts ORDER BY id")
        prompts_data = cursor.fetchall()
        prompts_count = 0
        
        for row in prompts_data:
            # Prüfen ob Prompt bereits existiert
            existing = db.session.get(Prompt, row['id'])
            if not existing:
                prompt = Prompt(
                    id=row['id'],
                    name=row['name'],
                    description=row['description'],
                    content=row['content']
                )
                db.session.add(prompt)
                print(f"  ✓ Prompt '{row['name']}' hinzugefügt")
                prompts_count += 1
            else:
                print(f"  ⊘ Prompt '{row['name']}' existiert bereits, überspringe")
        
        db.session.commit()
        print(f"✅ {prompts_count} neue Prompts migriert")
        
        # 2. Groups migrieren
        print("\n👥 Migriere Gruppen...")
        cursor.execute("SELECT * FROM groups ORDER BY id")
        groups_data = cursor.fetchall()
        groups_count = 0
        
        for row in groups_data:
            existing = db.session.get(Group, row['id'])
            if not existing:
                # Parse date if exists
                group_date = None
                if row['date']:
                    try:
                        group_date = datetime.strptime(row['date'], '%Y-%m-%d').date()
                    except:
                        pass
                
                group = Group(
                    id=row['id'],
                    name=row['name'],
                    date=group_date,
                    location=row['location'],
                    leitung_fremdeinschatzung=row['leitung'],  # ALT → NEU Mapping
                    leitung_selbsteinschatzung=None,  # Bleibt leer für alte Daten
                    beobachter1=row['beobachter1'],
                    beobachter2=row['beobachter2']
                )
                db.session.add(group)
                print(f"  ✓ Gruppe '{row['name']}' hinzugefügt")
                groups_count += 1
            else:
                print(f"  ⊘ Gruppe '{row['name']}' existiert bereits, überspringe")
        
        db.session.commit()
        print(f"✅ {groups_count} neue Gruppen migriert")
        
        # 3. Participants migrieren
        print("\n🧑 Migriere Teilnehmer...")
        cursor.execute("SELECT * FROM participants ORDER BY id")
        participants_data = cursor.fetchall()
        participants_count = 0
        
        for row in participants_data:
            existing = db.session.get(Participant, row['id'])
            if not existing:
                participant = Participant(
                    id=row['id'],
                    name=row['name'],
                    group_id=row['group_id'],
                    general_data=row['general_data'],
                    observations=row['observations'],
                    sk_ratings=row['sk_ratings'],
                    vk_ratings=row['vk_ratings'],
                    ki_texts=row['ki_texts'],
                    ki_raw_response=row['ki_raw_response'],
                    footer_data=row['footer_data']
                )
                db.session.add(participant)
                print(f"  ✓ Teilnehmer '{row['name']}' hinzugefügt")
                participants_count += 1
            else:
                print(f"  ⊘ Teilnehmer '{row['name']}' existiert bereits, überspringe")
        
        db.session.commit()
        print(f"✅ {participants_count} neue Teilnehmer migriert")
        
        print("\n" + "=" * 60)
        print("🎉 DATENMIGRATION ABGESCHLOSSEN!")
        print("=" * 60)
        print(f"Migriert: {prompts_count} Prompts, {groups_count} Gruppen, {participants_count} Teilnehmer")
        print("\nℹ️  Hinweis: self_assessments Tabelle bleibt für alte Gruppen leer.")
        print("   Diese können später manuell nachgepflegt werden.")
    
    old_db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("DATENMIGRATION: database.db → SQLAlchemy")
    print("=" * 60)
    print("\nDiese Migration wird:")
    print("- Alle Prompts übertragen")
    print("- Alle Gruppen übertragen (leitung → leitung_fremdeinschatzung)")
    print("- Alle Teilnehmer mit allen Daten übertragen")
    print("- Keine existierenden Daten überschreiben")
    print("\n")
    
    migrate_data()
