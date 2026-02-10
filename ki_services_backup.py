"""
Dieses Modul enthält Funktionen zur Integration und Nutzung von KI-Modellen
für die Berichtserstellung.
"""

import json
import os

from dotenv import load_dotenv

# Lade die Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Versuche, die notwendigen Bibliotheken zu importieren und zu konfigurieren
try:
    from google.api_core import exceptions as google_exceptions
    from google.generativeai import GenerativeModel, configure, list_models

    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if GOOGLE_API_KEY:
        configure(api_key=GOOGLE_API_KEY)
    else:
        print(
            "WARNUNG: GOOGLE_API_KEY nicht gefunden. Google-Modelle sind nicht verfügbar."
        )
except ImportError:
    GenerativeModel, list_models, google_exceptions = None, None, None
    print(
        "WARNUNG: google-generativeai nicht installiert. Google-Modelle nicht verfügbar."
    )

try:
    from mistralai.client import MistralClient
    from mistralai.exceptions import MistralAPIException
    from mistralai.models.chat_completion import ChatMessage

    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_CLIENT = MistralClient(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None
    if not MISTRAL_API_KEY:
        print(
            "WARNUNG: MISTRAL_API_KEY nicht gefunden. Mistral-Modelle sind nicht verfügbar."
        )
except ImportError:
    MistralClient, ChatMessage, MistralAPIException, MISTRAL_CLIENT = (
        None,
        None,
        None,
        None,
    )
    print("WARNUNG: mistralai nicht installiert. Mistral-Modelle nicht verfügbar.")


def generate_report_with_ai(prompt_text, ki_model):
    """
    Generiert einen Bericht mithilfe des ausgewählten KI-Modells.
    Nutzt einen festen System-Prompt für die JSON-Struktur und den User-Prompt
    für die inhaltlichen Anweisungen.
    """
    print(f"--- DEBUG-INFO: Das übergebene 'ki_model' ist: '{ki_model}' ---")
    try:
        if ki_model == "gemini":
            if not GenerativeModel:
                raise ValueError(
                    "Die 'Google Generative AI'-Bibliothek ist nicht installiert."
                )

            # KORREKTUR: Flash-Modell verwenden (schneller, höheres Free-Tier-Kontingent)
            model_name = "models/gemini-flash-latest"
            try:
                model = GenerativeModel(model_name)
                response = model.generate_content(prompt_text)
                return response.text
            except (google_exceptions.GoogleAPICallError, Exception) as e:
                print(f"!!! FEHLER BEI ANFRAGE AN GEMINI ('{model_name}') !!!\n{e}")
                _try_list_available_gemini_models(model_name, e)

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
                model="mistral-large-latest",
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            return chat_response.choices[0].message.content

        raise ValueError(f"Ungültiges KI-Modell ausgewählt: {ki_model}")

    except (ValueError, MistralAPIException) as e:
        print(f"!!! FEHLER BEI DER KI-ANALYSE !!!\n{e}")
        return json.dumps({"error": f"Ein Fehler ist aufgetreten: {str(e)}"})


def _try_list_available_gemini_models(model_name, original_exception):
    """
    Versucht bei einem Fehler, verfügbare Modelle aufzulisten und wirft dann einen Fehler.
    """
    if not list_models:
        raise ValueError(
            "Kommunikation mit Gemini fehlgeschlagen. Funktion zum Auflisten "
            "der Modelle ist nicht verfügbar."
        ) from original_exception

    try:
        print("\n--- VERSUCHE, VERFÜGBARE MODELLE AUFZULISTEN ---")
        available_models = [
            m.name
            for m in list_models()
            if "generateContent" in m.supported_generation_methods
        ]

        if available_models:
            print("Folgende Modelle sind für deinen API-Key verfügbar und nutzbar:")
            for name in available_models:
                print(f"- {name}")
            print("----------------------------------------------------")
            raise ValueError(
                f"Das Modell '{model_name}' hat nicht funktioniert. Bitte versuche eines "
                "der oben gelisteten Modelle in der 'ki_services.py'."
            ) from original_exception

        print(
            "Es konnten keine verfügbaren Modelle für deinen API-Key gefunden werden."
        )
        raise ValueError(
            "Keine kompatiblen Gemini-Modelle für deinen API-Key gefunden."
        ) from original_exception

    except Exception as list_models_error:
        print(f"Fehler beim Auflisten der verfügbaren Modelle: {list_models_error}")
        raise ValueError(
            "Die Kommunikation mit dem Gemini-Modell ist fehlgeschlagen."
        ) from list_models_error


# =============================================================================
# Phase 2: Task Generation (B4 & B6)
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
        context_data: Dict mit Metadaten (z.B. use_example)
        example_tasks: Dict mit Reference-Aufgaben
        ki_model: "mistral" oder "gemini"
    
    Returns:
        {"title": "...", "content": "<html>", "observation_focus": "..."}
    """
    
    context_data = context_data or {}
    
    # Bestimme KI basierend auf Beobachtungsbereich
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
    
    # System-Prompt mit Best-Practice Knowledge
    system_prompt = f"""
Du bist ein zertifizierter Assessment-Center Manager und Experte für Stärken-based Assessment.
Du kennst Best Practices für die Gestaltung von:
- Gruppen-Diskussionsaufgaben mit realistischen Szenarien
- Kreativ- und Kooperations-Aufgaben
- Delegations- und Entscheidungsaufgaben
- Verhandlungs- und Moderations-Szenarien

Deine Aufgabe: Generiere professionelle AC-Aufgaben, die STÄRKEN eines Einzelnen in Gruppenumgebung sichtbar machen.
NICHT: Stress-Szenarien oder Konfrontation-Tests - konzentriere dich auf Potentialentwicklung.

Beobachtungsbereich: {observation_area}
Definition: {area_spec['definition']}

OUTPUT-FORMAT (WICHTIG):
```json
{{
  "title": "Kurzer Aufgaben-Titel",
  "content": "<html mit Quill.js-kompatiblem Markup>",
  "observation_focus": "Konkrete Beobachtungskriterien und Signale",
  "facilitator_notes": "Tipps für Moderatoren zur Beobachtung"
}}
```

CONTENT-STRUKTUR:
<h2>Auftrag</h2>
<p>Kurze aussagekräftige Beschreibung des Szenarios</p>
<h3>Ablauf</h3>
<ol><li>Phase 1 (Xx Min): ...</li>...</ol>
<h3>Unterlagen</h3>
<p>Liste verfügbare Materialien/Szenarien</p>
"""
    
    # Beispiele als Context
    examples_text = ""
    if example_tasks:
        examples_text = "\n\nREFERENCE EXAMPLES (gleiche Domain):\n"
        for key, example in example_tasks.items():
            if example.get("observation_area") == observation_area:
                examples_text += f"""
Beispiel: {example['title']}
- Teilnehmer: {example.get('participant_count', '?')}
- Dauer: {example.get('duration_minutes', '?')} Min
- Fokus: {example.get('observation_focus', '')}

Content-Struktur:
{example.get('task_description', '')[:500]}...
"""
    
    user_prompt = f"""
Generiere eine Assessment-Center Aufgabe mit:
- Teilnehmerzahl: {participant_count}
- Dauer: {duration_minutes} Minuten  
- Bereich: {observation_area}

Anforderungen:
1. REALISTISCHES SZENARIO mit klarem Kontext
2. KLARE PHASEN mit Zeitangaben
3. BEOBACHTUNGSKRITERIEN die STÄRKEN identifizieren
4. Material/Ressourcen-Spezifikation
5. MODERATOR-NOTES für Beobachter
6. Professionelle Sprache, akademisch-sachlich

{examples_text}

Generiere eine NEUE, ORIGINELLE Aufgabe (nicht die Beispiele wiederholen).
Antworte mit gültigem JSON (no Markdown-Blöcke, direkt JSON).
"""
    
    try:
        if ki_model == "mistral" and MISTRAL_CLIENT:
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt)
            ]
            
            response = MISTRAL_CLIENT.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            response_text = response.choices[0].message.content
        
        elif ki_model == "gemini" and genai_client:
            model = genai_client.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=system_prompt
            )
            response = model.generate_content(user_prompt)
            response_text = response.text
        
        else:
            # Fallback - deutlich besserer Mock!
            response_text = f"""{{
  "title": "{observation_area} - Gruppenaufgabe",
  "content": "<h2>Auftrag: Gruppenaufgabe {observation_area}</h2><p>Dies ist ein Vorschlag der KI. Bitte passen Sie diesen an Ihre Bedürfnisse an.</p><h3>Ablauf</h3><ol><li>Planung (10 Min)</li><li>Durchführung ({max(20, duration_minutes-10)} Min)</li><li>Abschluss (5 Min)</li></ol>",
  "observation_focus": "{area_spec['focus']}",
  "facilitator_notes": "Achten Sie auf typische Verhaltensweisen in dieser Kompetenzdomäne"
}}"""
        
        # Parse JSON
        try:
            import json as json_lib
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json_lib.loads(json_str)
                return result
        except:
            pass
        
        # Fallback wenn JSON-Parsing scheitert
        return {
            "title": f"Aufgabe: {observation_area}",
            "content": f"<p>{response_text[:500]}...</p>",
            "observation_focus": area_spec['focus'],
            "facilitator_notes": "Manuelle Überprüfung empfohlen"
        }
    
    except Exception as e:
        print(f"Task generation error: {e}")
        return None
                ChatMessage(role="user", content=user_prompt),
            ]
            response = MISTRAL_CLIENT.chat(
                model="mistral-large-latest",
                messages=messages,
                temperature=0.7,
            )
            html_content = response.choices[0].message.content
            
            # Clean and validate HTML
            if html_content.startswith("```html"):
                html_content = html_content[7:-4].strip()
            elif html_content.startswith("```"):
                html_content = html_content[3:-3].strip()
            
            return {
                "content": html_content,
                "suggestions": [
                    "Füge praktisches Szenario hinzu",
                    "Include Bewertungskriterien",
                    "Definiere Erfolgsindikatoren"
                ]
            }
        
        elif ki_model == "gemini" and GenerativeModel:
            model = GenerativeModel("models/gemini-flash-latest")
            response = model.generate_content(user_prompt)
            html_content = response.text
            
            if html_content.startswith("```html"):
                html_content = html_content[7:-4].strip()
            elif html_content.startswith("```"):
                html_content = html_content[3:-3].strip()
            
            return {
                "content": html_content,
                "suggestions": [
                    "Füge praktisches Szenario hinzu",
                    "Include Bewertungskriterien",
                    "Definiere Erfolgsindikatoren"
                ]
            }
        
        else:
            # Fallback: return mock HTML
            return {
                "content": f"""
                    <h2>AC-Task: {observation_area}</h2>
                    <h3>Scenario</h3>
                    <p>Ein realistisches Geschäftsszenario für {participant_count} Teilnehmer</p>
                    <h3>Instructions</h3>
                    <p>Klare Anweisung der Aufgabe (Dauer: {duration} Min)</p>
                    <h3>Assessment Criteria</h3>
                    <ul>
                        <li>Kriterium 1</li>
                        <li>Kriterium 2</li>
                    </ul>
                """,
                "suggestions": [
                    "Refine scenario details",
                    "Add assessment rubric",
                    "Include observer notes"
                ]
            }
    
    except (ValueError, MistralAPIException, Exception) as e:
        print(f"ERROR generating task: {e}")
        return {
            "error": str(e),
            "content": "",
            "suggestions": []
        }


def refine_task_content(draft_content: str, user_request: str, conversation_history: list = None,
                       ki_model: str = "mistral") -> dict:
    """
    Iterativ verfeine Task-Content basierend auf User-Input (B8 Chat).
    
    Args:
        draft_content: Aktueller HTML-Inhalt
        user_request: User's Anfrage/Änderungswunsch
        conversation_history: Bisherige Chat-Messages
        ki_model: "mistral" oder "gemini"
    
    Returns:
        {"ai_response": "...", "updated_content": "..."}
    """
    system_prompt = (
        "Du bist ein AC Task-Design Expert. Der User verfeinert eine AC-Aufgabe. "
        "Antworte prägnant (2-3 Sätze) auf den Refinement-Wunsch und gib dann "
        "besseres HTML zurück. Nutze Quill-kompatibles HTML."
    )
    
    history_text = ""
    if conversation_history:
        for msg in conversation_history[-3:]:  # Last 3 messages
            history_text += f"User: {msg.get('user', '')}\nAssistant: {msg.get('ai', '')}\n\n"
    
    user_prompt = f"""
Current Task Content:
{draft_content}

User Request:
{user_request}

Previous Context:
{history_text if history_text else "None"}

Please:
1. Respond to the user's request (2-3 sentences)
2. Then provide updated HTML content

IMPORTANT: Return ONLY valid HTML, no markdown code blocks.
"""
    
    try:
        if ki_model == "mistral" and MISTRAL_CLIENT:
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt),
            ]
            response = MISTRAL_CLIENT.chat(
                model="mistral-large-latest",
                messages=messages,
                temperature=0.7,
            )
            result = response.choices[0].message.content
        elif ki_model == "gemini" and GenerativeModel:
            model = GenerativeModel("models/gemini-flash-latest")
            response = model.generate_content(user_prompt)
            result = response.text
        else:
            return {
                "ai_response": f"Verstanden. Ich verfeinere die Task basierend auf: {user_request}",
                "updated_content": f"<p>Verfeinert: {user_request}</p>\n{draft_content}"
            }
        
        # Parse response (simple split on double newline or delimiter)
        parts = result.split("\n\n", 1)
        ai_response = parts[0].strip() if parts else "Inhalt verfeinert"
        updated_html = parts[1].strip() if len(parts) > 1 else draft_content
        
        # Clean markdown code blocks if present
        if updated_html.startswith("```html"):
            updated_html = updated_html[7:-4].strip()
        elif updated_html.startswith("```"):
            updated_html = updated_html[3:-3].strip()
        
        return {
            "ai_response": ai_response,
            "updated_content": updated_html
        }
    
    except Exception as e:
        return {
            "ai_response": f"Fehler bei der Verarbeitung: {str(e)}",
            "updated_content": draft_content
        }
