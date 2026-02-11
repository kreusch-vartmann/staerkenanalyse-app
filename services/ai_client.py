"""
AI client setup and helpers for Mistral and Google Gemini.
"""

import json
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Google AI Setup
try:
    from google.generativeai import GenerativeModel, configure
    try:
        from google.api_core.exceptions import NotFound
    except ImportError:
        NotFound = None
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-flash-latest")
    GEMINI_FALLBACK_MODELS = [
        GEMINI_MODEL,
        "models/gemini-flash-latest",
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-flash-lite-latest",
        "models/gemini-pro-latest",
        "models/gemini-2.5-pro",
    ]
    GEMINI_FALLBACK_MODELS = [m for m in GEMINI_FALLBACK_MODELS if m]
    if GOOGLE_API_KEY:
        configure(api_key=GOOGLE_API_KEY)
        genai_client = True
    else:
        genai_client = None
except ImportError:
    GenerativeModel = None
    NotFound = None
    GEMINI_MODEL = None
    GEMINI_FALLBACK_MODELS = []
    genai_client = None

# Mistral Setup
try:
    from mistralai.client import MistralClient
    from mistralai.exceptions import MistralAPIException
    from mistralai.models.chat_completion import ChatMessage

    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
    if MISTRAL_API_KEY:
        MISTRAL_CLIENT = MistralClient(api_key=MISTRAL_API_KEY)
    else:
        MISTRAL_CLIENT = None
        logger.warning("MISTRAL_API_KEY nicht gefunden. Mistral-Modelle sind nicht verfügbar.")
except ImportError:
    MistralClient, ChatMessage, MistralAPIException, MISTRAL_CLIENT = (
        None,
        None,
        None,
        None,
    )
    logger.warning("mistralai nicht installiert. Mistral-Modelle nicht verfügbar.")


def _call_gemini(system_prompt_text: str, user_prompt_text: str, max_output_tokens: int = 8000) -> tuple[str, str]:
    if not genai_client or GenerativeModel is None:
        raise RuntimeError("Google Gemini ist nicht konfiguriert")
    last_error = None
    generation_config = {"max_output_tokens": max_output_tokens}
    for model_name in GEMINI_FALLBACK_MODELS:
        try:
            model = GenerativeModel(model_name=model_name, system_instruction=system_prompt_text)
            response = model.generate_content(user_prompt_text, generation_config=generation_config)
            return response.text, model_name
        except Exception as e:
            message = str(e).lower()
            if (NotFound and isinstance(e, NotFound)) or "not found" in message:
                last_error = e
                continue
            raise
    raise last_error if last_error else RuntimeError("Kein unterstütztes Gemini-Modell verfügbar")


# =============================================================================
# KI-GYM: RAW RESPONSE CAPTURE
# =============================================================================


def save_ai_raw_response(
    response_text: str,
    response_type: str,
    context_id: int,
    ki_model: str,
    observation_area: str | None = None,
    context_metadata: dict | None = None,
) -> int | None:
    """
    Speichert die unbearbeitete KI-Antwort für spätere Lernzwecke.
    """
    from extensions import db
    from models import AIRawResponse

    try:
        raw_response = AIRawResponse(
            type=response_type,
            context_id=context_id,
            ki_model=ki_model,
            raw_response=response_text,
            processing_status="pending",
            observation_area=observation_area,
            context_metadata=context_metadata or {},
        )
        db.session.add(raw_response)
        db.session.flush()

        logger.info(
            "KI-Gym: Raw response #%s gespeichert (%s chars)",
            raw_response.id,
            len(response_text),
        )

        return raw_response.id
    except Exception as e:
        logger.warning("Fehler beim Speichern der Raw Response: %s", e)
        return None


def compute_content_diff(raw_content: str, final_content: str) -> dict:
    """
    Berechnet metrische Unterschiede zwischen Raw AI Output und finaler User-Version.
    """
    import difflib
    from html.parser import HTMLParser

    raw_len = len(raw_content)
    final_len = len(final_content)
    char_diff = abs(raw_len - final_len)
    char_diff_percent = (char_diff / raw_len * 100) if raw_len > 0 else 0
    length_change_percent = ((final_len - raw_len) / raw_len * 100) if raw_len > 0 else 0

    similarity = difflib.SequenceMatcher(None, raw_content, final_content).ratio()
    similarity_percent = similarity * 100

    try:
        class TagCounter(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tags = []

            def handle_starttag(self, tag, attrs):
                self.tags.append(tag)

        raw_counter = TagCounter()
        final_counter = TagCounter()
        raw_counter.feed(raw_content)
        final_counter.feed(final_content)

        tag_diff = abs(len(raw_counter.tags) - len(final_counter.tags))
        structural_changes = f"{tag_diff} Tag-Änderungen" if tag_diff > 0 else "Keine strukturellen Änderungen"
    except Exception:
        structural_changes = "Konnte nicht berechnen"

    if similarity_percent > 90 and char_diff_percent < 10:
        edit_magnitude = "minor"
    elif similarity_percent > 70 and char_diff_percent < 30:
        edit_magnitude = "moderate"
    else:
        edit_magnitude = "major"

    return {
        "char_diff_percent": round(char_diff_percent, 2),
        "char_diff_absolute": char_diff,
        "length_change_percent": round(length_change_percent, 2),
        "similarity_percent": round(similarity_percent, 2),
        "structural_changes": structural_changes,
        "edit_magnitude": edit_magnitude,
    }


# =============================================================================
# Report generation helpers
# =============================================================================


def generate_report_with_ai(prompt_text, ki_model):
    """
    Generiert einen Bericht mithilfe des ausgewählten KI-Modells.
    """
    logger.debug("Das übergebene 'ki_model' ist: '%s'", ki_model)
    try:
        if ki_model == "gemini":
            system_prompt = (
                "Du bist ein Experte für die Auswertung von Assessment-Center-Beobachtungen. "
                "Antworte IMMER und AUSSCHLIESSLICH mit einem JSON-Objekt, das exakt "
                "der vom User im folgenden Prompt geforderten Struktur entspricht. "
                "Ignoriere diese Anweisung niemals."
            )
            if not genai_client or GenerativeModel is None:
                raise ValueError("Google Gemini ist nicht konfiguriert")
            result, _used_model = _call_gemini(system_prompt, prompt_text)
            return result

        elif ki_model == "mistral":
            if not MISTRAL_CLIENT:
                raise ValueError("Mistral Client nicht initialisiert. API-Key fehlt?")

            system_prompt = (
                "Du bist ein Experte für die Auswertung von Assessment-Center-Beobachtungen. "
                "Antworte IMMER und AUSSCHLIESSLICH mit einem JSON-Objekt, das exakt "
                "der vom User im folgenden Prompt geforderten Struktur entspricht. "
                "Ignoriere diese Anweisung niemals."
            )
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=prompt_text),
            ]
            chat_response = MISTRAL_CLIENT.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            return chat_response.choices[0].message.content

        raise ValueError(f"Ungültiges KI-Modell ausgewählt: {ki_model}")

    except (ValueError, MistralAPIException, RuntimeError) as e:
        logger.warning("Fehler bei der KI-Analyse: %s", e)
        return json.dumps({"error": f"Ein Fehler ist aufgetreten: {str(e)}"})


def generate_text_report_with_ai(ki_texts: dict, ki_model: str = "mistral") -> str:
    """
    Generiert einen textuellen Gesamtbericht basierend auf KI-Insights.
    """
    system_prompt = "Du bist ein Berichtsschreiber für Stärkenanalysen. Verfasse prägnante, informative Reports."

    ki_contents = (
        json.dumps(ki_texts, ensure_ascii=False, indent=2)
        if isinstance(ki_texts, dict)
        else str(ki_texts)
    )

    user_prompt = f"""Schreibe einen professionellen Analysebericht basierend auf diesen KI-Insights:

{ki_contents}

Anforderungen:
1. Sachlich-professioneller Ton
2. Fokus auf Stärken und Potenziale
3. Konkrete Beispiele
4. Handlungsempfehlungen
"""

    try:
        if ki_model == "mistral" and MISTRAL_CLIENT and ChatMessage:
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt),
            ]
            response = MISTRAL_CLIENT.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=3000,
            )
            return response.choices[0].message.content

        elif ki_model == "gemini" and genai_client:
            result, _used_model = _call_gemini(system_prompt, user_prompt)
            return result

        else:
            return "Mock Report: KI-Generierung nicht verfügbar."

    except Exception as e:
        logger.exception("Report generation error: %s", e)
        return f"Fehler: {str(e)}"
