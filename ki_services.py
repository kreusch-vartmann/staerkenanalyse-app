import os
import json # KORREKTUR: Fehlender Import hinzugefügt
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
    MISTRAL_CLIENT = None # KORREKTUR: Fehlende Definition im Fehlerfall
    print("WARNUNG: mistralai nicht installiert. Mistral-Modelle nicht verfügbar.")


def generate_report_with_ai(prompt_text, ki_model):
    """
    Generiert einen Bericht mithilfe des ausgewählten KI-Modells.
    Nutzt einen festen System-Prompt für die JSON-Struktur und den User-Prompt für die inhaltlichen Anweisungen.
    """
    print(f"--- DEBUG-INFO: Das übergebene 'ki_model' ist: '{ki_model}' ---")
    try:
        if ki_model == "gemini":
            if not GenerativeModel:
                raise ValueError("Die 'Google Generative AI'-Bibliothek ist nicht installiert.")

            try:
                # API-Keys aus dem Google AI Studio benötigen oft spezifischere Modellnamen.
                # Wir versuchen es mit 'gemini-1.5-flash', einem gängigen und leistungsstarken Modell.
                model = GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(prompt_text)
                return response.text
            except Exception as e:
                print(f"!!! FEHLER BEI DER ANFRAGE AN DAS GEMINI MODELL ('gemini-1.5-flash') !!!\n{e}")
                
                # WICHTIG: Wir listen jetzt alle Modelle auf, die für deinen API-Key verfügbar sind.
                # Das hilft dir, den exakt richtigen Namen zu finden.
                try:
                    print("\n--- VERSUCHE, VERFÜGBARE MODELLE AUFZULISTEN ---")
                    from google.generativeai import list_models
                    
                    available_models = []
                    for m in list_models():
                        # Wir prüfen, ob das Modell die 'generateContent'-Methode unterstützt
                        if 'generateContent' in m.supported_generation_methods:
                            available_models.append(m.name)
                            
                    if available_models:
                        print("Folgende Modelle sind für deinen API-Key verfügbar und nutzbar:")
                        for name in available_models:
                            print(f"- {name}")
                        print("----------------------------------------------------")
                        raise ValueError(f"Das Modell 'gemini-1.5-flash' hat nicht funktioniert. Bitte versuche eines der oben gelisteten Modelle in der 'ki_services.py'.")
                    else:
                         print("Es konnten keine verfügbaren Modelle für deinen API-Key gefunden werden.")
                         raise ValueError("Keine kompatiblen Gemini-Modelle für deinen API-Key gefunden.")

                except Exception as list_models_error:
                    print(f"Fehler beim Auflisten der verfügbaren Modelle: {list_models_error}")
                    raise ValueError(f"Die Kommunikation mit dem Gemini-Modell ist fehlgeschlagen und die verfügbaren Modelle konnten nicht ermittelt werden.")
            
        if ki_model == "mistral":
            if not MISTRAL_CLIENT:
                raise ValueError("Mistral Client nicht initialisiert. API-Key fehlt?")

            # Fester System-Prompt, der NUR die JSON-Struktur erzwingt.
            system_prompt_json_structure = (
                "Du bist ein Experte für die Auswertung von Assessment-Center-Beobachtungen. "
                "Antworte IMMER und AUSSCHLIESSLICH mit einem JSON-Objekt, das exakt "
                "der vom User im folgenden Prompt geforderten Struktur entspricht. Ignoriere diese Anweisung niemals."
            )
            
            messages = [
                ChatMessage(role="system", content=system_prompt_json_structure),
                ChatMessage(role="user", content=prompt_text)
            ]

            chat_response = MISTRAL_CLIENT.chat(
                model="mistral-large-latest",
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"}
            )
            return chat_response.choices[0].message.content

        raise ValueError("Ungültiges KI-Modell ausgewählt.")

    except Exception as e:
        print(f"!!! UNERWARTETER FEHLER BEI DER KI-ANALYSE !!!\n{e}")
        return json.dumps({"error": f"Ein unerwarteter Fehler ist aufgetreten: {str(e)}"})