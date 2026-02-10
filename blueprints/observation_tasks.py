# blueprints/observation_tasks.py
"""
Beobachtungsaufgaben-Verwaltung für Assessment-Center.
Workflow: Beobachtungsbereich + Metadaten → KI generiert Aufgabenvorschlag → Editor + Chat-Iteration
"""

import json
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

from extensions import csrf, db
from ki_services import generate_task, refine_task_content
from models import Task, TaskVersion, User
from decorators import admin_required
from services import get_target_group_options

observation_tasks_bp = Blueprint("observation_tasks", __name__, url_prefix="/beobachtungsaufgaben")


# =============================================================================
# BEISPIEL-AUFGABEN (Hardcoded als References)
# =============================================================================

EXAMPLE_TASKS = {
    "erbengemeinschaft": {
        "title": "Diskussion Erbengemeinschaft",
        "observation_area": "Verbale Kompetenzen",
        "participant_count": 4,
        "duration_minutes": 40,
        "task_description": """
            <h2>Auftrag: Diskussion Erbengemeinschaft</h2>
            <h3>Eure Aufgabe</h3>
            <p>Ihr seid eine Erbengemeinschaft und habt ein Haus geerbt. Darin soll nun eine Wohnung neu vermietet werden.</p>
            <p><strong>Einigt euch in der Gruppe auf eine Mietpartei!</strong></p>
            
            <h3>Ablauf</h3>
            <ol>
                <li><strong>Vorbereitungsphase (10 Min):</strong> Jedes Gruppenmitglied legt für sich selbst eine Reihenfolge fest und notiert die Begründungen.</li>
                <li><strong>Diskussionsphase (30 Min):</strong> Jeder stellt seine Liste vor und begründet, warum er/sie der Mietpartei seiner/ihrer Wahl den Vorzug geben möchte. Diskutiert in der Gruppe alle Argumente, um zu einer einstimmigen Entscheidung zu kommen.</li>
                <li><strong>Abstimmungsphase:</strong> Führt eine Abstimmung durch. Wer abweichend von der ursprünglichen Position abstimmt, muss dies begründen.</li>
            </ol>
            
            <h3>Interessenten</h3>
            <ul>
                <li>Ein Künstlerehepaar aus Italien mit kleinem Hund</li>
                <li>Ein freiberuflich tätiger Journalist (6 Monate präsent)</li>
                <li>Eine Wohngemeinschaft aus 4 Azubis (Fachinformatik Siemens)</li>
                <li>Ein kinderloses berufstätiges Ehepaar mit Hund, religiös aktiv</li>
                <li>Eine alleinerziehende Mutter mit drei Kindern</li>
                <li>Ein wohlhabendes Rentnerehepaar (zieht wegen Lärm)</li>
            </ul>
        """,
        "observation_focus": "Argumentation, Überzeugungsfähigkeit, Kompromissfähigkeit, Moderationsfähigkeit, Umgang mit Konflikten",
        "is_example": True
    },
    "plakat": {
        "title": "Plakat-Gestaltung",
        "observation_area": "Soziale Kompetenzen",
        "participant_count": 4,
        "duration_minutes": 45,
        "task_description": """
            <h2>Auftrag: Plakat zur Gemeinde-Veranstaltung</h2>
            <h3>Aufgabenstellung</h3>
            <p>Das nächste Sommerfest eurer Gemeinde naht und ihr möchtet eure Gruppe und ihre Aktivitäten gut präsentieren. Zu diesem Zweck erstellt ihr ein Plakat.</p>
            <p>Um das Plakat zu erstellen, werden euch verschiedene Materialien und Werkzeuge zur Verfügung gestellt. Ein Flipchart-Papierbogen dient als Grundlage.</p>
            <p><strong>Das fertige Plakat wird zum Abschluss vorgestellt.</strong></p>
            
            <h3>Arbeitsanweisungen</h3>
            <ol>
                <li><strong>Planung (10 Min):</strong> Besprecht, was genau ihr auf dem Plakat präsentieren möchtet und wie ihr es grob umsetzen wollt.</li>
                <li><strong>Gestaltung (30 Min):</strong> Gestaltet das Plakat mit den zur Verfügung stehenden Materialien. Lasst eurer Phantasie gern freien Lauf.</li>
                <li><strong>Präsentation (5 Min):</strong> Stellt das fertige Plakat vor.</li>
            </ol>
            
            <h3>Verfügbare Materialien</h3>
            <p>Flipchart-Papier, Stifte, Kleber, Schere, bunte Papiere, Bilder, und weitere Gestaltungsmaterialien nach Verfügbarkeit.</p>
        """,
        "observation_focus": "Teamfähigkeit, Kreativität, Entscheidungsfähigkeit, Umsetzungs- und Zeiteinteilung, Kooperationsfähigkeit",
        "is_example": True
    }
}


# =============================================================================
# ROUTEN - AUFGABENVERWALTUNG
# =============================================================================

@observation_tasks_bp.route("/")
@login_required
@admin_required
def task_library():
    """Übersicht aller Beobachtungsaufgaben (mit Beispielen)."""
    page = request.args.get("page", 1, type=int)
    per_page = 10
    
    # Hole alle Aufgaben + Beispiele
    tasks = Task.query.filter_by(is_active=True).paginate(page=page, per_page=per_page)
    
    return render_template(
        "observation_tasks/library.html",
        tasks=tasks,
        example_tasks=EXAMPLE_TASKS,
        observation_areas=["Soziale Kompetenzen", "Verbale Kompetenzen"]
    )


@observation_tasks_bp.route("/neu", methods=["GET", "POST"])
@login_required
@admin_required
def create_task():
    """
    Schritt 1: Formular für neue Aufgabe
    Auswahl: Beobachtungsbereich, Teilnehmer, Dauer, Zielgruppe
    """
    if request.method == "POST":
        observation_area = request.form.get("observation_area")
        participant_count = request.form.get("participant_count", type=int)
        duration_minutes = request.form.get("duration_minutes", type=int)
        target_group = request.form.get("target_group") or None
        use_example = request.form.get("use_example") == "on"
        
        # Validierung
        if not observation_area or observation_area not in ["Soziale Kompetenzen", "Verbale Kompetenzen"]:
            flash("Ungültiger Beobachtungsbereich", "error")
            return redirect(url_for("observation_tasks.create_task"))
        
        if not participant_count or participant_count < 1 or participant_count > 10:
            flash("Teilnehmerzahl muss zwischen 1 und 10 liegen", "error")
            return redirect(url_for("observation_tasks.create_task"))
        
        if not duration_minutes or duration_minutes < 5 or duration_minutes > 120:
            flash("Dauer muss zwischen 5 und 120 Minuten liegen", "error")
            return redirect(url_for("observation_tasks.create_task"))
        
        # Neue Task erstellen
        task = Task(
            title=f"Neue Aufgabe - {observation_area}",
            observation_area=observation_area,
            participant_count=participant_count,
            duration_minutes=duration_minutes,
            is_example=False,
            is_active=True,
            created_by_id=current_user.id
        )
        db.session.add(task)
        db.session.flush()
        
        # Initiale Version mit Metadaten erstellen (inklusive Zielgruppe)
        context_data = {
            "observation_area": observation_area,
            "participant_count": participant_count,
            "duration_minutes": duration_minutes,
            "target_group": target_group,
            "use_example": use_example
        }
        
        version = TaskVersion(
            task_id=task.id,
            version_number=1.0,
            content="<p>Aufgabenvorschlag wird generiert...</p>",
            context_data=json.dumps(context_data),
            change_notes="Initiale Version - vor KI-Generierung",
            created_by_id=current_user.id
        )
        db.session.add(version)
        db.session.flush()  # Wichtig: flush() damit version.id verfügbar wird
        task.current_version_id = version.id
        
        db.session.commit()
        
        # Direkt zum Editor und Modell-Auswahl-Modal öffnen
        return redirect(url_for("observation_tasks.edit", task_id=task.id, autogen=1))
    
    return render_template(
        "observation_tasks/create.html",
        observation_areas=["Soziale Kompetenzen", "Verbale Kompetenzen"],
        target_group_options=get_target_group_options(),
        example_tasks=EXAMPLE_TASKS
    )


@observation_tasks_bp.route("/<int:task_id>/generieren", methods=["POST"])
@login_required  
@admin_required
def generate(task_id):
    """
    Schritt 2: KI generiert Aufgabenvorschlag basierend auf Metadaten
    """
    task = db.get_or_404(Task, task_id)

    if request.method == "POST":
        # KI-Auswahl aus Request (Default: Mistral)
        ki_model = request.form.get("ki_model", "mistral")
        
        # KI-Generierung triggern
        if task.current_version:
            context = json.loads(task.current_version.context_data or "{}")
        else:
            context = {}
        
        ai_response = generate_task(
            observation_area=task.observation_area,
            participant_count=task.participant_count,
            duration_minutes=task.duration_minutes,
            context_data=context,
            example_tasks=EXAMPLE_TASKS if context.get("use_example") else None,
            ki_model=ki_model,
            target_group=context.get("target_group")
        )
        
        if ai_response and ai_response.get("content"):
            # Neue Version speichern
            latest_version = max([v for v in task.versions], key=lambda v: v.version_number, default=None)
            next_version = (latest_version.version_number + 0.1) if latest_version else 1.0
            
            # Extrahiere KI-Gym raw_response_id
            raw_response_id = ai_response.get('_raw_response_id')
            
            # Erweitere context_data um KI-Gym Tracking
            context_data_dict = json.loads(task.current_version.context_data) if task.current_version and task.current_version.context_data else {}
            if raw_response_id:
                context_data_dict['raw_response_id'] = raw_response_id
            
            version = TaskVersion(
                task_id=task.id,
                version_number=next_version,
                content=ai_response["content"],
                context_data=json.dumps(context_data_dict) if context_data_dict else None,
                change_notes=f"KI-Vorschlag generiert ({ai_response.get('title', 'Unbetitelt')})",
                created_by_id=current_user.id
            )
            task.current_version_id = None  # Wird unten gesetzt
            db.session.add(version)
            db.session.flush()
            
            task.current_version_id = version.id
            task.title = ai_response.get("title", task.title)
            task.ki_model = ki_model  # Speichere welche KI verwendet wurde
            
            # KI-Gym: Update AIRawResponse mit echter task_id
            if raw_response_id:
                from models import AIRawResponse
                raw_response = db.session.get(AIRawResponse, raw_response_id)
                if raw_response:
                    raw_response.context_id = task.id
                    print(f"   📦 KI-Gym: AIRawResponse #{raw_response_id} aktualisiert mit task_id={task.id}")
            
            db.session.commit()
            
            flash("✓ Aufgabenvorschlag generiert!", "success")
        else:
            flash("KI-Generierung fehlgeschlagen", "error")
        
        return redirect(url_for("observation_tasks.edit", task_id=task.id))
    
    return render_template("observation_tasks/generate.html", task=task)


@observation_tasks_bp.route("/<int:task_id>/bearbeiten", methods=["GET", "POST"])
@login_required
@admin_required
def edit(task_id):
    """
    Schritt 3: Editor + Chat-Integration
    Bearbeitung mit Live-Vorschau und Chat zum Iterieren
    """
    task = db.get_or_404(Task, task_id)
    
    return render_template(
        "observation_tasks/editor.html",
        task=task,
        current_version=task.current_version
    )


@observation_tasks_bp.route("/<int:task_id>/verwerfen", methods=["POST"])
@login_required
@admin_required
def discard_task(task_id):
    """Verwirft die aktuelle Aufgabe (Erstellung abbrechen) und führt zur Übersicht zurück."""
    task = db.get_or_404(Task, task_id)
    task_title = task.title

    task.current_version_id = None
    db.session.flush()
    TaskVersion.query.filter_by(task_id=task.id).delete(synchronize_session=False)
    db.session.delete(task)
    db.session.commit()

    flash(f"✕ Aufgabe '{task_title}' verworfen.", "info")
    return redirect(url_for("observation_tasks.task_library"))


@observation_tasks_bp.route("/<int:task_id>/löschen", methods=["POST"])
@login_required
@admin_required
def delete_task(task_id):
    """Lösche eine Aufgabe."""
    task = db.get_or_404(Task, task_id)
    task_title = task.title
    
    # Wichtig: Zirkuläre Abhängigkeit aufheben
    # current_version_id muss vor dem Löschen auf None gesetzt werden
    task.current_version_id = None
    db.session.flush()
    # Versions explizit löschen, um CircularDependency zu vermeiden
    TaskVersion.query.filter_by(task_id=task.id).delete(synchronize_session=False)
    
    # Jetzt können wir die Task löschen
    db.session.delete(task)
    db.session.commit()
    
    flash(f"✓ Aufgabe '{task_title}' gelöscht!", "success")
    return redirect(url_for("observation_tasks.task_library"))


@observation_tasks_bp.route("/<int:task_id>/versions", methods=["GET"])
@login_required
@admin_required
def versions(task_id):
    """Liste aller Versionen einer Aufgabe."""
    task = db.get_or_404(Task, task_id)
    versions = TaskVersion.query.filter_by(task_id=task_id).order_by(TaskVersion.version_number.desc()).all()
    
    return jsonify([{
        "version": v.version_number,
        "created_at": v.created_at.isoformat(),
        "change_notes": v.change_notes,
        "created_by": v.created_by.first_name + " " + v.created_by.last_name if v.created_by else "System"
    } for v in versions])


@observation_tasks_bp.route("/<int:task_id>/speichern", methods=["POST"])
@login_required
@admin_required
def save_version(task_id):
    """Speichere aktuelle Editor-Version als neue Taskversion."""
    task = db.get_or_404(Task, task_id)
    data = request.get_json()
    
    content = data.get("content")
    change_notes = data.get("change_notes", "Manuelle Bearbeitung")
    
    if not content:
        return jsonify({"error": "Kein Inhalt"}), 400
    
    # Titel aktualisieren falls vorhanden
    if data.get("title"):
        task.title = data["title"]
    
    # Neue Version erstellen
    latest_version = max([v for v in task.versions], key=lambda v: v.version_number, default=None)
    next_version = (latest_version.version_number + 0.1) if latest_version else 1.0
    
    version = TaskVersion(
        task_id=task.id,
        version_number=next_version,
        content=content,
        context_data=task.current_version.context_data if task.current_version else None,
        change_notes=change_notes,
        created_by_id=current_user.id
    )
    db.session.add(version)
    db.session.flush()  # Get version.id
    
    task.current_version = version
    
    # KI-Gym: Track edits if this version was derived from AI
    if task.current_version and task.current_version.context_data:
        try:
            context_dict = json.loads(task.current_version.context_data)
            raw_response_id = context_dict.get('raw_response_id')
            
            if raw_response_id:
                from models import AIRawResponse, ContentEdit
                from ki_services import compute_content_diff
                
                raw_response = db.session.get(AIRawResponse, raw_response_id)
                if raw_response:
                    # Extract content from raw JSON response
                    try:
                        raw_json = json.loads(raw_response.raw_response)
                        raw_content = raw_json.get('content', raw_response.raw_response)
                    except:
                        raw_content = raw_response.raw_response
                    
                    # Compute diff metrics
                    diff_metrics = compute_content_diff(raw_content, content)
                    
                    # Create ContentEdit record
                    content_edit = ContentEdit(
                        raw_response_id=raw_response_id,
                        version_type='task_version',
                        version_id=version.id,
                        diff_metrics=diff_metrics,
                        edit_reason=change_notes,
                        edited_by_id=current_user.id
                    )
                    db.session.add(content_edit)
                    
                    # Update AIRawResponse status
                    raw_response.processing_status = 'edited'
                    
                    print(f"   📝 KI-Gym: ContentEdit #{content_edit.id if hasattr(content_edit, 'id') else '?'} erstellt "
                          f"(Magnitude: {diff_metrics['edit_magnitude']}, Ähnlichkeit: {diff_metrics['similarity_percent']}%)")
        except Exception as e:
            print(f"   ⚠️  KI-Gym Edit Tracking Fehler: {e}")
            # Non-critical: continue without breaking
    
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "version": version.version_number,
        "message": f"✓ Version {version.version_number} gespeichert"
    })


@observation_tasks_bp.route("/<int:task_id>/chat", methods=["POST"])
@login_required
@admin_required
def chat_message(task_id):
    """Chat-Iteration: Nutzer schreibt Anfrage, KI verfeinert Aufgabe."""
    task = db.get_or_404(Task, task_id)
    data = request.get_json()
    
    user_message = data.get("message")
    current_content = data.get("current_content")
    
    if not user_message:
        return jsonify({"error": "Keine Nachricht"}), 400
    
    # KI-Refinement
    ai_response = refine_task_content(
        draft_content=current_content or (task.current_version.content if task.current_version else ""),
        user_request=user_message,
        conversation_history=[],
        ki_model="mistral"
    )
    
    if ai_response and ai_response.get("updated_content"):
        return jsonify({
            "status": "success",
            "ai_response": ai_response.get("ai_response", ""),
            "updated_content": ai_response["updated_content"]
        })
    else:
        return jsonify({"error": "KI-Verarbeitung fehlgeschlagen"}), 500


@observation_tasks_bp.route("/<int:task_id>/beispiel/<example_key>", methods=["GET"])
@login_required
@admin_required
def view_example(task_id, example_key):
    """Zeige Beispiel-Aufgabe an."""
    if example_key not in EXAMPLE_TASKS:
        return jsonify({"error": "Beispiel nicht gefunden"}), 404
    
    example = EXAMPLE_TASKS[example_key]
    return jsonify(example)
