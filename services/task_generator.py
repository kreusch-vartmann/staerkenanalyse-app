"""
Task generation using AI models.
"""

import ast
import json
import logging
import re

from services.task_knowledge_base import get_knowledge_for_prompt
from services.ai_client import (
    MISTRAL_CLIENT,
    MISTRAL_MODEL,
    genai_client,
    _call_gemini,
    save_ai_raw_response,
)
from services.task_normalization import (
    _clean_html_output,
    _normalize_task_html,
    _validate_task_content,
)

logger = logging.getLogger(__name__)


def _sanitize_json_string(raw_json: str) -> str:
    """Escapes control characters inside JSON strings and removes trailing commas."""
    result = []
    in_string = False
    escape = False
    for ch in raw_json:
        if escape:
            result.append(ch)
            escape = False
            continue
        if ch == "\\":
            result.append(ch)
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            result.append(ch)
            continue
        if in_string and ch in ("\n", "\r"):
            result.append("\\n")
            continue
        if in_string and ch == "\t":
            result.append("\\t")
            continue
        result.append(ch)
    cleaned = "".join(result)
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    return cleaned


def _maybe_unpack_json_content(parsed: dict) -> dict:
    """Wenn content fälschlich JSON enthält, versuche es zu entpacken."""
    content = parsed.get("content")
    if isinstance(content, str):
        text = content.strip()
        if text.startswith("{") and "\"content\"" in text and "\"title\"" in text:
            try:
                nested = json.loads(text)
                return {
                    "title": nested.get("title", parsed.get("title")),
                    "content": nested.get("content", parsed.get("content")),
                    "observation_focus": nested.get("observation_focus", parsed.get("observation_focus")),
                    "facilitator_notes": nested.get("facilitator_notes", parsed.get("facilitator_notes")),
                }
            except Exception:
                return parsed
        if text.startswith("{") and "'title'" in text and "'content'" in text:
            try:
                nested = ast.literal_eval(text)
                if isinstance(nested, dict):
                    return {
                        "title": nested.get("title", parsed.get("title")),
                        "content": nested.get("content", parsed.get("content")),
                        "observation_focus": nested.get("observation_focus", parsed.get("observation_focus")),
                        "facilitator_notes": nested.get("facilitator_notes", parsed.get("facilitator_notes")),
                    }
            except Exception:
                return parsed
    return parsed


def _extract_json_block(text: str) -> str | None:
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _parse_ai_response(response_text: str) -> dict | None:
    response_clean = response_text.replace('```json', '').replace('```', '')
    json_str = _extract_json_block(response_clean)
    if not json_str:
        return None
    try:
        result = json.loads(json_str)
        result = _maybe_unpack_json_content(result)
        return result
    except json.JSONDecodeError:
        json_fixed = _sanitize_json_string(json_str)
        try:
            result = json.loads(json_fixed)
            result = _maybe_unpack_json_content(result)
            return result
        except json.JSONDecodeError:
            return None


def generate_task(
    observation_area: str,
    participant_count: int,
    duration_minutes: int,
    context_data: dict | None = None,
    example_tasks: dict | None = None,
    ki_model: str = "mistral",
    target_group: str | None = None,
) -> dict | None:
    """
    Generiert professionelle Assessment-Center Aufgaben via KI.
    """

    context_data = context_data or {}
    raw_response_id = None

    if not target_group and context_data:
        target_group = context_data.get('target_group')

    area_info = {
        "Soziale Kompetenzen": {
            "definition": "Fähigkeit zur Zusammenarbeit, Teamfähigkeit, Eigenverantwortung, Empathie, Konfliktbewältigung",
            "focus": "Beobachte: Gruppendynamik, Rollenverständnis, Umgang mit Differenzen, Unterstützung anderer",
        },
        "Verbale Kompetenzen": {
            "definition": "Argumentation, Überzeugungsfähigkeit, Redegewandtheit, Präsentation, Diskussionsfähigkeit",
            "focus": "Beobachte: Klarheit, Logik der Argumente, Überzeugungskraft, Fachkenntnis, Rhetorik",
        },
    }

    area_spec = area_info.get(observation_area, area_info["Soziale Kompetenzen"])

    try:
        import ai_gym
        active_rules = ai_gym.get_active_rules('task', observation_area)
        learned_rules_text = ai_gym.format_rules_for_prompt(active_rules)
    except Exception as e:
        logger.warning("Konnte Rules nicht laden: %s", e)
        learned_rules_text = ""

    try:
        knowledge_context = get_knowledge_for_prompt(
            observation_area=observation_area,
            participant_count=participant_count,
            duration_minutes=duration_minutes,
            target_group=target_group,
        )
    except Exception as e:
        logger.warning("Knowledge Base nicht verfügbar: %s", e)
        knowledge_context = ""

    system_prompt = f"""Du bist ein erfahrener Assessment-Center-Gestalter.
Erstelle EINFACHE, KLARE AC-Gruppenübungen für Stärken-basierte Beobachtung.
{learned_rules_text}
{knowledge_context}

WICHTIG - EINFACHHEIT:
AC-Aufgaben sollen EINFACH und KLAR sein. KEINE komplexen Projekte mit vielen Unterpunkten!
Orientiere dich an diesen Beispielen:

BEISPIEL 1 (Erbengemeinschaft):
- Szenario: "Ihr seid eine Erbengemeinschaft und habt ein Haus geerbt. Eine Wohnung soll neu vermietet werden."
- Aufgabe: "Einigt euch in der Gruppe auf eine Mietpartei!"
- Ablauf: 3 Phasen (Vorbereitung 10 Min, Diskussion 30 Min, Abstimmung)
- Zusatzinfo: Liste der Interessenten

BEISPIEL 2 (Plakat):
- Szenario: "Das Sommerfest naht und ihr möchtet eure Gruppe präsentieren."
- Aufgabe: "Erstellt gemeinsam ein Plakat."
- Ablauf: 3 Phasen (Planung 10 Min, Gestaltung 30 Min, Präsentation 5 Min)
- Materialien: Flipchart-Papier, Stifte, Kleber, Schere

STRUKTUR DER AUFGABE:
1. Szenario: 3-5 Sätze, die die Ausgangssituation beschreiben (kurz und verständlich!)
2. Aufgabe: 1-2 Sätze, was die Gruppe konkret tun soll (KEIN Aufzählungsliste mit Unterpunkten!)
3. Ablauf: 3 Phasen mit Zeitangaben als nummerierte Liste
4. Zusatzinfos: Materialien ODER Rollenvorschläge ODER Szenarien-Details als einfache Liste

FORMATIERUNG - NUR HTML:
- <h2> für Titel, <h3> für Sektionsüberschriften
- <p> für Textabsätze
- <ol><li> für Ablauf-Phasen
- <ul><li> für Materialien/Listen
- <strong> für Hervorhebungen innerhalb von HTML-Tags

ABSOLUT VERBOTEN:
- Markdown-Formatierung: NIEMALS ** oder __ oder # verwenden!
- Nummerierte Aufzählungen im Aufgabentext (1. 2. 3. als Fließtext)
- Leere Sektionen ohne Inhalt
- Übermäßig komplexe Aufgaben mit mehr als 3 Diskussionspunkten
- Zu lange Szenarien (max 5 Sätze!)

JSON-FORMAT:
{{
  "title": "Kurzer Titel (3-6 Wörter)",
  "content": "<h2>Titel</h2><h3>Szenario</h3><p>Kurze Beschreibung...</p><h3>Eure Aufgabe</h3><p>Was ist zu tun...</p><h3>Ablauf</h3><ol><li>Phase 1...</li></ol><h3>Materialien</h3><ul><li>Item</li></ul>",
  "observation_focus": "Was wird beobachtet",
  "facilitator_notes": "Tipps für Moderatoren"
}}

WICHTIG:
- KEINE Markdown-Blöcke (```)
- KEIN Markdown (**, __, #, - als Aufzählung)
- REINES JSON, gültig und parsbar
- Alle Strings escaped
- Zeilenumbrüche als \n

Beobachtungsbereich: {observation_area}
Definition: {area_spec['definition']}
Fokus: {area_spec['focus']}"""

    examples_text = ""
    if example_tasks:
        for key, example in example_tasks.items():
            if example.get("observation_area") == observation_area:
                examples_text += f"\n- {example['title']}: {example.get('observation_focus', '')}"

    user_prompt = f"""Erstelle eine EINFACHE Assessment-Center Gruppenübung:

Teilnehmerzahl: {participant_count}
Dauer: {duration_minutes} Minuten
Bereich: {observation_area}
{f"Zielgruppe: {target_group}" if target_group else ""}

{f"Ähnliche Aufgaben: {examples_text}" if examples_text else ''}

Anforderungen:
- EINFACHES, alltägliches Szenario (3-5 Sätze, NICHT komplex!)
- Klare Gruppenaufgabe in 1-2 Sätzen (KEINE nummerierten Unterpunkte!)
- 3 Ablauf-Phasen mit Zeitangaben
- Materialien oder Rollenbeschreibungen
- KEIN Markdown (**, __, #) - NUR HTML-Tags verwenden!

Gib SOFORT NUR das JSON zurück - keine Erklärungen."""

    try:
        logger.info("Starte KI-Generierung mit Model: %s", ki_model)
        logger.info(
            "Bereich: %s, Teilnehmer: %s, Dauer: %s Min",
            observation_area,
            participant_count,
            duration_minutes,
        )

        parsed_result = None

        if ki_model == "mistral" and MISTRAL_CLIENT:
            logger.info("Verwende Mistral API...")
            for attempt, temp in enumerate([0.7, 0.2], start=1):
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                response = MISTRAL_CLIENT.chat(
                    model=MISTRAL_MODEL,
                    messages=messages,
                    temperature=temp,
                    max_tokens=8000,
                )
                response_text = response.choices[0].message.content
                logger.debug(
                    "Mistral antwortete %s Zeichen (Attempt %s)",
                    len(response_text),
                    attempt,
                )

                raw_response_id = save_ai_raw_response(
                    response_text=response_text,
                    response_type='task',
                    context_id=0,
                    ki_model=MISTRAL_MODEL,
                    observation_area=observation_area,
                    context_metadata={
                        'temperature': temp,
                        'max_tokens': 2000,
                        'participant_count': participant_count,
                        'duration_minutes': duration_minutes,
                        'attempt': attempt,
                    },
                )

                parsed_result = _parse_ai_response(response_text)
                if parsed_result and parsed_result.get("content"):
                    parsed_result['content'] = _clean_html_output(parsed_result['content'])
                    parsed_result['content'] = _normalize_task_html(
                        parsed_result['content'],
                        parsed_result.get('title'),
                    )
                    is_valid, reason = _validate_task_content(parsed_result['content'])
                    if is_valid:
                        parsed_result['_raw_response_id'] = raw_response_id
                        logger.info(
                            "JSON erfolgreich geparst: %s",
                            parsed_result.get('title', 'Keine Titel'),
                        )
                        return parsed_result
                    logger.warning(
                        "Content-Validierung fehlgeschlagen (Attempt %s): %s",
                        attempt,
                        reason,
                    )
                    parsed_result = None

        elif ki_model == "gemini" and genai_client:
            logger.info("Verwende Google Gemini API...")
            response_text, used_model = _call_gemini(system_prompt, user_prompt)
            logger.debug(
                "Gemini (%s) antwortete %s Zeichen",
                used_model,
                len(response_text),
            )

            raw_response_id = save_ai_raw_response(
                response_text=response_text,
                response_type='task',
                context_id=0,
                ki_model=used_model,
                observation_area=observation_area,
                context_metadata={
                    'participant_count': participant_count,
                    'duration_minutes': duration_minutes,
                },
            )
            parsed_result = _parse_ai_response(response_text)
            if parsed_result and parsed_result.get("content"):
                parsed_result['content'] = _clean_html_output(parsed_result['content'])
                parsed_result['content'] = _normalize_task_html(
                    parsed_result['content'],
                    parsed_result.get('title'),
                )
                is_valid, reason = _validate_task_content(parsed_result['content'])
                if is_valid:
                    parsed_result['_raw_response_id'] = raw_response_id
                    logger.info(
                        "JSON erfolgreich geparst: %s",
                        parsed_result.get('title', 'Keine Titel'),
                    )
                    return parsed_result
                logger.warning("Content-Validierung fehlgeschlagen: %s", reason)

        else:
            logger.warning("Keine KI verfügbar für '%s' - verwende Mock-Antwort", ki_model)
            logger.warning(
                "Mistral verfügbar: %s, Gemini verfügbar: %s",
                bool(MISTRAL_CLIENT),
                bool(genai_client),
            )
            response_text = json.dumps({
                "title": f"Assessment-Aufgabe: {observation_area}",
                "content": f"<h2>{observation_area}</h2><h3>Ablauf</h3><ol><li>Vorbereitung (10 Min)</li><li>Durchführung ({duration_minutes-10} Min)</li></ol>",
                "observation_focus": area_spec['focus'],
                "facilitator_notes": "Achten Sie auf typische Verhaltensweisen in dieser Domäne",
            })

        if parsed_result and parsed_result.get("content"):
            parsed_result['content'] = _clean_html_output(parsed_result['content'])
            parsed_result['content'] = _normalize_task_html(parsed_result['content'], parsed_result.get('title'))
            parsed_result['_raw_response_id'] = raw_response_id
            return parsed_result

        logger.warning("Konnte JSON nicht extrahieren, verwende Fallback")
        return {
            "title": f"Aufgabe: {observation_area}",
            "content": f"<p>{response_text[:500]}</p>",
            "observation_focus": area_spec['focus'],
            "facilitator_notes": "Manuelle Überprüfung empfohlen",
            "_raw_response_id": raw_response_id,
        }

    except Exception as e:
        logger.exception("Task generation error: %s: %s", type(e).__name__, e)
        return None
