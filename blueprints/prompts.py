# blueprints/prompts.py - KOMPLETTE DATEI
"""Dieses Modul enthält Routen und Funktionen für die Prompt-Verwaltung."""

from flask import (Blueprint, request, redirect, url_for, flash, render_template,
                   jsonify)

import database as db

# Ein Blueprint-Objekt für die Prompt-Verwaltung
prompts_bp = Blueprint('prompts', __name__)


# --- ROUTEN FÜR PROMPT-VERWALTUNG ---

@prompts_bp.route("/prompts")
def manage_prompts():
    """Zeigt die Seite zur Verwaltung von Prompts an."""
    prompts = db.get_all_prompts()
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Prompt-Verwaltung"},
    ]
    return render_template(
        "manage_prompts.html", prompts=prompts, breadcrumbs=breadcrumbs
    )


@prompts_bp.route("/prompt/add", methods=["GET", "POST"])
def add_prompt():
    """Fügt einen neuen Prompt hinzu."""
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        content = request.form.get("content")
        
        if not name or not content:
            flash("Name und Inhalt des Prompts dürfen nicht leer sein.", "warning")
            return render_template("prompt_form.html", title="Neuen Prompt erstellen")
            
        db.add_prompt(name, description, content)
        flash(f'Prompt "{name}" wurde erfolgreich erstellt.', "success")
        return redirect(url_for("prompts.manage_prompts"))
        
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("prompts.manage_prompts"), "text": "Prompt-Verwaltung"},
        {"text": "Neuen Prompt erstellen"},
    ]
    return render_template(
        "prompt_form.html", title="Neuen Prompt erstellen", breadcrumbs=breadcrumbs
    )


@prompts_bp.route("/prompt/edit/<int:prompt_id>", methods=["GET", "POST"])
def edit_prompt(prompt_id):
    """Bearbeitet einen bestehenden Prompt."""
    prompt = db.get_prompt_by_id(prompt_id)
    if not prompt:
        flash("Prompt nicht gefunden.", "error")
        return redirect(url_for("prompts.manage_prompts"))
        
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        content = request.form.get("content")
        
        if not name or not content:
            flash("Name und Inhalt des Prompts dürfen nicht leer sein.", "warning")
            return render_template(
                "prompt_form.html",
                title=f"Prompt bearbeiten: {prompt['name']}",
                prompt=prompt,
            )
            
        db.update_prompt(prompt_id, name, description, content)
        flash(f'Prompt "{name}" wurde erfolgreich aktualisiert.', "success")
        return redirect(url_for("prompts.manage_prompts"))
        
    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"link": url_for("prompts.manage_prompts"), "text": "Prompt-Verwaltung"},
        {"text": f"Prompt bearbeiten: {prompt['name']}"},
    ]
    return render_template(
        "prompt_form.html",
        title=f"Prompt bearbeiten: {prompt['name']}",
        prompt=prompt,
        breadcrumbs=breadcrumbs,
    )


@prompts_bp.route("/prompt/delete/<int:prompt_id>", methods=["POST"])
def delete_prompt(prompt_id):
    """Löscht einen Prompt."""
    db.delete_prompt_by_id(prompt_id)
    flash("Prompt wurde gelöscht.", "success")
    return redirect(url_for("prompts.manage_prompts"))


# --- API-ROUTE FÜR PROMPTS ---

@prompts_bp.route("/api/prompt/<int:prompt_id>")
def get_prompt_content_api(prompt_id):
    """Gibt den Inhalt eines bestimmten Prompts zurück."""
    prompt = db.get_prompt_by_id(prompt_id)
    if prompt:
        return jsonify({"content": prompt["content"]})
    return jsonify({"error": "Prompt not found"}), 404