# blueprints/data_import.py
"""Robuste Import-Funktionen mit Schema-Versions-Unterstützung."""

import json
from datetime import UTC, datetime

import pandas as pd
from flask import flash

from extensions import db
from models import Group, Participant
from version import EXPORT_SCHEMA_VERSION


def import_participants_from_export(file, format="xlsx"):
    """
    Importiert Teilnehmer aus einem Export-File mit Schema-Versions-Check.

    Args:
        file: FileStorage-Objekt (aus request.files)
        format: 'xlsx' oder 'csv'

    Returns:
        tuple: (success: bool, message: str, imported_count: int)
    """
    try:
        # Datei einlesen
        if format == "xlsx":
            df = pd.read_excel(file)
        else:
            df = pd.read_csv(file)

        if df.empty:
            return False, "Die Datei enthält keine Daten.", 0

        # Schema-Version prüfen (falls vorhanden)
        schema_version = (
            df["_export_schema_version"].iloc[0]
            if "_export_schema_version" in df.columns
            else "unknown"
        )

        # Version-spezifische Import-Logik
        if schema_version == "1.0" or schema_version == "unknown":
            return _import_schema_v1_0(df)
        else:
            return (
                False,
                f"Unbekannte Schema-Version: {schema_version}. Bitte App aktualisieren.",
                0,
            )

    except Exception as e:
        return False, f"Fehler beim Importieren: {str(e)}", 0


def _import_schema_v1_0(df):
    """Import-Logik für Schema Version 1.0"""
    imported_count = 0
    skipped_count = 0

    # Erforderliche Spalten prüfen
    required_columns = ["Name", "Gruppe"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"Fehlende Spalten: {', '.join(missing_columns)}", 0

    # Gruppen-Mapping erstellen (bestehende Gruppen verwenden oder neu anlegen)
    groups_cache = {}

    for _, row in df.iterrows():
        try:
            # Gruppe finden oder erstellen
            group_name = row.get("Gruppe", "").strip()
            if not group_name:
                skipped_count += 1
                continue

            if group_name not in groups_cache:
                group = db.session.execute(
                    db.select(Group).where(Group.name == group_name)
                ).scalar_one_or_none()

                if not group:
                    # Neue Gruppe anlegen
                    group = Group(
                        name=group_name,
                        location=row.get("Ort", ""),
                        leitung_fremdeinschatzung=row.get("Leitung (Fremd)", ""),
                        leitung_selbsteinschatzung=row.get("Leitung (Selbst)", ""),
                        beobachter1=row.get("Beobachter 1", ""),
                        beobachter2=row.get("Beobachter 2", ""),
                    )
                    db.session.add(group)
                    db.session.flush()

                groups_cache[group_name] = group

            group = groups_cache[group_name]

            # Teilnehmer prüfen (Name + Gruppe muss eindeutig sein)
            participant_name = row.get("Name", "").strip()
            if not participant_name:
                skipped_count += 1
                continue

            existing_participant = db.session.execute(
                db.select(Participant).where(
                    Participant.name == participant_name,
                    Participant.group_id == group.id,
                )
            ).scalar_one_or_none()

            if existing_participant:
                # Überspringen oder aktualisieren?
                # TODO: Entscheiden: Überspringen oder Daten überschreiben
                skipped_count += 1
                continue

            # Neuen Teilnehmer erstellen
            participant = Participant(name=participant_name, group_id=group.id)

            # Beobachtungen
            observations = {
                "social": row.get("Beobachtung (Sozial)", ""),
                "verbal": row.get("Beobachtung (Verbal)", ""),
            }
            participant.observations = (
                json.dumps(observations) if any(observations.values()) else None
            )

            # SK/VK Ratings (mit Fallback für fehlende Werte)
            sk_ratings = {
                "flexibility": _safe_numeric(row.get("SK Flexibilität")),
                "team_orientation": _safe_numeric(row.get("SK Teamorientierung")),
                "process_orientation": _safe_numeric(row.get("SK Prozessorientierung")),
                "results_orientation": _safe_numeric(
                    row.get("SK Ergebnisorientierung")
                ),
            }
            participant.sk_ratings = (
                json.dumps(sk_ratings) if any(sk_ratings.values()) else None
            )

            vk_ratings = {
                "flexibility": _safe_numeric(row.get("VK Flexibilität")),
                "consulting": _safe_numeric(row.get("VK Beratung")),
                "objectivity": _safe_numeric(row.get("VK Sachlichkeit")),
                "goal_orientation": _safe_numeric(row.get("VK Zielorientierung")),
            }
            participant.vk_ratings = (
                json.dumps(vk_ratings) if any(vk_ratings.values()) else None
            )

            # KI-Texte
            ki_texts = {
                "social_text": row.get("KI-Text (Sozial)", ""),
                "verbal_text": row.get("KI-Text (Verbal)", ""),
                "summary_text": row.get("KI-Text (Zusammenfassung)", ""),
            }
            participant.ki_texts = (
                json.dumps(ki_texts) if any(ki_texts.values()) else None
            )

            # KI-Rohdaten (falls vorhanden)
            if "KI-Rohdaten" in row and pd.notna(row["KI-Rohdaten"]):
                participant.ki_raw_response = row["KI-Rohdaten"]

            db.session.add(participant)
            imported_count += 1

        except Exception as e:
            # Einzelne Fehler loggen, aber weitermachen
            flash(f"Fehler bei Zeile {_ + 2}: {str(e)}", "warning")
            skipped_count += 1
            continue

    # Commit
    db.session.commit()

    message = f"Import erfolgreich: {imported_count} Teilnehmer importiert"
    if skipped_count > 0:
        message += f", {skipped_count} übersprungen"

    return True, message, imported_count


def _safe_numeric(value):
    """Konvertiert Wert sicher zu float oder None."""
    if pd.isna(value) or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
