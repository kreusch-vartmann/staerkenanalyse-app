# blueprints/prompts.py
"""Dieses Modul enthält Routen und Funktionen für die Prompt-Verwaltung."""

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import login_required

from extensions import csrf, db
from models import Prompt
from decorators import permission_required

# Ein Blueprint-Objekt für die Prompt-Verwaltung
prompts_bp = Blueprint("prompts", __name__)


# --- ROUTEN FÜR PROMPT-VERWALTUNG ---


@prompts_bp.route("/prompts")
@login_required
@permission_required("prompts.manage")
def manage_prompts():
    """Zeigt die Seite zur Verwaltung von Prompts an."""
    prompts = (
        db.session.execute(db.select(Prompt).order_by(Prompt.name)).scalars().all()
    )
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Prompts"},
    ]
    return render_template(
        "manage_prompts.html", prompts=prompts, breadcrumbs=breadcrumbs
    )


@prompts_bp.route("/prompt/add", methods=["GET", "POST"])
@login_required
@permission_required("prompts.manage")
def add_prompt():
    """Fügt einen neuen Prompt hinzu."""
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        content = request.form.get("content")
        is_default = request.form.get("is_default") == "1"

        if not name or not content:
            flash("Name und Inhalt des Prompts dürfen nicht leer sein.", "warning")
            temp_prompt = Prompt(
                name=name or "",
                description=description,
                content=content or "",
                is_default=is_default,
            )
            return render_template(
                "prompt_form.html",
                title="Neuen Prompt erstellen",
                prompt=temp_prompt,
            )

        # Prüfe auf Duplikat
        existing = Prompt.query.filter_by(name=name).first()
        if existing:
            flash(f'Ein Prompt mit dem Namen "{name}" existiert bereits.', "error")
            temp_prompt = Prompt(
                name=name,
                description=description,
                content=content or "",
                is_default=is_default,
            )
            return render_template(
                "prompt_form.html",
                title="Neuen Prompt erstellen",
                prompt=temp_prompt,
            )

        if is_default:
            Prompt.query.update({Prompt.is_default: False}, synchronize_session=False)

        new_prompt = Prompt(
            name=name,
            description=description,
            content=content,
            is_default=is_default,
        )
        db.session.add(new_prompt)
        db.session.commit()

        flash(f'Prompt "{name}" wurde erfolgreich erstellt.', "success")
        return redirect(url_for("prompts.manage_prompts"))

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("prompts.manage_prompts"), "text": "Prompts"},
        {"text": "Neuen Prompt erstellen"},
    ]
    return render_template(
        "prompt_form.html", title="Neuen Prompt erstellen", breadcrumbs=breadcrumbs
    )


@prompts_bp.route("/prompt/edit/<int:prompt_id>", methods=["GET", "POST"])
@login_required
@permission_required("prompts.manage")
def edit_prompt(prompt_id):
    """Bearbeitet einen bestehenden Prompt."""
    prompt = db.session.get(Prompt, prompt_id)
    if not prompt:
        flash("Prompt nicht gefunden.", "error")
        return redirect(url_for("prompts.manage_prompts"))

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        content = request.form.get("content")
        is_default = request.form.get("is_default") == "1"

        if not name or not content:
            flash("Name und Inhalt des Prompts dürfen nicht leer sein.", "warning")
            temp_prompt = Prompt(
                name=name or "",
                description=description,
                content=content or "",
                is_default=is_default,
            )
            return render_template(
                "prompt_form.html",
                title=f"Prompt bearbeiten: {prompt.name}",
                prompt=temp_prompt,
            )

        # Prüfe ob ein anderer Prompt bereits diesen Namen hat
        if name != prompt.name:
            existing = Prompt.query.filter_by(name=name).first()
            if existing:
                flash(
                    f'Ein anderer Prompt mit dem Namen "{name}" existiert bereits.',
                    "error",
                )
                temp_prompt = Prompt(
                    name=name,
                    description=description,
                    content=content or "",
                    is_default=is_default,
                )
                return render_template(
                    "prompt_form.html",
                    title=f"Prompt bearbeiten: {prompt.name}",
                    prompt=temp_prompt,
                )

        prompt.name = name
        prompt.description = description
        prompt.content = content
        prompt.is_default = is_default

        if is_default:
            Prompt.query.filter(Prompt.id != prompt.id).update(
                {Prompt.is_default: False},
                synchronize_session=False,
            )
        db.session.commit()

        flash(f'Prompt "{name}" wurde erfolgreich aktualisiert.', "success")
        return redirect(url_for("prompts.manage_prompts"))

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("prompts.manage_prompts"), "text": "Prompts"},
        {"text": f"Prompt bearbeiten: {prompt.name}"},
    ]
    return render_template(
        "prompt_form.html",
        title=f"Prompt bearbeiten: {prompt.name}",
        prompt=prompt,
        breadcrumbs=breadcrumbs,
    )


@prompts_bp.route("/prompt/delete/<int:prompt_id>", methods=["POST"])
@login_required
@permission_required("prompts.manage")
def delete_prompt(prompt_id):
    """Löscht einen Prompt."""
    prompt = db.session.get(Prompt, prompt_id)
    if prompt:
        db.session.delete(prompt)
        db.session.commit()
        flash("Prompt wurde gelöscht.", "success")
    else:
        flash("Prompt nicht gefunden.", "error")
    return redirect(url_for("prompts.manage_prompts"))


# --- API-ROUTE FÜR PROMPTS ---


@prompts_bp.route("/api/prompt/<int:prompt_id>")
@login_required
@permission_required("prompts.manage")
@csrf.exempt
def get_prompt_content_api(prompt_id):
    """Gibt den Inhalt eines bestimmten Prompts zurück."""
    prompt = db.session.get(Prompt, prompt_id)
    if prompt:
        return jsonify({"content": prompt.content})
    return jsonify({"error": "Prompt not found"}), 404
