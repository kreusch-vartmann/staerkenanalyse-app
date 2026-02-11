"""
Task refinement using AI models.
"""

import logging
import re

from services.ai_client import MISTRAL_CLIENT, MISTRAL_MODEL, genai_client, _call_gemini
from services.task_normalization import (
    _clean_html_output,
    _ensure_all_sections_filled,
    _normalize_task_html,
    _validate_task_content,
)

logger = logging.getLogger(__name__)


def refine_task_content(
    draft_content: str,
    user_request: str,
    conversation_history: list | None = None,
    ki_model: str = "mistral",
) -> dict:
    """
    Verfeinere Task-Content basierend auf User-Input (Chat-Iteration).
    """
    if not draft_content or len(draft_content.strip()) < 200:
        return {
            "ai_response": "Fehler: Die aktuelle Aufgabe ist leer oder zu kurz. Bitte erstelle zuerst eine vollständige Aufgabe.",
            "updated_content": draft_content or "",
        }

    system_prompt = """Du bist ein Experte für einfache Assessment-Center-Gruppenübungen.

DEINE AUFGABE:
Nimm die bestehende Aufgabe, wende die gewünschte Änderung an, und gib die VOLLSTÄNDIGE überarbeitete Aufgabe zurück.

REGELN:
1. Gib die KOMPLETTE Aufgabe mit ALLEN Sektionen zurück (nicht nur die Änderung!)
2. Alle bestehenden Sektionen müssen erhalten bleiben und gefüllt sein
3. Halte die Aufgabe EINFACH - Assessment-Center-Übungen sind kurz und klar
4. Das Szenario soll 3-5 Sätze haben (nicht länger!)
5. Die Aufgabenstellung soll 1-2 Sätze sein (KEINE nummerierten Unterpunkte!)

FORMATIERUNG - NUR HTML:
- <h2> für Titel, <h3> für Sektionsüberschriften
- <p> für Textabsätze
- <ol><li> für Ablauf-Phasen, <ul><li> für Listen
- <strong> für Hervorhebungen

ABSOLUT VERBOTEN:
- Markdown-Formatierung: NIEMALS ** oder __ oder # verwenden!
- Leere Sektionen ohne Inhalt
- Nummerierte Aufzählungen als Fließtext (1. **Punkt:** ... 2. **Punkt:** ...)
- Text vor oder nach dem HTML-Code
- Markdown Code-Blöcke (```)

Antworte NUR mit dem kompletten HTML-Code der überarbeiteten Aufgabe!"""

    history_text = ""
    if conversation_history:
        for msg in conversation_history[-2:]:
            history_text += f"User: {msg.get('user', '')}\n"

    conversation_section = ""
    if history_text:
        conversation_section = f"BISHERIGE KONVERSATION:\n{history_text}\n---\n"

    user_prompt = f"""AKTUELLE AUFGABE (vollständiger HTML-Content):
{draft_content}

---

GEWÜNSCHTE ÄNDERUNG:
{user_request}

{conversation_section}
WICHTIG: Nimm die KOMPLETTE aktuelle Aufgabe, wende die Änderung an, und gib die GESAMTE verbesserte Aufgabe zurück!
Nicht nur die Änderungen - die VOLLSTÄNDIGE Aufgabe mit ALLEM Content in allen Sektionen!

ANTWORTE NUR MIT DEM KOMPLETTEN HTML-CODE - NICHTS ANDERES!"""

    try:
        temperatures = [0.5, 0.3]
        updated_html = None

        for attempt, temp in enumerate(temperatures, 1):
            logger.debug("REFINE_TASK_CONTENT ATTEMPT %s (temp=%s)", attempt, temp)

            if ki_model == "mistral" and MISTRAL_CLIENT:
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
                result = response.choices[0].message.content

            elif ki_model == "gemini" and genai_client:
                result, _used_model = _call_gemini(system_prompt, user_prompt, max_output_tokens=8000)

            else:
                return {
                    "ai_response": f"Verstanden. Ich verfeinere basierend auf: {user_request}",
                    "updated_content": draft_content,
                }

            logger.debug("Response length: %s chars", len(result))
            logger.debug("Raw Response (first 600 chars): %s...", result[:600])

            cleaned = result.strip()

            if '```' in cleaned:
                code_block_match = re.search(r'```(?:html)?\s*\n?(.*?)\n?```', cleaned, re.DOTALL)
                if code_block_match:
                    cleaned = code_block_match.group(1).strip()
                elif cleaned.startswith('```'):
                    lines = cleaned.split('\n')
                    if lines[0].startswith('```'):
                        lines = lines[1:]
                    if lines and lines[-1].strip().startswith('```'):
                        lines = lines[:-1]
                    cleaned = '\n'.join(lines).strip()

            if '<' in cleaned:
                html_start = cleaned.find('<')
                if html_start > 0:
                    cleaned = cleaned[html_start:]

                last_bracket = cleaned.rfind('>')
                if last_bracket > 0:
                    cleaned = cleaned[:last_bracket + 1]

            cleaned = _clean_html_output(cleaned)
            cleaned = _normalize_task_html(cleaned)
            cleaned = _ensure_all_sections_filled(cleaned, draft_content)

            is_valid, reason = _validate_task_content(cleaned)

            logger.debug("Cleaned HTML (first 400 chars): %s...", cleaned[:400])

            if is_valid:
                updated_html = cleaned
                logger.info("Versuch %s erfolgreich", attempt)
                break
            logger.warning("Versuch %s fehlgeschlagen: %s", attempt, reason)

        if not updated_html:
            logger.warning("Keine vollständige KI-Antwort, verwende Original")
            updated_html = draft_content

        updated_html = _clean_html_output(updated_html)

        ai_response = f"Aufgabe wurde angepasst: {user_request}"

        return {
            "ai_response": ai_response,
            "updated_content": updated_html,
        }

    except Exception as e:
        logger.exception("Exception in refine_task_content: %s", e)
        return {
            "ai_response": f"Fehler bei der Verarbeitung: {str(e)}",
            "updated_content": draft_content,
        }
