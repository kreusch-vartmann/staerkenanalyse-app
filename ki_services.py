"""
KI-Integration für Berichtserstellung und Aufgaben-Generierung.
Unterstützt Mistral und Google Gemini APIs.
"""

import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

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
        print("WARNUNG: MISTRAL_API_KEY nicht gefunden. Mistral-Modelle sind nicht verf\u00fcgbar.")
except ImportError:
    MistralClient, ChatMessage, MistralAPIException, MISTRAL_CLIENT = (
        None,
        None,
        None,
        None,
    )
    print("WARNUNG: mistralai nicht installiert. Mistral-Modelle nicht verf\u00fcgbar.")


def _call_gemini(system_prompt_text: str, user_prompt_text: str) -> tuple[str, str]:
    if not genai_client:
        raise RuntimeError("Google Gemini ist nicht konfiguriert")
    last_error = None
    for model_name in GEMINI_FALLBACK_MODELS:
        try:
            model = GenerativeModel(model_name=model_name, system_instruction=system_prompt_text)
            response = model.generate_content(user_prompt_text)
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

def save_ai_raw_response(response_text: str, response_type: str, context_id: int, 
                         ki_model: str, observation_area: str = None, 
                         context_metadata: dict = None) -> int:
    """
    Speichert die unbearbeitete KI-Antwort für spätere Lernzwecke.
    
    Args:
        response_text: Originale KI-Antwort (unverändert)
        response_type: 'task' oder 'report'
        context_id: task_id oder participant_id
        ki_model: z.B. 'mistral-large-latest' oder 'gemini-flash-latest'
        observation_area: Optional, z.B. 'Soziale Kompetenzen'
        context_metadata: Optional, z.B. {'prompt': '...', 'temperature': 0.7}
    
    Returns:
        raw_response_id: ID des gespeicherten Records
    """
    from extensions import db
    from models import AIRawResponse
    
    try:
        raw_response = AIRawResponse(
            type=response_type,
            context_id=context_id,
            ki_model=ki_model,
            raw_response=response_text,
            processing_status='pending',
            observation_area=observation_area,
            context_metadata=context_metadata or {}
        )
        db.session.add(raw_response)
        db.session.flush()  # Get ID without committing
        
        print(f"   📦 KI-Gym: Raw response #{raw_response.id} gespeichert ({len(response_text)} chars)")
        
        return raw_response.id
    except Exception as e:
        print(f"   ⚠️  Fehler beim Speichern der Raw Response: {e}")
        # Non-critical: return None but don't break the main flow
        return None


def compute_content_diff(raw_content: str, final_content: str) -> dict:
    """
    Berechnet metrische Unterschiede zwischen Raw AI Output und finaler User-Version.
    
    Args:
        raw_content: Originale KI-Antwort
        final_content: Bearbeitete finale Version
    
    Returns:
        {
            'char_diff_percent': float (0-100),
            'char_diff_absolute': int,
            'length_change_percent': float,
            'structural_changes': str (summary),
            'edit_magnitude': str ('minor'|'moderate'|'major')
        }
    """
    import difflib
    from html.parser import HTMLParser
    
    # Simple Zeichenanzahl-Metriken
    raw_len = len(raw_content)
    final_len = len(final_content)
    char_diff = abs(raw_len - final_len)
    char_diff_percent = (char_diff / raw_len * 100) if raw_len > 0 else 0
    length_change_percent = ((final_len - raw_len) / raw_len * 100) if raw_len > 0 else 0
    
    # Sequence Matcher für Gesamtähnlichkeit
    similarity = difflib.SequenceMatcher(None, raw_content, final_content).ratio()
    similarity_percent = similarity * 100
    
    # Strukturelle Änderungen (einfache HTML Tag Zählung)
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
    except:
        structural_changes = "Konnte nicht berechnen"
    
    # Edit Magnitude Klassifikation
    if similarity_percent > 90 and char_diff_percent < 10:
        edit_magnitude = "minor"
    elif similarity_percent > 70 and char_diff_percent < 30:
        edit_magnitude = "moderate"
    else:
        edit_magnitude = "major"
    
    return {
        'char_diff_percent': round(char_diff_percent, 2),
        'char_diff_absolute': char_diff,
        'length_change_percent': round(length_change_percent, 2),
        'similarity_percent': round(similarity_percent, 2),
        'structural_changes': structural_changes,
        'edit_magnitude': edit_magnitude
    }


# =============================================================================
# BEOBACHTUNGSAUFGABEN-GENERIERUNG (NEUE FUNKTIONEN)
# =============================================================================

def generate_task(observation_area: str, participant_count: int, duration_minutes: int, 
                  context_data: dict = None, example_tasks: dict = None, ki_model: str = "mistral") -> dict:
    """
    Generiert professionelle Assessment-Center Aufgaben via KI.
    Spezialisiert auf Stärken-Assessment mit Best-Practice Knowledge.
    
    Args:
        observation_area: "Soziale Kompetenzen" oder "Verbale Kompetenzen"
        participant_count: 2-10 Teilnehmer
        duration_minutes: 30-60 Minuten
        context_data: Dict mit Metadaten
        example_tasks: Dict mit Reference-Aufgaben
        ki_model: "mistral" oder "gemini"
    
    Returns:
        {"title": "...", "content": "<html>", "observation_focus": "...", "_raw_response_id": <int>}
    """
    
    context_data = context_data or {}
    raw_response_id = None  # Will be set after AI call
    
    # Beobachtungsbereich-Spezifikation
    area_info = {
        "Soziale Kompetenzen": {
            "definition": "Fähigkeit zur Zusammenarbeit, Teamfähigkeit, Eigenverantwortung, Empathie, Konfliktbewältigung",
            "focus": "Beobachte: Gruppendynamik, Rollenverständnis, Umgang mit Differenzen, Unterstützung anderer"
        },
        "Verbale Kompetenzen": {
            "definition": "Argumentation, Überzeugungsfähigkeit, Redegewandtheit, Präsentation, Diskussionsfähigkeit",
            "focus": "Beobachte: Klarheit, Logik der Argumente, Überzeugungskraft, Fachkenntnis, Rhetorik"
        }
    }
    
    area_spec = area_info.get(observation_area, area_info["Soziale Kompetenzen"])
    
    # KI-Gym: Hole aktive Rules für Tasks
    try:
        import ai_gym
        active_rules = ai_gym.get_active_rules('task', observation_area)
        learned_rules_text = ai_gym.format_rules_for_prompt(active_rules)
    except Exception as e:
        print(f"   ⚠️  Konnte Rules nicht laden: {e}")
        learned_rules_text = ""
    
    system_prompt = f"""Du bist ein zertifizierter Assessment-Center Manager.
Generiere realistische AC-Aufgaben für Stärken-basierte Bewertung.
{learned_rules_text}
REGELN FÜR DEINE ANTWORT:
1. KEINE Markdown-Blöcke (kein ```, keine Formatierung)
2. REINES JSON, gültig und parsbar
3. Alle Strings mit korrekten Escapes ("Wort mit \"Anführung\"" z.B.)
4. Keine ungescapten Zeilenumbrüche in Strings (verwende \\n)
5. Valide HTML nur in "content" Feld

ANTWORTE NUR MIT DIESEM JSON (ohne extra Text):
{{
  "title": "Aufgabentitel",
  "content": "<h2>HTML Aufgabenbeschreibung</h2><p>...</p>",
  "observation_focus": "Was wird beobachtet",
  "facilitator_notes": "Moderator-Tipps"
}}

Beobachtungsbereich: {observation_area}
Definition: {area_spec['definition']}
Fokus: {area_spec['focus']}"""
    
    # Beispiele als Context
    examples_text = ""
    if example_tasks:
        for key, example in example_tasks.items():
            if example.get("observation_area") == observation_area:
                examples_text += f"\n- {example['title']}: {example.get('observation_focus', '')}"
    
    user_prompt = f"""Erstelle eine Assessment-Center Aufgabe mit diesen Parametern:

Teilnehmerzahl: {participant_count}
Dauer: {duration_minutes} Minuten
Bereich: {observation_area}

Beispiel-Aufgaben im gleichen Bereich:
{examples_text if examples_text else 'Folge den Best-Practice Richtlinien'}

Die Aufgabe MUSS enthalten:
- Realistisches Geschäftsszenario
- Klar definierte Rollen/Aufgaben für die Gruppe
- Phasen mit Zeitvorgaben (z.B. 10 Min Vorbereitung, 15 Min Durchführung)
- Was die Moderator:in beobachten soll
- Erforderliche Materialien

Gib SOFORT eine gültige JSON-Response ohne weitere Erklärung."""

    try:
        print(f"\n🤖 Starte KI-Generierung mit Model: {ki_model}")
        print(f"   Bereich: {observation_area}, Teilnehmer: {participant_count}, Dauer: {duration_minutes} Min\n")
        
        if ki_model == "mistral" and MISTRAL_CLIENT:
            print("   ➜ Verwende Mistral API...")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = MISTRAL_CLIENT.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            response_text = response.choices[0].message.content
            print(f"   ✓ Mistral antwortete {len(response_text)} Zeichen\n")
            
            # KI-Gym: Save raw response (context_id=0 will be updated later)
            raw_response_id = save_ai_raw_response(
                response_text=response_text,
                response_type='task',
                context_id=0,  # Placeholder - will be updated when task is created
                ki_model=MISTRAL_MODEL,
                observation_area=observation_area,
                context_metadata={
                    'temperature': 0.7,
                    'max_tokens': 2000,
                    'participant_count': participant_count,
                    'duration_minutes': duration_minutes
                }
            )
        
        elif ki_model == "gemini" and genai_client:
            print("   ➜ Verwende Google Gemini API...")
            response_text, used_model = _call_gemini(system_prompt, user_prompt)
            print(f"   ✓ Gemini ({used_model}) antwortete {len(response_text)} Zeichen\n")
            
            # KI-Gym: Save raw response
            raw_response_id = save_ai_raw_response(
                response_text=response_text,
                response_type='task',
                context_id=0,  # Placeholder
                ki_model=used_model,
                observation_area=observation_area,
                context_metadata={
                    'participant_count': participant_count,
                    'duration_minutes': duration_minutes
                }
            )
        
        else:
            # Fallback Mock mit Warnung
            print(f"   ⚠️  Keine KI verfügbar für '{ki_model}' - verwende Mock-Antwort")
            print(f"       (Mistral verfügbar: {bool(MISTRAL_CLIENT)}, Gemini verfügbar: {bool(genai_client)})\n")
            response_text = json.dumps({
                "title": f"Assessment-Aufgabe: {observation_area}",
                "content": f"<h2>{observation_area}</h2><h3>Ablauf</h3><ol><li>Vorbereitung (10 Min)</li><li>Durchführung ({duration_minutes-10} Min)</li></ol>",
                "observation_focus": area_spec['focus'],
                "facilitator_notes": "Achten Sie auf typische Verhaltensweisen in dieser Domäne"
            })
        
        # JSON Parsing (with markdown code block removal)
        # Remove markdown json code blocks if present
        response_clean = response_text.replace('```json', '').replace('```', '')
        
        json_start = response_clean.find('{')
        json_end = response_clean.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_clean[json_start:json_end]
            # Fix unescaped newlines in strings for proper JSON parsing
            # This handles HTML content with newlines
            try:
                result = json.loads(json_str)
                print(f"   ✓ JSON erfolgreich geparst: {result.get('title', 'Keine Titel')}\n")
                result['_raw_response_id'] = raw_response_id  # Add KI-Gym tracking
                return result
            except json.JSONDecodeError:
                # If direct parsing fails, try to fix common issues
                json_fixed = json_str.replace('\n', ' ')  # Replace newlines with spaces in overall structure first
                json_fixed = json_fixed.replace('  ', ' ')  # Collapse multiple spaces
                try:
                    result = json.loads(json_fixed)
                    print(f"   ✓ JSON erfolgreich geparst (nach Cleanup): {result.get('title', 'Keine Titel')}\n")
                    result['_raw_response_id'] = raw_response_id  # Add KI-Gym tracking
                    return result
                except json.JSONDecodeError as e:
                    print(f"   ⚠️  JSON Parse Error nach Cleanup: {e}\n")
        
        print(f"   ⚠️  Konnte JSON nicht extrahieren, verwende Fallback\n")
        return {
            "title": f"Aufgabe: {observation_area}",
            "content": f"<p>{response_text[:500]}</p>",
            "observation_focus": area_spec['focus'],
            "facilitator_notes": "Manuelle Überprüfung empfohlen",
            "_raw_response_id": raw_response_id
        }
    
    except Exception as e:
        print(f"\n❌ Task generation error: {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
        return None


def refine_task_content(draft_content: str, user_request: str, conversation_history: list = None,
                       ki_model: str = "mistral") -> dict:
    """
    Verfeinere Task-Content basierend auf User-Input (Chat-Iteration).
    """
    system_prompt = """Du bist AC Task-Design Expert. 
Der User verfeinert eine AC-Aufgabe. 
Antworte kurz (2-3 Sätze) auf die Anfrage, dann gib verbessertes HTML zurück.
WICHTIG: Nur HTML zurück, keine Markdown-Blöcke."""
    
    history_text = ""
    if conversation_history:
        for msg in conversation_history[-2:]:
            history_text += f"User: {msg.get('user', '')}\n"
    
    user_prompt = f"""Aktuelle Aufgabe:
{draft_content}

Anfrage:
{user_request}

Kontext:
{history_text if history_text else "Keine"}

Antworte kurz zur Anfrage, dann verbesseres HTML."""
    
    try:
        if ki_model == "mistral" and MISTRAL_CLIENT:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = MISTRAL_CLIENT.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                temperature=0.7
            )
            result = response.choices[0].message.content
        
        elif ki_model == "gemini" and genai_client:
            result, _used_model = _call_gemini(system_prompt, user_prompt)
        
        else:
            return {
                "ai_response": f"Verstanden. Ich verfeinere basierend auf: {user_request}",
                "updated_content": draft_content
            }
        
        # Parse response
        parts = result.split("\n\n", 1)
        ai_response = parts[0].strip() if parts else "Verfeinert"
        updated_html = parts[1].strip() if len(parts) > 1 else draft_content
        
        return {
            "ai_response": ai_response,
            "updated_content": updated_html
        }
    
    except Exception as e:
        return {
            "ai_response": f"Fehler: {str(e)}",
            "updated_content": draft_content
        }


def generate_report_with_ai(prompt_text, ki_model):
    """
    Generiert einen Bericht mithilfe des ausgewählten KI-Modells.
    Nutzt einen festen System-Prompt für die JSON-Struktur und den User-Prompt
    für die inhaltlichen Anweisungen.
    """
    print(f"--- DEBUG-INFO: Das übergebene 'ki_model' ist: '{ki_model}' ---")
    try:
        if ki_model == "gemini":
            system_prompt = (
                "Du bist ein Experte für die Auswertung von Assessment-Center-Beobachtungen. "
                "Antworte IMMER und AUSSCHLIESSLICH mit einem JSON-Objekt, das exakt "
                "der vom User im folgenden Prompt geforderten Struktur entspricht. "
                "Ignoriere diese Anweisung niemals."
            )
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

    except (ValueError, MistralAPIException) as e:
        print(f"!!! FEHLER BEI DER KI-ANALYSE !!!\n{e}")
        return json.dumps({"error": f"Ein Fehler ist aufgetreten: {str(e)}"})


def generate_text_report_with_ai(ki_texts: dict, ki_model: str = "mistral") -> str:
    """
    Generiert einen textuellen Gesamtbericht basierend auf KI-Insights.
    (Für KI-Gym Text-Reports, nicht für die strukturierte JSON-Analyse.)
    """
    system_prompt = "Du bist ein Berichtsschreiber für Stärkenanalysen. Verfasse prägnante, informative Reports."
    
    ki_contents = json.dumps(ki_texts, ensure_ascii=False, indent=2) if isinstance(ki_texts, dict) else str(ki_texts)
    
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
                ChatMessage(role="user", content=user_prompt)
            ]
            response = MISTRAL_CLIENT.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=3000
            )
            return response.choices[0].message.content
        
        elif ki_model == "gemini" and genai_client:
            result, _used_model = _call_gemini(system_prompt, user_prompt)
            return result
        
        else:
            return "Mock Report: KI-Generierung nicht verfügbar."
    
    except Exception as e:
        print(f"Report generation error: {e}")
        return f"Fehler: {str(e)}"
