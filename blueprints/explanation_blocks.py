# blueprints/explanation_blocks.py
"""Dieses Modul enthält Routen und Funktionen für die Verwaltung von Erklärungstextblöcken."""

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import login_required

from extensions import db
from models import ExplanationBlock
from decorators import permission_required

explanation_blocks_bp = Blueprint("explanation_blocks", __name__)


@explanation_blocks_bp.route("/explanation-blocks")
@login_required
@permission_required("explanation_blocks.manage")
def manage_explanation_blocks():
    """Zeigt die Seite zur Verwaltung von Textblöcken an."""
    blocks = (
        db.session.execute(
            db.select(ExplanationBlock).order_by(
                ExplanationBlock.order, ExplanationBlock.id
            )
        )
        .scalars()
        .all()
    )

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {"text": "Text"},
    ]

    return render_template(
        "manage_explanation_blocks.html", blocks=blocks, breadcrumbs=breadcrumbs
    )


@explanation_blocks_bp.route("/explanation-block/add", methods=["GET", "POST"])
@login_required
@permission_required("explanation_blocks.manage")
def add_explanation_block():
    """Fügt einen neuen Textblock hinzu."""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        order = request.form.get("order", 0, type=int)

        if not title:
            flash("Titel ist erforderlich.", "error")
            return redirect(url_for("explanation_blocks.add_explanation_block"))

        new_block = ExplanationBlock(title=title, content=content, order=order)

        db.session.add(new_block)
        db.session.commit()

        flash("Textblock erfolgreich hinzugefügt.", "success")
        return redirect(url_for("explanation_blocks.manage_explanation_blocks"))

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {
            "link": url_for("explanation_blocks.manage_explanation_blocks"),
            "text": "Text",
        },
        {"text": "Neuer Textblock"},
    ]

    return render_template(
        "explanation_block_form.html", breadcrumbs=breadcrumbs, block=None
    )


@explanation_blocks_bp.route(
    "/explanation-block/edit/<int:block_id>", methods=["GET", "POST"]
)
@login_required
@permission_required("explanation_blocks.manage")
def edit_explanation_block(block_id):
    """Bearbeitet einen bestehenden Textblock."""
    block = db.get_or_404(ExplanationBlock, block_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        order = request.form.get("order", 0, type=int)

        if not title:
            flash("Titel ist erforderlich.", "error")
            return redirect(
                url_for("explanation_blocks.edit_explanation_block", block_id=block_id)
            )

        block.title = title
        block.content = content
        block.order = order

        db.session.commit()

        flash("Textblock erfolgreich aktualisiert.", "success")
        return redirect(url_for("explanation_blocks.manage_explanation_blocks"))

    breadcrumbs = [
        {"link": url_for("dashboard"), "text": "Dashboard"},
        {
            "link": url_for("explanation_blocks.manage_explanation_blocks"),
            "text": "Text",
        },
        {"text": f"Bearbeiten: {block.title}"},
    ]

    return render_template(
        "explanation_block_form.html", breadcrumbs=breadcrumbs, block=block
    )


@explanation_blocks_bp.route(
    "/explanation-block/delete/<int:block_id>", methods=["POST"]
)
@login_required
@permission_required("explanation_blocks.manage")
def delete_explanation_block(block_id):
    """Löscht einen Textblock."""
    block = db.get_or_404(ExplanationBlock, block_id)

    db.session.delete(block)
    db.session.commit()

    flash("Textblock wurde gelöscht.", "success")
    return redirect(url_for("explanation_blocks.manage_explanation_blocks"))
