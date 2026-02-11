"""
Task Generator Blueprint - Phase 2 Feature Development.
Handles task library, generation, versioning, and chat-based iteration.
"""

import json
from datetime import datetime, timezone
from flask import (
    Blueprint, flash, jsonify, redirect, render_template,
    request, url_for
)
from flask_login import login_required, current_user
from extensions import csrf, db
from models import Task, TaskVersion, User
from decorators import admin_required, filter_groups_by_access
from utils import sanitize_html
from services.task_generator import generate_task as ki_generate_task
from services.task_refinement import refine_task_content

tasks_bp = Blueprint("tasks", __name__)


# =============================================================================
# TASK LIBRARY (B3)
# =============================================================================

@tasks_bp.route("/tasks/library")
@login_required
def task_library():
    """
    Browse task library, filterable by observation area and participant count.
    All authenticated users can view, only admins can create.
    """
    # Get filter parameters
    observation_area = request.args.get("observation_area", "").strip()
    participant_count = request.args.get("participant_count", type=int)
    page = request.args.get("page", 1, type=int)
    per_page = 10
    
    # Build query
    query = db.select(Task).where(Task.is_active == True)
    
    if observation_area:
        query = query.where(Task.observation_area.ilike(f"%{observation_area}%"))
    
    if participant_count:
        query = query.where(
            (Task.participant_count == participant_count) | 
            (Task.participant_count == None)
        )
    
    # Paginate
    pagination = db.paginate(
        query.order_by(Task.created_at.desc()),
        page=page,
        per_page=per_page
    )
    
    tasks = pagination.items
    
    # Get unique observation areas for filter dropdown
    observation_areas_query = db.session.execute(
        db.select(Task.observation_area.distinct()).where(Task.is_active == True)
    ).scalars().all()
    observation_areas = [oa for oa in observation_areas_query if oa]
    
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Task Library"},
    ]
    
    return render_template(
        "tasks/library.html",
        tasks=tasks,
        pagination=pagination,
        observation_areas=observation_areas,
        selected_area=observation_area,
        selected_count=participant_count,
        breadcrumbs=breadcrumbs,
    )


@tasks_bp.route("/tasks/<int:task_id>")
@login_required
def view_task(task_id):
    """View task details and version history."""
    task = db.get_or_404(Task, task_id)
    
    if not task.is_active:
        flash("Diese Task ist nicht verfügbar.", "warning")
        return redirect(url_for("tasks.task_library"))
    
    versions = db.session.execute(
        db.select(TaskVersion)
        .where(TaskVersion.task_id == task_id)
        .order_by(TaskVersion.version_number.desc())
    ).scalars().all()
    
    return jsonify({
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "observation_area": task.observation_area,
        "participant_count": task.participant_count,
        "duration_minutes": task.duration_minutes,
        "current_version": task.current_version_id,
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "created_at": v.created_at.isoformat(),
                "change_notes": v.change_notes,
            }
            for v in versions
        ]
    })


@tasks_bp.route("/tasks/<int:task_id>/versions/<int:version_id>")
@login_required
def view_task_version(task_id, version_id):
    """Get specific version content (Read-Only)."""
    task = db.get_or_404(Task, task_id)
    version = db.session.execute(
        db.select(TaskVersion).where(
            (TaskVersion.id == version_id) & 
            (TaskVersion.task_id == task_id)
        )
    ).scalar_one_or_none()
    
    if not version:
        return jsonify({"error": "Version not found"}), 404
    
    return jsonify({
        "content": version.content,
        "version_number": version.version_number,
        "created_at": version.created_at.isoformat(),
        "change_notes": version.change_notes,
        "context_data": json.loads(version.context_data or "{}"),
    })


# =============================================================================
# TASK GENERATION (B6 - Auto-Generation endpoint)
# =============================================================================

@tasks_bp.route("/tasks/generate", methods=["POST"])
@login_required
@admin_required
def generate_task_draft():
    """
    Generate task draft (B6).
    Input: {observation_area, participant_count, duration}
    Output: {content: HTML, suggestions: []}
    Draft NOT saved - only cache in session for chat preview.
    """
    data = request.get_json() or {}
    
    observation_area = data.get("observation_area", "").strip()
    participant_count = data.get("participant_count", type=int)
    duration = data.get("duration", type=int)
    ki_model = data.get("ki_model", "mistral")
    
    # Validation
    if not observation_area:
        return jsonify({"error": "observation_area erforderlich"}), 400
    if participant_count and not (1 <= participant_count <= 6):
        return jsonify({"error": "participant_count zwischen 1-6"}), 400
    if duration and not (25 <= duration <= 35):
        return jsonify({"error": "duration zwischen 25-35 Minuten"}), 400
    
    # Call KI service (B4 + B6)
    try:
        result = ki_generate_task(
            observation_area=observation_area,
            participant_count=participant_count or 3,
            duration=duration or 30,
            ki_model=ki_model
        )
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 500
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": f"KI-Fehler: {str(e)}"}), 500


# =============================================================================
# CHAT INTERFACE (B8 - Chat-driven iteration)
# =============================================================================

@tasks_bp.route("/tasks/chat/message", methods=["POST"])
@login_required
@admin_required
@csrf.exempt
def chat_message():
    """
    Chat API for iterative task refinement (B8 + B9).
    Maintains conversation history and updates draft in real-time.
    
    Input: {message: "...", draft_id: "UUID", history: [...]}
    Output: {ai_response: "...", updated_content: "..."}
    """
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()
    draft_id = data.get("draft_id", "")
    history = data.get("history", [])
    current_content = data.get("current_content", "<p>Task content...</p>")
    ki_model = data.get("ki_model", "mistral")
    
    if not user_message:
        return jsonify({"error": "Nachricht erforderlich"}), 400
    
    # Call KI service (B9 - Context Management + Iterative Refinement)
    try:
        result = refine_task_content(
            draft_content=current_content,
            user_request=user_message,
            conversation_history=history,
            ki_model=ki_model
        )
        
        return jsonify({
            "ai_response": result.get("ai_response", ""),
            "updated_content": result.get("updated_content", current_content),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    
    except Exception as e:
        return jsonify({
            "ai_response": f"Fehler: {str(e)}",
            "updated_content": current_content,
        }), 500


# =============================================================================
# VERSIONING SYSTEM (B10)
# =============================================================================

@tasks_bp.route("/tasks", methods=["POST"])
@login_required
@admin_required
def create_task():
    """Create new task from chat draft."""
    data = request.get_json() or {}
    
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    observation_area = data.get("observation_area", "").strip()
    participant_count = data.get("participant_count", type=int)
    duration = data.get("duration", type=int)
    
    if not all([title, content, observation_area]):
        return jsonify({"error": "title, content, observation_area erforderlich"}), 400
    
    # Create Task
    task = Task(
        title=title,
        description=data.get("description", ""),
        observation_area=observation_area,
        participant_count=participant_count,
        duration_minutes=duration,
        created_by_id=current_user.id,
        is_active=True,
    )
    db.session.add(task)
    db.session.flush()
    
    # Create initial TaskVersion v1.0
    version = TaskVersion(
        task_id=task.id,
        version_number=1.0,
        content=sanitize_html(content),
        context_data=json.dumps({
            "observation_area": observation_area,
            "participant_count": participant_count,
            "duration": duration,
        }),
        change_notes="Initiale Version",
        created_by_id=current_user.id,
    )
    db.session.add(version)
    db.session.flush()
    
    # Set as current version
    task.current_version_id = version.id
    db.session.commit()
    
    flash(f"Task '{title}' erstellt.", "success")
    return jsonify({"id": task.id, "version_id": version.id}), 201


@tasks_bp.route("/tasks/<int:task_id>/save-version", methods=["POST"])
@login_required
@admin_required
def save_task_version(task_id):
    """Save current draft as new version (B10)."""
    task = db.get_or_404(Task, task_id)
    data = request.get_json() or {}
    
    content = data.get("content", "").strip()
    change_notes = data.get("change_notes", "").strip()
    
    if not content:
        return jsonify({"error": "content erforderlich"}), 400
    
    # Get last version number and increment
    last_version = db.session.execute(
        db.select(TaskVersion)
        .where(TaskVersion.task_id == task_id)
        .order_by(TaskVersion.version_number.desc())
    ).scalar_one_or_none()
    
    next_version = (last_version.version_number + 0.1) if last_version else 1.0
    
    # Create new version
    new_version = TaskVersion(
        task_id=task_id,
        version_number=next_version,
        content=sanitize_html(content),
        change_notes=change_notes or "Keine Anmerkungen",
        created_by_id=current_user.id,
    )
    db.session.add(new_version)
    db.session.flush()
    
    # Update current_version
    task.current_version_id = new_version.id
    task.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    
    return jsonify({
        "id": new_version.id,
        "version_number": new_version.version_number
    }), 201


@tasks_bp.route("/tasks/<int:task_id>/versions")
@login_required
def list_task_versions(task_id):
    """List all versions with metadata."""
    task = db.get_or_404(Task, task_id)
    
    versions = db.session.execute(
        db.select(TaskVersion)
        .where(TaskVersion.task_id == task_id)
        .order_by(TaskVersion.version_number.desc())
    ).scalars().all()
    
    return jsonify({
        "task_id": task.id,
        "task_title": task.title,
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "created_at": v.created_at.isoformat(),
                "created_by": v.created_by.email,
                "change_notes": v.change_notes,
            }
            for v in versions
        ]
    })


@tasks_bp.route("/tasks/<int:task_id>/revert/<int:version_id>", methods=["POST"])
@login_required
@admin_required
def revert_to_version(task_id, version_id):
    """Revert task to specific version (B10)."""
    task = db.get_or_404(Task, task_id)
    version = db.session.execute(
        db.select(TaskVersion).where(
            (TaskVersion.id == version_id) & 
            (TaskVersion.task_id == task_id)
        )
    ).scalar_one_or_none()
    
    if not version:
        return jsonify({"error": "Version nicht gefunden"}), 404
    
    # Create revert version
    last_version = db.session.execute(
        db.select(TaskVersion)
        .where(TaskVersion.task_id == task_id)
        .order_by(TaskVersion.version_number.desc())
    ).scalar_one_or_none()
    
    next_version_number = (last_version.version_number + 0.1) if last_version else 2.0
    
    revert_version = TaskVersion(
        task_id=task_id,
        version_number=next_version_number,
        content=version.content,
        change_notes=f"Reverted to v{version.version_number}",
        created_by_id=current_user.id,
    )
    db.session.add(revert_version)
    db.session.flush()
    
    task.current_version_id = revert_version.id
    db.session.commit()
    
    return jsonify({"message": "Reverted successfully"}), 200


# =============================================================================
# EDIT INTERFACE (B8 Frontend + B10 Backend)
# =============================================================================

@tasks_bp.route("/tasks/<int:task_id>/edit")
@login_required
@admin_required
def edit_task(task_id):
    """Edit task with chat + rich editor interface."""
    task = db.get_or_404(Task, task_id)
    
    current_version = None
    if task.current_version_id:
        current_version = db.session.get(TaskVersion, task.current_version_id)
    
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("tasks.task_library"), "text": "Task Library"},
        {"text": f"Edit: {task.title}"},
    ]
    
    return render_template(
        "tasks/generate.html",
        task=task,
        current_version=current_version,
        breadcrumbs=breadcrumbs,
    )


@tasks_bp.route("/tasks/new")
@login_required
@admin_required
def new_task():
    """Create new task with chat + editor interface."""
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("tasks.task_library"), "text": "Task Library"},
        {"text": "Create Task"},
    ]
    
    return render_template(
        "tasks/generate.html",
        task=None,
        breadcrumbs=breadcrumbs,
    )


@tasks_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_task(task_id):
    """Soft-delete task (set is_active=False)."""
    task = db.get_or_404(Task, task_id)
    task.is_active = False
    db.session.commit()
    
    return jsonify({"message": "Task gelöscht"}), 200
