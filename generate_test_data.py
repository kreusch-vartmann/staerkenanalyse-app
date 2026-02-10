#!/usr/bin/env python3
"""
Flask CLI Command zur Generierung synthetischer Testdaten.

Nutzt Mistral oder Gemini API zur Generierung realistischer deutscher Namen,
Beobachtungen und Texte. Vermeidet jegliches Risiko durch reale Nutzerdaten.

Usage:
    flask generate-test-data
    flask generate-test-data --groups 3 --participants 10-15
    flask generate-test-data --clear  # Löscht vorher alle Daten
"""

import json
import os
import random
from datetime import datetime, timezone, timedelta

import click
from flask import Flask
from flask.cli import with_appcontext

from extensions import db
from models import Group, Participant, SelfAssessment

# Import API-Clients direkt aus ki_services
try:
    from ki_services import MISTRAL_CLIENT, GenerativeModel

    # Für Mistral API Message-Format
    try:
        from mistralai.models.chat_completion import ChatMessage
    except ImportError:
        ChatMessage = None
except ImportError:
    MISTRAL_CLIENT = None
    GenerativeModel = None
    ChatMessage = None


# =============================================================================
# Fake-Daten für realistische Kontexte
# =============================================================================

FAKE_CITIES = [
    "Berlin",
    "München",
    "Hamburg",
    "Köln",
    "Frankfurt",
    "Stuttgart",
    "Düsseldorf",
    "Leipzig",
    "Dortmund",
    "Essen",
]

FAKE_FIRST_NAMES = [
    "Anna",
    "Max",
    "Sophie",
    "Leon",
    "Emma",
    "Paul",
    "Mia",
    "Lukas",
    "Hannah",
    "Felix",
    "Lena",
    "Jonas",
    "Laura",
    "Tim",
    "Marie",
    "David",
]

FAKE_LAST_NAMES = [
    "Schmidt",
    "Müller",
    "Weber",
    "Fischer",
    "Wagner",
    "Becker",
    "Hoffmann",
    "Koch",
    "Schulz",
    "Meyer",
    "Schneider",
    "Richter",
    "Zimmermann",
    "Braun",
    "Krüger",
    "Wolf",
    "Schäfer",
    "Keller",
    "Schulze",
    "Berger",
]

FAKE_SEASONS = ["Frühjahr", "Sommer", "Herbst", "Winter"]
FAKE_YEARS = ["2024", "2025", "2026"]


# =============================================================================
# Hilfsfunktion: KI-API Wrapper
# =============================================================================


def _call_ai_api(prompt, max_tokens=300, temperature=0.8):
    """
    Wrapper für KI-API-Aufrufe (Mistral oder Gemini).

    Args:
        prompt (str): User-Prompt
        max_tokens (int): Maximale Token-Anzahl
        temperature (float): Temperature-Parameter

    Returns:
        str: KI-generierte Antwort

    Raises:
        Exception: Bei API-Fehler oder fehlenden Clients
    """
    # Versuche zuerst Mistral (bevorzugt für JSON)
    if MISTRAL_CLIENT and ChatMessage:
        try:
            messages = [ChatMessage(role="user", content=prompt)]
            response = MISTRAL_CLIENT.chat(
                model="mistral-small-latest",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            click.echo(f"   ⚠️ Mistral API Fehler: {e}")
            # Fallback zu Gemini

    # Fallback: Google Gemini
    if GenerativeModel:
        try:
            # API-Key prüfen
            if not os.getenv("GOOGLE_API_KEY"):
                raise ValueError("GOOGLE_API_KEY nicht gesetzt")

            model = GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API Fehler: {e}")

    raise Exception("Keine KI-API verfügbar (kein Mistral oder Gemini Client)")


# =============================================================================
# Text-Generierungsfunktionen
# =============================================================================


def generate_observation_text(name):
    """
    Generiert echte Assessment-Center-Beobachtungen (NICHT Interpretationen).

    AC-Beobachtungen sind VERHALTENSDESKRIPTOREN:
    - ✅ "Kandidat sprach 40% der Redezeit, unterbrach 2x andere"
    - ❌ "Kandidat war dominant"

    Args:
        name (str): Teilnehmername

    Returns:
        dict: {"social": Verhaltensbeobachtung SK, "verbal": Verhaltensbeobachtung VK}
    """

    # Echte AC-Beobachtungen-Bausteine (behavioral descriptors)
    sk_observations = [
        f"{name} initiierte Diskussion mit Frage an zwei Gruppenmitglieder. Notierte deren Aussagen wörtlich mit.",
        f"{name} sprach ca. 35% der Redezeit. Bezog sich 3x auf vorherige Aussagen anderer Spieler.",
        f"In Konfliktsituation: {name} hörte Gegenposition zu Ende an, bot dann Kompromiss an. Alle akzeptierten Lösung.",
        f"{name} regelte Moderatorenrolle nach 10min ab. Bezog danach weniger sprechend, aber fragend andere ein.",
        f"{name} lehnte Vorschlag von xyz ab, begründete mit Zitataus Aufgabe. Zeigte beiden Richtungen später Respekt.",
        f"{name} betonte zweimal 'lass mich das verstehen' vor Reaktion. Stellte 6 Fragen, davon 4 an andere TN.",
        f"Bei Widerstand: {name} fragte nach Begründung, nicht nach Person. Schrieb Argumente auf Flipchart.",
        f"{name} lachte bei Ablehnung seines Vorschlags auf. Sagte 'ok, dann zeigen wir eine Alternative'. Tat das.",
    ]

    vk_observations = [
        f"{name} hatte ersten Plan (Lösung A), adaptierte nach Einwand zu Plan B. Kombinierte sp beiden Aspekte.",
        f"{name} traf Entscheidung 'Wir machen X' nach 5min Diskussion. Team folgte ohne Widerspruch. X war erfolgreich.",
        f"Bei Druck (Zeit-/Ressourcenlimit): {name} priorisierte 3 von 8 Aufgaben. Begründung schriftlich. Dann zügig.",
        f"{name} setzte sich durch: 'Das machen wir so' mit Blickkontakt, ruhige Stimme. Keine Aggression. Team setzte um.",
        f"Unter Zeitdruck: {name} atmete tief durch. Sprach deutlich langsamer. Gab Anweisungen strukturiert. Keine Hektik.",
        f"{name} organisierte: Verteilte Aufgaben auf 3 Personen. Notiert Abhängigkeiten. Check-in nach jedem Block.",
        f"{name} systematisch: Listen mit 'Pro/Contra'. Mit Nummern arbeitend. Streicht nachts rigoros Nicht-Essentielles.",
        f"{name} initiierte ohne Aufforderung: 'Wer macht was?' Schlug vor: Sie schreiben, ich moderiere, xyz rechnet.",
    ]

    prompt = f"""Du bist AC-Beobachter. Generiere 1 präzise Verhaltensbeschreibung für JEDE Dimension.

SOZIALE KOMPETENZ - konkrete Beobachtung (40-60 Wörter):
{random.choice(sk_observations)}

VERHALTENSKOMPETENZ - konkrete Beobachtung (40-60 Wörter):
{random.choice(vk_observations)}

Regel: NUR Verhaltensdeskriptoren, NICHT Interpretationen!
- ✅ "Sprach 2x länger als Schnitt, unterbrach 1x, stellte 4 Fragen"
- ❌ "War dominant und reflektiv"

Gib JSON zurück:
{{"social": "Beobachtung SK", "verbal": "Beobachtung VK"}}"""

    try:
        response = _call_ai_api(prompt, max_tokens=300, temperature=0.6)

        # Parse JSON-Response
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        result = json.loads(cleaned)
        click.echo(
            f"   📝 Beobachtungen generiert: SK={len(result.get('social',''))//10} Words, VK={len(result.get('verbal',''))//10} Words"
        )
        return result
    except Exception as e:
        click.echo(f"   ⚠️ Fehler bei Beobachtungstext: {e}. Nutze Fallback.")
        # Fallback mit echten Beobachtungen
        return {
            "social": random.choice(sk_observations),
            "verbal": random.choice(vk_observations),
        }


def generate_ki_text(category, name, observations_text):
    """
    DEPRECATED: Diese Funktion wird NICHT mehr verwendet.

    KI-Texte werden durch die normale KI-Analyse des Systems generiert,
    nicht durch den Test-Daten-Generator. Dies ermöglicht das Testen
    der implementierten KI-Analyse-Funktionalität.

    Die Funktion bleibt zur Rückwärts-Kompatibilität erhalten.
    """
    pass


def generate_self_assessment_text(name):
    """
    Generiert realistische Selbsteinschätzung aus Sicht des Teilnehmers.

    Args:
        name (str): Teilnehmername

    Returns:
        str: HTML-formatierter Selbsteinschätzungstext
    """
    prompt = f"""Schreibe eine authentische Selbstreflexion nach einem AC-Training.

Teilnehmer: {name}

STRUKTUR:
1. Was ist mir BEWUSST GEWORDEN über mich?
2. Was sind meine ERKANNTEN STÄRKEN (mit Bezug zu AC-Erlebnissen)?
3. Was möchte ich VERBESSERN?

REGELN:
- Ich-Perspektive (Ich bin mir bewusst, ich werde gesehen als, ich möchte)
- 140-180 Wörter
- HTML (p, strong, em nur)
- Authentisch, nicht zu perfekt
- Konkrete AC-Szenen referenzieren

Beispiel:
<p>Im Diskussionsteil wurde mir bewusst, dass ich andere oft unterbreche...</p>
<p><strong>Erkannte Stärken:</strong> Ich kann strukturiert vorgehen...</p>
<p><em>Entwicklungsziele:</em> Ich möchte mehr zuhören...</p>

Gib NUR HTML zurück."""

    try:
        response = _call_ai_api(prompt, max_tokens=400, temperature=0.8)
        result = response.strip()
        click.echo(f"   ✅ Selbsteinschätzung: {len(result)//10} Words")
        return result
    except Exception as e:
        click.echo(f"   ⚠️ Fehler bei Selbsteinschätzung: {e}")
        return (
            f"<p>Das AC-Training hat mir wertvolle Impulse gegeben. Besonders die Gruppenübungen waren aufschlussreich.</p>"
            f"<p><strong>Erkannte Stärken:</strong> Ich kann strukturiert planen und arbeite gerne im Team. "
            f"Anderen zuzuhören fällt mir leicht, und ich versuche, alle Sichtweisen einzubeziehen.</p>"
            f"<p><em>Entwicklungsziele:</em> Ich möchte assertiver werden und schneller Entscheidungen treffen. "
            f"Auch unter Druck möchte ich meine Ruhe bewahren.</p>"
        )


# =============================================================================
# Daten-Generierungsfunktionen
# =============================================================================


def _generate_ratings():
    """
    DEPRECATED: Diese Funktion wird NICHT mehr verwendet.

    Ratings werden durch die KI-Analyse des Systems generiert,
    nicht durch den Test-Daten-Generator. Dies ermöglicht das Testen
    der implementierten KI-Analyse-Funktionalität.

    Die Funktion bleibt zur Rückwärts-Kompatibilität erhalten.
    """
    pass


def _create_group(index):
    """Erstellt eine Gruppe mit Fake-Daten."""
    season = random.choice(FAKE_SEASONS)
    year = random.choice(FAKE_YEARS)
    city = random.choice(FAKE_CITIES)

    # Generiere zwei Namen für Leiter und Beobachter
    leiter_name = f"{random.choice(FAKE_FIRST_NAMES)} {random.choice(FAKE_LAST_NAMES)}"
    beobachter_name = (
        f"{random.choice(FAKE_FIRST_NAMES)} {random.choice(FAKE_LAST_NAMES)}"
    )

    group = Group(
        name=f"Trainingsgruppe {season} {year}",
        date_from=datetime.now(timezone.utc).date() - timedelta(days=random.randint(30, 180)),
        date_to=datetime.now(timezone.utc).date() + timedelta(days=random.randint(7, 60)),
        location=city,
        leitung_fremdeinschatzung=leiter_name,
        beobachter1=beobachter_name,
        leitung_selbsteinschatzung=leiter_name,
    )

    return group


def _create_participant(name, group):
    """
    Erstellt einen Teilnehmer mit Beobachtungen.

    Ratings und KI-Texte werden NICHT generiert - diese sollen durch die normale
    KI-Analyse des Systems erzeugt werden, um diese Funktionalität zu testen.
    """

    # Generiere Beobachtungstexte (echte AC-Beobachtungen)
    obs_data = generate_observation_text(name)

    # Hinweis: Ratings und KI-Texte bleiben LEER - werden später durch KI-Analyse generiert
    participant = Participant(
        name=name,
        group_id=group.id,
        observations=json.dumps(obs_data),
        sk_ratings=None,  # Wird durch KI-Analyse des Systems generiert
        vk_ratings=None,  # Wird durch KI-Analyse des Systems generiert
        ki_texts=None,  # Wird durch KI-Analyse des Systems generiert
        ki_raw_response=None,  # Wird durch KI-Analyse des Systems gefüllt
    )

    return participant


def _create_self_assessment(participant):
    """Erstellt eine Selbsteinschätzung."""
    return SelfAssessment(
        participant_id=participant.id,
        content=generate_self_assessment_text(participant.name),
    )


# =============================================================================
# Hauptfunktion: Testdaten generieren
# =============================================================================


def _generate_test_data(num_groups=2, participants_range=(8, 10), clear_existing=False):
    """
    Generiert synthetische Testdaten.

    Args:
        num_groups (int): Anzahl zu erstellender Gruppen
        participants_range (tuple): (min, max) Teilnehmer pro Gruppe
        clear_existing (bool): Alle Daten vorher löschen
    """
    click.echo("=" * 70)
    click.echo("🔧 Testdaten-Generator für Stärkenanalyse-App")
    click.echo("=" * 70)
    click.echo()
    click.echo("📋 Was wird generiert:")
    click.echo("   ✅ Gruppen (mit Leiter/Beobacher/Datum/Ort)")
    click.echo("   ✅ Teilnehmer (mit Namen)")
    click.echo("   ✅ Beobachtungsdaten (AC-konforme Verhaltensbeobachtungen)")
    click.echo("   ✅ Selbsteinschätzungen (Seelbreflexion, ~65% der TN)")
    click.echo(
        "   ❌ SK/VK-Ratings (sollen durch KI-Analyse des Systems generiert werden)"
    )
    click.echo(
        "   ❌ KI-Berichte (sollen durch KI-Analyse des Systems generiert werden)"
    )
    click.echo("   ❌ Abschlussberichte (sollen manuell designer/angepasst werden)")
    click.echo()

    # Prüfe, ob API verfügbar
    if not MISTRAL_CLIENT and not GenerativeModel:
        click.echo("⚠️ WARNUNG: Keine KI-API verfügbar!")
        click.echo("   Setze MISTRAL_API_KEY oder GOOGLE_API_KEY in .env")
        click.echo("   Fortfahren mit Fallback-Texten.")
        click.echo()

    # Lösche vorhandene Daten?
    if clear_existing:
        click.echo("🗑️ Lösche vorhandene Daten...")
        try:
            SelfAssessment.query.delete()
            Participant.query.delete()
            Group.query.delete()
            db.session.commit()
            click.echo("   ✅ Alle Gruppen/Teilnehmer gelöscht")
        except Exception as e:
            db.session.rollback()
            click.echo(f"   ❌ Fehler beim Löschen: {e}")
            return
        click.echo()

    # Konfiguration anzeigen
    click.echo(f"⚙️ Konfiguration:")
    click.echo(f"   • Gruppen: {num_groups}")
    click.echo(
        f"   • Teilnehmer pro Gruppe: {participants_range[0]}-{participants_range[1]}"
    )
    click.echo(f"   • Selbsteinschätzungen: ~65% der Teilnehmer")
    click.echo(f"   • KI-Berichte: NICHT generiert (werden vom System erzeugt)")
    click.echo()
    click.echo("🚀 Starte Generierung...")
    click.echo()

    total_participants = 0
    total_self_assessments = 0

    try:
        for group_num in range(1, num_groups + 1):
            # Erstelle Gruppe
            group = _create_group(group_num)
            db.session.add(group)
            db.session.flush()  # Generiere group_id

            num_participants = random.randint(*participants_range)
            click.echo(f"📁 Gruppe {group_num}/{num_groups}: {group.name}")

            # Erstelle Teilnehmer
            for p_num in range(1, num_participants + 1):
                # Generiere Namen
                first = random.choice(FAKE_FIRST_NAMES)
                last = random.choice(FAKE_LAST_NAMES)
                name = f"{first} {last}"

                # Erstelle Teilnehmer
                participant = _create_participant(name, group)
                db.session.add(participant)
                db.session.flush()  # Generiere participant_id

                # Selbsteinschätzung (~65% Wahrscheinlichkeit)
                has_self_assessment = random.random() < 0.65
                if has_self_assessment:
                    self_assessment = _create_self_assessment(participant)
                    db.session.add(self_assessment)
                    total_self_assessments += 1

                se_marker = " (+SE)" if has_self_assessment else ""
                click.echo(f"   👤 {p_num}/{num_participants}: {name}... ✅{se_marker}")

                total_participants += 1

            click.echo()

        # Commit alle Änderungen
        db.session.commit()

        # Erfolgsmeldung
        click.echo("=" * 70)
        click.echo("✅ Testdaten erfolgreich generiert!")
        click.echo("=" * 70)
        click.echo(f"📊 Statistik:")
        click.echo(f"   • {num_groups} Gruppen erstellt")
        click.echo(f"   • {total_participants} Teilnehmer generiert")
        pct = (
            int(total_self_assessments / total_participants * 100)
            if total_participants > 0
            else 0
        )
        click.echo(
            f"   • {total_self_assessments} Selbsteinschätzungen erstellt ({pct}%)"
        )
        click.echo()
        click.echo("ℹ️  Hinweis:")
        click.echo(
            "   • SK/VK-Ratings sind LEER - Sie können jetzt die KI-Analyse-Funktion testen!"
        )
        click.echo(
            "   • KI-Berichte sind LEER - Sie können jetzt die KI-Analyse-Funktion testen!"
        )
        click.echo(
            "   • Abschlussberichte existieren noch nicht - diese können dann designed werden"
        )
        click.echo()
        click.echo("🎯 Nächste Schritte:")
        click.echo("   1. App starten: python app.py")
        click.echo("   2. Dashboard öffnen: http://localhost:5001")
        click.echo("   3. KI-Analyse für Teilnehmer generieren und testen")
        click.echo()

    except Exception as e:
        db.session.rollback()
        click.echo()
        click.echo("=" * 70)
        click.echo(f"❌ Fehler bei Testdaten-Generierung: {e}")
        click.echo("=" * 70)
        raise


# =============================================================================
# Flask CLI Command
# =============================================================================


@click.command("generate-test-data")
@click.option(
    "--groups", default=2, help="Anzahl zu erstellender Gruppen (Standard: 2)"
)
@click.option(
    "--participants",
    default="8-10",
    help='Teilnehmer-Range pro Gruppe (z.B. "8-10", Standard: 8-10)',
)
@click.option(
    "--clear", is_flag=True, help="Alle Daten vor Generierung löschen (mit Bestätigung)"
)
@with_appcontext
def generate_test_data_command(groups, participants, clear):
    """
    Generiert synthetische Testdaten (Gruppen, Teilnehmer, Beobachtungen, Selbsteinschätzungen).

    KI-TEXTE und ABSCHLUSSBERICHTE werden NICHT generiert - diese sollen durch die
    normale KI-Analyse und das Bericht-System des Systems erzeugt werden, um diese
    Funktionalität zu testen.

    Beispiele:
        flask generate-test-data
        flask generate-test-data --groups 3 --participants 12-15
        flask generate-test-data --clear
    """
    # Parse participants-Range
    try:
        if "-" in participants:
            min_p, max_p = map(int, participants.split("-"))
        else:
            min_p = max_p = int(participants)

        if min_p < 1 or max_p < min_p:
            raise ValueError("Ungültige Teilnehmer-Range")
    except ValueError as e:
        click.echo(f"❌ Fehler: Ungültige --participants Option: {participants}")
        click.echo("   Erwartetes Format: '8-10' oder '10'")
        return

    # Bestätigung bei --clear
    if clear:
        click.echo("⚠️ WARNUNG: Alle Gruppen und Teilnehmer werden gelöscht!")
        if not click.confirm("Wirklich fortfahren?"):
            click.echo("Abgebrochen.")
            return

    # Starte Generierung
    _generate_test_data(
        num_groups=groups, participants_range=(min_p, max_p), clear_existing=clear
    )


def register_commands(app):
    """Registriert CLI-Commands in Flask-App."""
    app.cli.add_command(generate_test_data_command)
