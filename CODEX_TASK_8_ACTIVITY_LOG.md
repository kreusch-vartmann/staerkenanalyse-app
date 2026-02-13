# Codex Task 8: Activity-Log für "Zuletzt bearbeitet" auf dem Dashboard

## Ziel
Das Dashboard-Widget "Zuletzt bearbeitet" zeigt aktuell nur die 5 zuletzt aktualisierten Teilnehmer-Namen. Stattdessen soll ein Activity-Log die letzten Arbeitsschritte aller User anzeigen, z.B. "Hans Wurst — Fremdeinschätzung bearbeitet" mit klickbarem Link zurück zum jeweiligen Arbeitskontext.

## Projekt-Stack
- Python 3.12, Flask 2.x, SQLAlchemy 2.x, Flask-Login, Flask-Migrate (Alembic)
- Jinja2-Templates mit Tailwind CSS (indigo-600 als Primärfarbe)
- Alle `<script>`-Tags müssen `nonce="{{ csp_nonce }}"` enthalten
- Datenbank: SQLite (Entwicklung)

## Schritt 1: Neues Modell `ActivityLog` in `models.py`

Füge **am Ende** der Datei `models.py` (vor dem letzten Zeilenumbruch, nach der Klasse `LearnedPromptRule`) folgendes Modell ein:

```python
class ActivityLog(db.Model):
    """Protokolliert Benutzeraktionen für das Dashboard-Aktivitätsfeed."""
    __tablename__ = "activity_log"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # z.B. "fremdeinschätzung_bearbeitet"
    action_label = db.Column(db.String(200), nullable=False)  # Anzeige, z.B. "Fremdeinschätzung bearbeitet"
    entity_type = db.Column(db.String(50), nullable=False)  # "participant", "group", "task" etc.
    entity_id = db.Column(db.Integer, nullable=True)
    entity_label = db.Column(db.String(200), nullable=False)  # z.B. "Hans Wurst"
    target_url = db.Column(db.String(500), nullable=True)  # Link zum Arbeitskontext
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), index=True)

    user = db.relationship("User", backref="activity_logs")

    def __repr__(self):
        return f"<ActivityLog {self.action} by user {self.user_id}>"
```

## Schritt 2: Helper-Funktion in `utils.py`

Füge am Ende von `utils.py` hinzu:

```python
def log_activity(user_id, action, action_label, entity_type, entity_id, entity_label, target_url=None):
    """Erstellt einen ActivityLog-Eintrag. Fail-safe: Fehler werden geloggt aber nicht geworfen."""
    try:
        from models import ActivityLog
        from extensions import db
        entry = ActivityLog(
            user_id=user_id,
            action=action,
            action_label=action_label,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_label=entity_label,
            target_url=target_url,
        )
        db.session.add(entry)
        # Nicht committen — das macht der aufrufende Code
    except Exception as e:
        print(f"⚠️ ActivityLog fehlgeschlagen: {e}")
```

## Schritt 3: Migration erstellen und anwenden

```bash
cd /home/timok/kDrive/Dokumente/staerkenanalyse-app
source venv/bin/activate
flask db migrate -m "add_activity_log_table"
flask db upgrade
```

## Schritt 4: Activity-Logging an zentralen Stellen einfügen

### 4a: `blueprints/analysis.py`

In der Funktion `save_edited_report` (Route `/save_report`, ca. Zeile 340-400) — NACH dem erfolgreichen `db.session.commit()`:

```python
from utils import log_activity
from flask_login import current_user
# ... nach db.session.commit():
log_activity(
    user_id=current_user.id,
    action="report_edited",
    action_label="Bericht bearbeitet",
    entity_type="participant",
    entity_id=participant.id,
    entity_label=participant.name,
    target_url=url_for('analysis.edit_report', participant_id=participant.id),
)
db.session.commit()  # commit den ActivityLog-Eintrag
```

In der Funktion `execute_batch_ai_analysis` (Route `/ai_analysis/execute`, ca. Zeile 553) — **VOR** dem `return render_template`:

```python
for p in participants:
    log_activity(
        user_id=current_user.id,
        action="ki_analysis_started",
        action_label="KI-Analyse gestartet",
        entity_type="participant",
        entity_id=p.id,
        entity_label=p.name,
        target_url=url_for('analysis.edit_report', participant_id=p.id),
    )
db.session.commit()
```

### 4b: `blueprints/data_io.py`

In der Funktion, die Beobachtungsdaten speichert — nach erfolgreichem Commit:

```python
log_activity(
    user_id=current_user.id,
    action="data_entry_saved",
    action_label="Beobachtungsdaten erfasst",
    entity_type="participant",
    entity_id=participant.id,
    entity_label=participant.name,
    target_url=url_for('participants.show_data_entry', participant_id=participant.id),
)
db.session.commit()
```

### 4c: `blueprints/groups.py`

In `add_group` (Route `/group/add`, POST) — nach Commit:

```python
log_activity(
    user_id=current_user.id,
    action="group_created",
    action_label="Gruppe erstellt",
    entity_type="group",
    entity_id=new_group.id,
    entity_label=new_group.name,
    target_url=url_for('groups.show_group_participants', group_id=new_group.id),
)
db.session.commit()
```

### 4d: `blueprints/participants.py`

In `add_participant` — nach Commit:

```python
log_activity(
    user_id=current_user.id,
    action="participant_added",
    action_label="Teilnehmer hinzugefügt",
    entity_type="participant",
    entity_id=new_participant.id,
    entity_label=new_participant.name,
    target_url=url_for('participants.show_data_entry', participant_id=new_participant.id),
)
db.session.commit()
```

## Schritt 5: Dashboard-Route in `app.py` anpassen

In der Funktion `dashboard()` (ca. Zeile 163-222):

**Ersetze** die `recently_updated`-Query (ca. Zeile 179-185):
```python
recently_updated = db.session.scalars(
    db.select(models.Participant)
    .order_by(models.Participant.updated_at.desc())
    .limit(5)
).all()
```

**Durch:**
```python
recent_activities = db.session.scalars(
    db.select(models.ActivityLog)
    .order_by(models.ActivityLog.created_at.desc())
    .limit(10)
).all()
```

**Ersetze** im `return render_template(...)` (ca. Zeile 217-222):
```python
recently_updated_participants=recently_updated,
```
**Durch:**
```python
recent_activities=recent_activities,
```

## Schritt 6: Dashboard-Template `templates/dashboard.html` anpassen

**Ersetze** den Block "Zuletzt bearbeitet" (ca. Zeile 46-58):

```html
<h3 class="text-lg font-semibold text-gray-900 mb-3">Zuletzt bearbeitet</h3>
{% if recently_updated_participants %}
    <ul class="space-y-2">
        {% for participant in recently_updated_participants %}
        <li class="text-sm">
            <a href="{{ url_for('participants.show_data_entry', participant_id=participant.id) }}" class="text-indigo-600 hover:underline">
                <strong>{{ participant.name }}</strong>
            </a>
            <span class="text-gray-500 block">in Gruppe: {{ participant.group_name }}</span>
        </li>
        {% endfor %}
    </ul>
{% else %}
    <p class="text-sm text-gray-500">Noch keine Teilnehmer bearbeitet.</p>
{% endif %}
```

**Durch:**
```html
<h3 class="text-lg font-semibold text-gray-900 mb-3">Letzte Aktivitäten</h3>
{% if recent_activities %}
    <ul class="space-y-2">
        {% for activity in recent_activities %}
        <li class="text-sm flex items-start gap-2">
            <span class="text-gray-400 text-xs mt-0.5 whitespace-nowrap">{{ activity.created_at.strftime('%d.%m. %H:%M') }}</span>
            <div>
                {% if activity.target_url %}
                    <a href="{{ activity.target_url }}" class="text-indigo-600 hover:underline font-medium">{{ activity.entity_label }}</a>
                {% else %}
                    <span class="font-medium text-gray-900">{{ activity.entity_label }}</span>
                {% endif %}
                <span class="text-gray-500">— {{ activity.action_label }}</span>
                {% if activity.user %}
                    <span class="text-gray-400 text-xs">({{ activity.user.full_name }})</span>
                {% endif %}
            </div>
        </li>
        {% endfor %}
    </ul>
{% else %}
    <p class="text-sm text-gray-500">Noch keine Aktivitäten vorhanden.</p>
{% endif %}
```

## Validierung
1. `flask db migrate -m "add_activity_log_table"` → Migration wird erstellt
2. `flask db upgrade` → Tabelle wird angelegt
3. Server starten: `flask run --port 5002` → Keine Fehler
4. Dashboard aufrufen → zeigt leeren Aktivitäts-Feed
5. Beliebige Aktion durchführen (z.B. Gruppe erstellen) → Eintrag erscheint im Feed

## Wichtige Hinweise
- **Immer** `db.session.commit()` NACH dem `log_activity()`-Aufruf verwenden
- `log_activity` ist fail-safe (fängt Exceptions ab), damit die Hauptaktionen nie durch Logging fehlschlagen
- `target_url` muss mit `url_for()` generiert werden, NICHT hardcoded
- Alle Template-Änderungen müssen Tailwind CSS-Klassen verwenden (indigo als Primärfarbe)
- Alle `<script>`-Tags brauchen `nonce="{{ csp_nonce }}"`
