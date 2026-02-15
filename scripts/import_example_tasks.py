#!/usr/bin/env python
"""
Import EXAMPLE_TASKS als DB-Einträge mit is_example=True.
Damit stehen Referenzaufgaben in der gleichen Weise zur Verfügung wie benutzerdefinierte Aufgaben.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from models import Task, TaskVersion, User
from blueprints.observation_tasks import EXAMPLE_TASKS


def import_example_tasks():
    """Importiert EXAMPLE_TASKS als DB-Einträge."""
    with app.app_context():
        # Get or create admin user (should exist, but be safe)
        admin_user = db.session.scalar(
            db.select(User).where(User.email == "admin@testlocal.de")
        )
        
        if not admin_user:
            print("❌ Admin-User nicht gefunden! Bitte create_admin.py ausführen.")
            return
        
        imported_count = 0
        skipped_count = 0
        
        print("\n" + "="*70)
        print("🔍 IMPORTIERE REFERENZAUFGABEN")
        print("="*70)
        
        for task_key, task_data in EXAMPLE_TASKS.items():
            title = task_data["title"]
            
            # Prüfe ob Task bereits existiert
            existing = db.session.scalar(
                db.select(Task).where(Task.title == title, Task.is_example == True)
            )
            
            if existing:
                print(f"⏭️  '{title}' existiert bereits (ID: {existing.id})")
                skipped_count += 1
                continue
            
            # Erstelle neuen Task
            new_task = Task(
                title=title,
                description=task_data.get("task_description", "").strip(),
                notes=f"Beobachtungsfokus: {task_data.get('observation_focus', '')}",
                observation_area=task_data["observation_area"],
                participant_count=task_data.get("participant_count"),
                duration_minutes=task_data.get("duration_minutes"),
                is_active=True,
                is_example=True,  # ⭐ Markiert als Referenzaufgabe
                ki_model=None,  # Manuell erstellt, nicht KI-generiert
                created_by_id=admin_user.id
            )
            
            db.session.add(new_task)
            db.session.flush()  # Get ID for TaskVersion
            
            # Erstelle TaskVersion v1.0
            version = TaskVersion(
                task_id=new_task.id,
                version_number=1.0,
                content=task_data.get("task_description", "").strip(),
                change_notes="Initiale Version (Referenzaufgabe)",
                created_by_id=admin_user.id
            )
            
            db.session.add(version)
            db.session.flush()  # Get version ID
            
            # Setze current_version_id
            new_task.current_version_id = version.id
            
            db.session.commit()
            
            print(f"✅ '{title}' importiert (ID: {new_task.id}, Bereich: {task_data['observation_area']})")
            imported_count += 1
        
        print("\n" + "="*70)
        print(f"📊 ERGEBNIS:")
        print(f"   ✅ Importiert: {imported_count}")
        print(f"   ⏭️  Übersprungen: {skipped_count}")
        print(f"   📦 Gesamt: {imported_count + skipped_count}")
        print("="*70 + "\n")


if __name__ == "__main__":
    import_example_tasks()
