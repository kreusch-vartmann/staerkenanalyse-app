"""
Dieses Modul enthält Funktionen zur Integration und Nutzung von KI-Modellen
für die Berichtserstellung.
"""

import os
import json
from dotenv import load_dotenv

# Lade die Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Versuche, die notwendigen Bibliotheken zu importieren und zu konfigurieren
try:
    from google.generativeai import GenerativeModel, configure, list_models
    from google.api_core import exceptions as google_exceptions
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if GOOGLE_API_KEY:
        configure(api_key=GOOGLE_API_KEY)
    else:
        print("WARNUNG: GOOGLE_API_KEY nicht gefunden. Google-Modelle sind nicht verfügbar.")
except ImportError:
    GenerativeModel, list_models, google_exceptions = None, None, None
    print("WARNUNG: google-generativeai nicht installiert. Google-Modelle nicht verfügbar.")

try:
    from mistralai.client import MistralClient
    from mistralai.models.chat_completion import ChatMessage
    from mistralai.exceptions import MistralAPIException
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_CLIENT = MistralClient(api_key=MISTRAL_API_KEY) if MISTRAL_API_KEY else None
    if not MISTRAL_API_KEY:
        print("WARNUNG: MISTRAL_API_KEY nicht gefunden. Mistral-Modelle sind nicht verfügbar.")
except ImportError:
    MistralClient, ChatMessage, MistralAPIException, MISTRAL_CLIENT = None, None, None, None
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
                raise ValueError("Die 'Google Generative AI'-Bibliothek ist nicht installiert.")

            # KORREKTUR: Modellnamen auf das Standardmodell für AI Studio Keys geändert.
            model_name = 'models/gemini-pro-latest'
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
                ChatMessage(role="user", content=prompt_text)
            ]
            chat_response = MISTRAL_CLIENT.chat(
                model="mistral-large-latest",
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"}
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
        available_models = [m.name for m in list_models()
                            if 'generateContent' in m.supported_generation_methods]

        if available_models:
            print("Folgende Modelle sind für deinen API-Key verfügbar und nutzbar:")
            for name in available_models:
                print(f"- {name}")
            print("----------------------------------------------------")
            raise ValueError(
                f"Das Modell '{model_name}' hat nicht funktioniert. Bitte versuche eines "
                "der oben gelisteten Modelle in der 'ki_services.py'."
            ) from original_exception

        print("Es konnten keine verfügbaren Modelle für deinen API-Key gefunden werden.")
        raise ValueError(
            "Keine kompatiblen Gemini-Modelle für deinen API-Key gefunden."
        ) from original_exception

    except Exception as list_models_error:
        print(f"Fehler beim Auflisten der verfügbaren Modelle: {list_models_error}")
        raise ValueError(
            "Die Kommunikation mit dem Gemini-Modell ist fehlgeschlagen."
        ) from list_models_error
