"""
Modul für die Interaktion mit externen KI-Diensten (Google Gemini, Mistral).

Lädt sicher API-Schlüssel und stellt eine einheitliche Funktion zur
Generierung von Berichten zur Verfügung.
"""
import os
import json
from dotenv import load_dotenv

# Lade die Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Konfiguriere die KI-Modelle sicher
try:
    from google.generativeai import GenerativeModel, configure
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if GOOGLE_API_KEY:
        configure(api_key=GOOGLE_API_KEY)
    else:
        print("WARNUNG: GOOGLE_API_KEY nicht gefunden. Google-Modelle sind nicht verfügbar.")
except ImportError:
    GenerativeModel = None
    print("WARNUNG: google-generativeai nicht installiert. Google-Modelle nicht verfügbar.")

try:
    from mistralai.client import MistralClient
    from mistralai.models.chat_completion import ChatMessage
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_CLIENT = None  # Sicher initialisieren
    if MISTRAL_API_KEY:
        MISTRAL_CLIENT = MistralClient(api_key=MISTRAL_API_KEY)
    else:
        print("WARNUNG: MISTRAL_API_KEY nicht gefunden. Mistral-Modelle sind nicht verfügbar.")
except ImportError:
    MistralClient = None
    ChatMessage = None
    MISTRAL_CLIENT = None
    print("WARNUNG: mistralai nicht installiert. Mistral-Modelle nicht verfügbar.")


def generate_report_with_ai(prompt_text, ki_model):
    """
    Generiert einen Bericht mithilfe des ausgewählten KI-Modells.
    """
    try:
        if ki_model == "google":
            if not GenerativeModel:
                raise ValueError("Google Generative AI Bibliothek nicht installiert.")
            model = GenerativeModel('gemini-pro')
            response = model.generate_content(prompt_text)
            return response.text

        if ki_model == "mistral":
            if not MISTRAL_CLIENT:
                raise ValueError("Mistral Client nicht initialisiert. API-Key fehlt?")

            system_prompt_mistral = (
                "Du bist ein Experte für die Auswertung von Assessment-Center-Beobachtungen. "
                "Deine Aufgabe ist es, die Beobachtungen zu analysieren und eine "
                "wertschätzende, stärkenorientierte Rückmeldung zu formulieren. "
                
                # --- KORRIGIERTE KONTEXT-REGEL ---
                "Die Analyse soll sich IMMER auf die Person beziehen, deren Name im User-Prompt "
                "explizit genannt wird. Die Beobachtungen beschreiben "
                "das Verhalten DIESER Person. Andere Namen, die in den Notizen erwähnt werden, "
                "sind nur Kontext und nicht das Subjekt der Analyse."
                # ---------------------------------
                
                "Antworte ausschließlich mit einem JSON-Objekt, das exakt "
                "folgender Struktur entspricht: "
                "```json\n"
                "{\n"
                '  "sk_ratings": {\n'
                '    "flexibility": 0-10,\n'
                '    "team_orientation": 0-10,\n'
                '    "process_orientation": 0-10,\n'
                '    "results_orientation": 0-10\n'
                '  },\n'
                '  "vk_ratings": {\n'
                '    "flexibility": 0-10,\n'
                '    "consulting": 0-10,\n'
                '    "objectivity": 0-10,\n'
                '    "goal_orientation": 0-10\n'
                '  },\n'
                '  "ki_texts": {\n'
                '    "social_text": "Text zu sozialen Kompetenzen (max. 150 Wörter).",\n'
                '    "verbal_text": "Text zu verbalen Kompetenzen (max. 150 Wörter).",\n'
                '    "summary_text": "Zusammenfassung der Stärken (max. 150 Wörter)."\n'
                '  }\n'
                "}\n"
                "```\n"
                "Wichtige Regeln: Bewerte nur Stärken, keine Schwächen. "
                "Nutze die Skala von 0 bis 10. Formuliere positiv und präzise."
            )
            
            messages = [
                ChatMessage(role="system", content=system_prompt_mistral),
                ChatMessage(role="user", content=prompt_text)
            ]

            chat_response = MISTRAL_CLIENT.chat(
                model="mistral-large-latest",
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            return chat_response.choices[0].message.content

        raise ValueError("Ungültiges KI-Modell ausgewählt.")

    except (ValueError, TypeError) as e:
        print(f"!!! FEHLER BEI DER KI-ANALYSE !!!\n{e}")
        return json.dumps({"error": str(e)})
    except Exception as e:
        print(f"!!! UNERWARTETER FEHLER BEI DER KI-ANALYSE !!!\n{e}")
        return json.dumps({"error": "Ein unerwarteter Fehler ist beim KI-Dienst aufgetreten."})
