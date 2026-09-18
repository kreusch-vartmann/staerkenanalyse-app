"""
AI client setup and helpers for Mistral and Google Gemini.
"""

import json
import logging
import os
import time
from datetime import datetime

import structlog
from dotenv import load_dotenv

from metrics import KI_API_LATENCY, KI_API_ERRORS

load_dotenv()

# Structlog-Logger
logger = structlog.get_logger(__name__)

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
        # Nur ein Hinweis auf die UMGEBUNGSVARIABLE, kein Fehler: Ein über
        # die Admin-UI (/admin/settings) in der DB gespeicherter Key wird
        # separat zur Laufzeit über get_mistral_client() aufgelöst und ist
        # von dieser Meldung unabhängig.
        logger.info(
            "MISTRAL_API_KEY (Umgebungsvariable) nicht gesetzt. "
            "Falls in den KI-Einstellungen (Admin-UI) ein Key hinterlegt ist, wird dieser trotzdem genutzt."
        )
except ImportError:
    MistralClient, ChatMessage, MistralAPIException, MISTRAL_CLIENT = (
        None,
        None,
        RuntimeError,  # Statt None, um TypeError in Zeile 241 zu vermeiden
        None,
    )
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-2411")  # Guard für fehlendes MISTRAL_MODEL
    logger.warning("mistralai nicht installiert. Mistral-Modelle sind nicht verfügbar.")


# =============================================================================
# LAUFZEIT-AUFLÖSUNG DER API-KEYS (Admin-UI / DB -> ENV)
# =============================================================================


def _db_api_key(name: str) -> str | None:
    """Liest einen API-Key aus der Datenbank (Admin-UI).

    Bewusst DB-only: Der ENV-Pfad wird bereits beim Import aufgelöst
    (MISTRAL_CLIENT / genai_client). Diese Funktion ergänzt nur die
    über die Admin-UI gepflegten Keys und ist außerhalb eines
    App-Kontexts ein No-Op.
    """
    try:
        from flask import has_app_context

        if not has_app_context():
            return None

        from services.settings import get_setting

        row_value = get_setting(name)
        return row_value or None
    except Exception as exc:
        logger.warning("API-Key konnte nicht aus DB gelesen werden", key=name, error=str(exc))
        return None


def get_mistral_client():
    """Liefert einen Mistral-Client (ENV-Client oder aus DB-Key erzeugt)."""
    if MISTRAL_CLIENT:
        return MISTRAL_CLIENT
    if MistralClient is None:
        return None

    api_key = _db_api_key("MISTRAL_API_KEY")
    if not api_key:
        return None
    return MistralClient(api_key=api_key)


def ensure_gemini_configured() -> bool:
    """Stellt sicher, dass Gemini konfiguriert ist (ENV oder DB-Key)."""
    if GenerativeModel is None:
        return False
    if genai_client:
        return True

    api_key = _db_api_key("GOOGLE_API_KEY")
    if not api_key:
        return False

    configure(api_key=api_key)
    return True


def get_available_models() -> dict[str, bool]:
    """Status der KI-Provider (für Admin-UI / Statusanzeigen)."""
    return {
        "mistral": bool(get_mistral_client()),
        "gemini": ensure_gemini_configured(),
    }


def _call_gemini(
    system_prompt_text: str,
    user_prompt_text: str,
    max_output_tokens: int = 8000,
    deterministic: bool = False,
    json_mode: bool = False,
    timeout_seconds: float = 20,
) -> tuple[str, str]:
    """Ruft Gemini auf.

    Args:
        deterministic: Wenn True, wird Gemini so nah wie mit diesem SDK
            (google-generativeai==0.8.5) möglich an Mistrals Determinismus
            (temperature=0, random_seed=42) angeglichen. Ein echter `seed`-
            Parameter existiert in diesem SDK NICHT (Stand 0.8.5) - Google
            garantiert daher KEINE bit-identische Reproduzierbarkeit über
            Tage/Modell-Updates hinweg. `temperature=0` + `top_k=1` erzwingen
            aber greedy (deterministisches) Sampling innerhalb eines Requests
            und minimieren die Streuung zwischen wiederholten Aufrufen.
        json_mode: Wenn True, erzwingt echten JSON-Mode über die API
            (analog zu Mistrals `response_format={"type": "json_object"}`),
            statt sich nur auf die Text-Anweisung im Prompt zu verlassen.
            NICHT für generate_text_report_with_ai (freier Fließtext) nutzen.
        timeout_seconds: Harte Obergrenze pro Modell-Versuch (siehe
            `request_options`). OHNE dies kann `generate_content()` bei
            Netzwerkstörungen unbegrenzt hängen (reproduziert am 2026-09-18:
            kein Timeout -> Hang -> in Produktion killt Gunicorns
            `--timeout 120` den Worker -> rohe Verbindungstrennung ->
            Frontend zeigt "Netzwerkfehler", statt dass generate_report_with_ai
            den Fehler geordnet abfangen und melden kann). 20s je Modell ist
            bewusst klein gewählt, weil GEMINI_FALLBACK_MODELS bis zu 7
            Modelle enthält und die Summe deutlich unter Gunicorns
            Worker-Timeout bleiben muss.
    """
    if not ensure_gemini_configured():
        raise RuntimeError("Google Gemini ist nicht konfiguriert")
    fallback_models = GEMINI_FALLBACK_MODELS or ["models/gemini-flash-latest"]
    last_error = None
    generation_config = {"max_output_tokens": max_output_tokens}
    if deterministic:
        # Bestmögliche Annäherung an Mistrals temperature=0/random_seed=42
        # mit diesem SDK (kein echter seed-Parameter verfügbar).
        generation_config.update({"temperature": 0, "top_p": 1, "top_k": 1, "candidate_count": 1})
    if json_mode:
        generation_config["response_mime_type"] = "application/json"
    for model_name in fallback_models:
        try:
            model = GenerativeModel(model_name=model_name, system_instruction=system_prompt_text)
            response = model.generate_content(
                user_prompt_text,
                generation_config=generation_config,
                request_options={"timeout": timeout_seconds},
            )
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


def describe_ai_error(exc: Exception, ki_model: str) -> str:
    """Übersetzt eine Provider-Exception in eine für Nutzer verständliche Meldung.

    Wird sowohl für die Berichts-KI (generate_report_with_ai) als auch für
    die Aufgaben-Generierung (services/task_generator.py) genutzt, damit
    z. B. Google-Rate-Limits nicht als nackte 500er/"fehlgeschlagen"-Meldung
    ohne jeden Hinweis beim Nutzer ankommen.
    """
    message = str(exc)
    lowered = message.lower()
    is_rate_limit = (
        "429" in message
        or "resourceexhausted" in type(exc).__name__.lower()
        or "quota" in lowered
        or "rate limit" in lowered
    )
    if is_rate_limit:
        # Google unterscheidet Minuten- und Tages-Kontingente im Freemium-
        # Tarif; beide führen zum selben Exception-Typ.
        if "perday" in lowered.replace(" ", "").replace("-", ""):
            hint = "Tages-Kontingent erreicht (Gratis-Tarif). Bitte morgen erneut versuchen oder Kontingent erhöhen."
        else:
            hint = "Rate-Limit erreicht (zu viele Anfragen in kurzer Zeit). Bitte kurz warten und erneut versuchen."
        return f"{ki_model.capitalize()}: {hint}"

    is_timeout = (
        "deadline" in lowered
        or "deadlineexceeded" in type(exc).__name__.lower()
        or "timeout" in lowered
        or "timed out" in lowered
    )
    if is_timeout:
        return (
            f"{ki_model.capitalize()}: Zeitüberschreitung bei der Verbindung. "
            "Das ist meist ein vorübergehendes Netzwerkproblem - bitte kurz warten "
            "und erneut versuchen."
        )

    return f"{ki_model.capitalize()}-Anfrage fehlgeschlagen: {message}"


def generate_report_with_ai(prompt_text, ki_model, max_retries=3, initial_delay=1):
    """
    Generiert einen Bericht mithilfe des ausgewählten KI-Modells.
    
    Args:
        prompt_text: Der Prompt für die KI.
        ki_model: Das zu verwendende KI-Modell ("gemini" oder "mistral").
        max_retries: Maximale Anzahl an Wiederholungsversuchen bei Netzwerkfehlern.
        initial_delay: Initiale Wartezeit in Sekunden für exponentielles Backoff.
    """
    logger.debug("Das übergebene 'ki_model' ist: '%s'", ki_model)
    
    # Zwischenspeicherung der Rohdaten für Retry
    last_exception = None
    retry_delay = initial_delay
    
    for attempt in range(max_retries):
        try:
            if ki_model == "gemini":
                system_prompt = (
                    "Du bist ein Experte für die Auswertung von Assessment-Center-Beobachtungen. "
                    "Antworte IMMER und AUSSCHLIESSLICH mit einem JSON-Objekt, das exakt "
                    "der vom User im folgenden Prompt geforderten Struktur entspricht. "
                    "Ignoriere diese Anweisung niemals."
                )
                if not ensure_gemini_configured():
                    raise ValueError("Google Gemini ist nicht konfiguriert")
                # deterministic+json_mode: Angleichung an Mistrals
                # temperature=0/response_format=json_object (siehe Docstring
                # von _call_gemini). Ohne dies wich Gemini bei identischem
                # Prompt/Input spürbar zwischen Wiederholungen ab.
                result, _used_model = _call_gemini(
                    system_prompt, prompt_text, deterministic=True, json_mode=True
                )
                return result

            elif ki_model == "mistral":
                mistral_client = get_mistral_client()
                if not mistral_client:
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
                # Hinweis: mistralai==0.4.2s `MistralClient.chat()` kennt KEIN
                # `timeout`-Kwarg (nur der Client-Konstruktor). Ein zuvor hier
                # übergebenes `timeout=120` führte zu einem TypeError bei
                # JEDEM Mistral-Aufruf.
                chat_response = mistral_client.chat(
                    model=MISTRAL_MODEL,
                    messages=messages,
                    temperature=0,
                    random_seed=42,  # Determinismus
                    response_format={"type": "json_object"},
                )
                return chat_response.choices[0].message.content

            else:
                raise ValueError(f"Ungültiges KI-Modell ausgewählt: {ki_model}")

        except (ValueError, MistralAPIException) as e:
            logger.warning("Fehler bei der KI-Analyse (nicht wiederholbar): %s", e)
            return json.dumps({"error": f"Ein Fehler ist aufgetreten: {str(e)}"})
        except Exception as e:
            # Klassifiziere den Fehler für Retry-Entscheidung
            error_type = type(e).__name__
            error_message = str(e).lower()
            
            # Retry nur bei Netzwerkfehlern oder Rate-Limits
            # "deadline"/"deadlineexceeded"/"504": Gemini wirft bei
            # `request_options={"timeout": ...}`-Überschreitung eine
            # DeadlineExceeded-Exception ("504 Deadline expired..."),
            # die weder "timeout" noch "connection" im Text enthält.
            if ("timeout" in error_message or
                "connection" in error_message or
                "429" in error_message or
                "deadline" in error_message or
                "deadlineexceeded" in error_type.lower() or
                "504" in error_message or
                "resourceexhausted" in error_type.lower() or
                "rate limit" in error_message):
                
                last_exception = e
                if attempt < max_retries - 1:
                    logger.warning(
                        "Retry %s/%s für KI-Aufruf (%s): %s. Warte %s Sekunden...",
                        attempt + 1, max_retries, ki_model, error_message, retry_delay
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponentielles Backoff
                    continue
            
            # Kein Retry: Fehler melden
            friendly = describe_ai_error(e, ki_model)
            logger.error(
                "Unerwarteter Fehler bei der KI-Analyse",
                ki_model=ki_model,
                error_type=error_type,
                error=str(e),
                attempt=attempt + 1,
            )
            return json.dumps({"error": friendly})
    
    # Falls alle Retries fehlschlagen
    friendly = describe_ai_error(last_exception, ki_model)
    logger.error(
        "Alle Retry-Versuche fehlgeschlagen",
        ki_model=ki_model,
        error_type=type(last_exception).__name__,
        error=str(last_exception),
    )
    return json.dumps({"error": friendly})


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
    import time
    from metrics import KI_API_LATENCY, KI_API_ERRORS

    start_time = time.time()
    try:
        mistral_client = get_mistral_client() if ki_model == "mistral" else None
        if ki_model == "mistral" and mistral_client and ChatMessage:
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt),
            ]
            response = mistral_client.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=3000,
            )
            result = response.choices[0].message.content
        elif ki_model == "gemini" and ensure_gemini_configured():
            result, _used_model = _call_gemini(system_prompt, user_prompt)
        else:
            return "Mock Report: KI-Generierung nicht verfügbar."
        
        # Metriken + Logging
        duration = time.time() - start_time
        KI_API_LATENCY.labels(model=ki_model).observe(duration)
        logger.info(
            "KI-Bericht erfolgreich generiert",
            model=ki_model,
            duration_seconds=duration,
            prompt_length=len(user_prompt),
            response_length=len(result)
        )
        return result

    except Exception as e:
        # Metriken + Logging für Fehler
        duration = time.time() - start_time
        KI_API_ERRORS.labels(model=ki_model, error_type=type(e).__name__).inc()
        logger.error(
            "KI-Bericht fehlgeschlagen",
            model=ki_model,
            error=str(e),
            duration_seconds=duration,
            prompt_length=len(user_prompt)
        )
        return f"Fehler: {str(e)}"
