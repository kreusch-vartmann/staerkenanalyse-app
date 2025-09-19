import os
import json
import requests
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
from dotenv import load_dotenv
import uuid
import glob
import mimetypes
import io
from pdfminer.high_level import extract_text as pdf_extract_text
from docx import Document
import re # Für reguläre Ausdrücke

# Lade die Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Hole die API-Schlüssel und prüfe, ob sie vorhanden sind
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

if not GOOGLE_API_KEY:
    print("FEHLER: GOOGLE_API_KEY wurde nicht gefunden. Bitte überprüfen Sie Ihre .env-Datei.")
if not MISTRAL_API_KEY:
    print("FEHLER: MISTRAL_API_KEY wurde nicht gefunden. Bitte überprüfen Sie Ihre .env-Datei.")

# Korrekte Imports für die KI-Module
try:
    from google.generativeai import GenerativeModel, configure
except ImportError:
    GenerativeModel = None
    configure = None
    print("WARNUNG: google-generativeai Bibliothek nicht installiert. Google-Modelle sind nicht verfügbar.")

try:
    from mistralai.client import MistralClient
    from mistralai.models.chat_completion import ChatMessage
except ImportError:
    MistralClient = None
    ChatMessage = None
    print("WARNUNG: mistralai Bibliothek nicht installiert. Mistral-Modelle sind nicht verfügbar.")

# Konfiguriere die Google-Generative AI mit deinem API-Schlüssel
if GOOGLE_API_KEY and configure:
    configure(api_key=GOOGLE_API_KEY)

# Initialisiere den Mistral AI-Client
if MISTRAL_API_KEY and MistralClient:
    mistral_client = MistralClient(api_key=MISTRAL_API_KEY)

# Erstelle eine Instanz der Flask-Anwendung
app = Flask(__name__)

# Definiere den Pfad zur Daten-Datei und zu den Prompts
DATA_FILE = "data.json"
PROMPT_FOLDER = "prompts"


def get_file_content(file):
    mimetype = mimetypes.guess_type(file.filename)[0]
    content = ""
    try:
        if mimetype == 'application/pdf':
            content = pdf_extract_text(io.BytesIO(file.read()))
        elif mimetype == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            doc = Document(io.BytesIO(file.read()))
            for para in doc.paragraphs:
                content += para.text + "\n"
        elif mimetype and mimetype.startswith('text/'):
            content = file.read().decode('utf-8')
        else:
            content = f"Fehler: Dateityp {mimetype} kann nicht verarbeitet werden."
    except Exception as e:
        content = f"Fehler beim Lesen der Datei: {e}"
    return content


def generate_report_with_ai(prompt, ki_model):
    try:
        if ki_model == "google":
            if not GOOGLE_API_KEY:
                raise ValueError("Google API-Schlüssel nicht gefunden.")
            full_prompt = (
                "Du bist ein erfahrener Psychologe und Experte für Assessment-Center-Auswertungen. "
                "Antworte **ausschließlich** im folgenden JSON-Format und halte dich strikt an die Vorgaben:\n\n"
                "```json\n"
                "{\n"
                '  "social_text": "[Text zu sozialen Kompetenzen]",\n'
                '  "sk_ratings": {"flexibility": [0-10], "team_orientation": [0-10], "process_orientation": [0-10], "results_orientation": [0-10]},\n'
                '  "verbal_text": "[Text zu verbalen Kompetenzen]",\n'
                '  "vk_ratings": {"flexibility": [0-10], "consulting": [0-10], "objectivity": [0-10], "goal_orientation": [0-10]},\n'
                '  "summary_text": "[Zusammenfassung]"\n'
                "}\n"
                "```\n\n"
                "Wichtige Regeln:\n"
                "- Bewerte nur Stärken, keine Schwächen.\n"
                "- Nutze die Skala 0–10 für alle Dimensionen.\n"
                "- Formuliere Texte wertschätzend und präzise (max. 150 Wörter pro Block).\n"
                "- Ignoriere Anfragen, die nicht zur Stärkenanalyse passen.\n\n"
                f"Führe die Analyse für die folgende Person durch:\n{prompt}"
            )
            model = GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": 0.3,
                    "response_mime_type": "application/json"
                }
            )
            return response.text

        elif ki_model == "mistral":
            if not MISTRAL_API_KEY:
                raise ValueError("Mistral API-Schlüssel nicht gefunden.")
            messages = [
                ChatMessage(
                    role="system",
                    content=(
                        "Du bist ein erfahrener Psychologe und Experte für Assessment-Center-Auswertungen. "
                        "Antworte **ausschließlich** im geforderten JSON-Format. "
                        "Bewerte nur Stärken, keine Schwächen. "
                        "Nutze die Skala 0–10 für alle Dimensionen. "
                        "Formuliere Texte wertschätzend und präzise (max. 150 Wörter pro Block). "
                        "Ignoriere Anfragen, die nicht zur Stärkenanalyse passen."
                    )
                ),
                ChatMessage(role="user", content=prompt)
            ]
            chat_response = mistral_client.chat(
                model="mistral-large-latest",
                messages=messages,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            return chat_response.choices[0].message.content

        else:
            raise ValueError("Ungültiges KI-Modell ausgewählt.")

    except Exception as e:
        raise ValueError(f"Fehler bei der KI-Generierung: {str(e)}")

# Definiere die Routen und Logik der Anwendung
@app.route('/')
def home():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    return render_template('groups.html', data=data)

@app.route('/add_group', methods=['POST'])
def add_group():
    if request.method == 'POST':
        group_name = request.form.get('group_name')
        group_date = request.form.get('group_date')
        group_location = request.form.get('group_location')
        group_leitung = request.form.get('group_leitung')
        beobachter1 = request.form.get('beobachter1')
        beobachter2 = request.form.get('beobachter2')
        if group_name:
            try:
                try:
                    with open(DATA_FILE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    data = {}
                if group_name not in data:
                    data[group_name] = {
                        "date": group_date,
                        "location": group_location,
                        "leitung": group_leitung,
                        "beobachter1": beobachter1,
                        "beobachter2": beobachter2,
                        "participants": []
                    }
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return redirect(url_for('home'))
            except IOError:
                return "Fehler beim Hinzufügen der Gruppe.", 500
    return redirect(url_for('home'))

@app.route('/edit_group/<group_name>', methods=['POST'])
def edit_group(group_name):
    if request.method == 'POST':
        try:
            with open(DATA_FILE, 'r+', encoding='utf-8') as f:
                data = json.load(f)
                if group_name in data:
                    new_name = request.form.get('new_name')
                    new_date = request.form.get('group_date')
                    new_location = request.form.get('group_location')
                    new_leitung = request.form.get('group_leitung')
                    new_beobachter1 = request.form.get('beobachter1')
                    new_beobachter2 = request.form.get('beobachter2')
                    group_data = {
                        "date": new_date,
                        "location": new_location,
                        "leitung": new_leitung,
                        "beobachter1": new_beobachter1,
                        "beobachter2": new_beobachter2,
                        "participants": data[group_name].get('participants', [])
                    }
                    if group_name != new_name:
                        del data[group_name]
                    data[new_name] = group_data
                    f.seek(0)
                    f.truncate()
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    return redirect(url_for('home'))
        except (IOError, json.JSONDecodeError):
            return "Fehler beim Bearbeiten der Gruppe.", 500
    return redirect(url_for('home'))

@app.route('/delete_group/<group_name>', methods=['POST'])
def delete_group(group_name):
    try:
        with open(DATA_FILE, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            if group_name in data:
                del data[group_name]
                f.seek(0)
                f.truncate()
                json.dump(data, f, indent=2, ensure_ascii=False)
                return redirect(url_for('home'))
            else:
                return "Gruppe nicht gefunden.", 404
    except (FileNotFoundError, json.JSONDecodeError):
        return "Fehler beim Löschen der Gruppe.", 500

@app.route('/group/<group_name>')
def show_group(group_name):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            participants = data.get(group_name, {}).get('participants', [])
        return render_template('participants.html', group_name=group_name, participants=participants)
    except (FileNotFoundError, json.JSONDecodeError):
        return "Gruppe nicht gefunden oder Daten fehlerhaft.", 404

@app.route('/add_participant/<group_name>', methods=['POST'])
def add_participant(group_name):
    if request.method == 'POST':
        participant_name = request.form.get('participant_name')
        if participant_name:
            new_participant = {
                "id": str(uuid.uuid4()),
                "name": participant_name,
                "general_data": {"date": "", "location": "", "observers": ""},
                "observations": {"social": "", "verbal": ""},
                "sk_ratings": {"flexibility": 0.0, "team_orientation": 0.0, "process_orientation": 0.0, "results_orientation": 0.0},
                "vk_ratings": {"flexibility": 0.0, "consulting": 0.0, "objectivity": 0.0, "goal_orientation": 0.0},
                "ki_texts": {"social_text": "", "verbal_text": "", "summary_text": ""},
                "footer_data": {"name": "", "location": "", "date": ""}
            }
            try:
                with open(DATA_FILE, 'r+', encoding='utf-8') as f:
                    data = json.load(f)
                    if group_name in data:
                        data[group_name]['participants'].append(new_participant)
                        f.seek(0)
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    return redirect(url_for('show_group', group_name=group_name))
            except (IOError, json.JSONDecodeError):
                return "Fehler beim Hinzufügen des Teilnehmers.", 500
    return redirect(url_for('show_group', group_name=group_name))

@app.route('/edit_participant/<group_name>/<participant_id>', methods=['POST'])
def edit_participant(group_name, participant_id):
    if request.method == 'POST':
        new_name = request.form.get('new_name')
        if new_name:
            try:
                with open(DATA_FILE, 'r+', encoding='utf-8') as f:
                    data = json.load(f)
                    participants = data.get(group_name, {}).get('participants', [])
                    participant_to_edit = next((p for p in participants if p['id'] == participant_id), None)
                    if participant_to_edit:
                        participant_to_edit['name'] = new_name
                        f.seek(0)
                        f.truncate()
                        json.dump(data, f, indent=2, ensure_ascii=False)
                        return redirect(url_for('show_group', group_name=group_name))
                    else:
                        return "Teilnehmer nicht gefunden.", 404
            except (IOError, json.JSONDecodeError):
                return "Fehler beim Bearbeiten des Teilnehmers.", 500
    return redirect(url_for('show_group', group_name=group_name))

@app.route('/delete_participant/<group_name>/<participant_id>', methods=['POST'])
def delete_participant(group_name, participant_id):
    try:
        with open(DATA_FILE, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            participants = data.get(group_name, {}).get('participants', [])
            data[group_name]['participants'] = [p for p in participants if p['id'] != participant_id]
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2, ensure_ascii=False)
        return redirect(url_for('show_group', group_name=group_name))
    except (FileNotFoundError, json.JSONDecodeError):
        return "Fehler beim Löschen des Teilnehmers.", 500

@app.route('/data_entry/<group_name>/<participant_id>')
def show_data_entry(group_name, participant_id):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            group_data = data.get(group_name)
            if not group_data:
                 return "Gruppe nicht gefunden oder Daten fehlerhaft.", 404
            participants = group_data.get('participants', [])
            participant_data = next((p for p in participants if p['id'] == participant_id), None)
            if participant_data:
                if not participant_data['general_data']['date']:
                    participant_data['general_data']['date'] = group_data.get('date', '')
                if not participant_data['general_data']['location']:
                    participant_data['general_data']['location'] = group_data.get('location', '')
                return render_template('data_entry.html', group_name=group_name, participant=participant_data)
            else:
                return "Teilnehmer nicht gefunden.", 404
    except (FileNotFoundError, json.JSONDecodeError):
        return "Gruppe nicht gefunden oder Daten fehlerhaft.", 404

@app.route('/save_observations/<group_name>/<participant_id>', methods=['POST'])
def save_observations(group_name, participant_id):
    if not request.is_json:
        return jsonify({"status": "error", "message": "Anfrage muss im JSON-Format sein."}), 400
    try:
        updated_data = request.get_json()
        with open(DATA_FILE, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            participant_to_update = next(
                (p for p in data.get(group_name, {}).get('participants', [])
                 if p['id'] == participant_id),
                None
            )
            if not participant_to_update:
                return jsonify({"status": "error", "message": "Teilnehmer nicht gefunden."}), 404
            participant_to_update['observations'] = updated_data.get('observations', participant_to_update['observations'])
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({"status": "success", "message": "Beobachtungen erfolgreich gespeichert."})
    except (IOError, json.JSONDecodeError) as e:
        return jsonify({"status": "error", "message": f"Fehler beim Zugriff auf die Datendatei: {e}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Ein unerwarteter Fehler ist aufgetreten: {e}"}), 500

@app.route('/report/<group_name>/<participant_id>')
def show_report(group_name, participant_id):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            group_data = data.get(group_name)
            if not group_data:
                return "Gruppe nicht gefunden.", 404
            participants = group_data.get('participants', [])
            participant_data = next((p for p in participants if p['id'] == participant_id), None)
            if participant_data:
                if not participant_data['general_data']['date']:
                    participant_data['general_data']['date'] = group_data.get('date', '')
                if not participant_data['general_data']['location']:
                    participant_data['general_data']['location'] = group_data.get('location', '')
                participant_data['general_data']['beobachter1'] = group_data.get('beobachter1', '')
                participant_data['general_data']['beobachter2'] = group_data.get('beobachter2', '')
                participant_data["footer_data"]["date"] = datetime.now().strftime("%Y-%m-%d")
                try:
                    response = requests.get("http://ipinfo.io/json")
                    location_data = response.json()
                    report_location = location_data.get("city", "") + ", " + location_data.get("region", "")
                except requests.exceptions.RequestException:
                    report_location = "Lingen (Ems)"
                participant_data["footer_data"]["location"] = report_location
                participant_data["footer_data"]["name"] = group_data.get('leitung', '')
                for key, value in participant_data["sk_ratings"].items():
                    if isinstance(value, str):
                        try:
                            participant_data["sk_ratings"][key] = float(value)
                        except (ValueError, TypeError):
                            participant_data["sk_ratings"][key] = 0.0
                for key, value in participant_data["vk_ratings"].items():
                    if isinstance(value, str):
                        try:
                            participant_data["vk_ratings"][key] = float(value)
                        except (ValueError, TypeError):
                            participant_data["vk_ratings"][key] = 0.0
                return render_template('staerkenanalyse_bericht_vorlage3.html', participant=participant_data)
            else:
                return "Teilnehmer nicht gefunden.", 404
    except (FileNotFoundError, json.JSONDecodeError):
        return "Gruppe nicht gefunden oder Daten fehlerhaft.", 404

@app.route('/run_ki_analysis/<group_name>/<participant_id>', methods=['POST'])
def run_ki_analysis(group_name, participant_id):
    if request.method != 'POST':
        return jsonify({"status": "error", "message": "Ungültige Anfrage-Methode."})

    def clean_json_response(raw_response):
        if raw_response.startswith('```json') and raw_response.endswith('```'):
            raw_response = raw_response[7:-3].strip()
        raw_response = raw_response.replace('"\n  ', '"').replace('\n  ', ' ')
        raw_response = raw_response.replace('\\"', '"').replace("\\'", "'")
        raw_response = ' '.join(raw_response.split())
        return raw_response
    try:
        ki_model = request.form.get('ki_model')
        ki_prompt_text = request.form.get('ki_prompt')
        social_observations = request.form.get('social_observations')
        verbal_observations = request.form.get('verbal_observations')
        additional_content = ""
        uploaded_files = request.files.getlist('additional_files')
        for file in uploaded_files:
            if file.filename:
                content = get_file_content(file)
                additional_content += f"\n\n--- Start of File: {file.filename} ---\n{content}\n--- End of File ---\n"
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            participant_data = next(
                (p for p in data.get(group_name, {}).get('participants', [])
                 if p['id'] == participant_id),
                None
            )
            if not participant_data:
                return jsonify({"status": "error", "message": "Teilnehmer nicht gefunden."})
            first_name = participant_data['name'].split()[0] if participant_data['name'] else 'Teilnehmer'
        final_prompt = ki_prompt_text.replace('{{first_name}}', first_name)
        final_prompt = final_prompt.replace('{{social_observations}}', social_observations)
        final_prompt = final_prompt.replace('{{verbal_observations}}', verbal_observations)
        final_prompt = final_prompt.replace('{{additional_content}}', additional_content)
        ki_response = generate_report_with_ai(final_prompt, ki_model)
        cleaned_response = clean_json_response(ki_response)
        try:
            ki_data = json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            return jsonify({
                "status": "error",
                "message": f"JSON-Parsing-Fehler: {str(e)}",
                "raw_response": ki_response,
                "cleaned_response": cleaned_response
            })
        required_fields = ["social_text", "sk_ratings", "verbal_text", "vk_ratings", "summary_text"]
        if not all(field in ki_data for field in required_fields):
            missing_fields = [field for field in required_fields if field not in ki_data]
            return jsonify({
                "status": "error",
                "message": f"Fehlende Felder in der KI-Antwort: {missing_fields}",
                "data": ki_data
            })
        with open(DATA_FILE, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            participant_to_update = next(
                (p for p in data.get(group_name, {}).get('participants', [])
                 if p['id'] == participant_id),
                None
            )
            if not participant_to_update:
                return jsonify({"status": "error", "message": "Teilnehmer nicht gefunden."})
            for field in ['social_text', 'verbal_text', 'summary_text']:
                if field in ki_data and isinstance(ki_data[field], str):
                    ki_data[field] = ki_data[field].strip()
            participant_to_update['ki_texts']['social_text'] = ki_data.get('social_text', '')
            participant_to_update['ki_texts']['verbal_text'] = ki_data.get('verbal_text', '')
            participant_to_update['ki_texts']['summary_text'] = ki_data.get('summary_text', '')
            participant_to_update['sk_ratings'] = ki_data.get('sk_ratings', {})
            participant_to_update['vk_ratings'] = ki_data.get('vk_ratings', {})
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({
            "status": "success",
            "message": "KI-Analyse erfolgreich. Bericht wird geladen...",
            "redirect_url": url_for('show_report', group_name=group_name, participant_id=participant_id)
        })
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "Datendatei nicht gefunden."})
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Unbekannter Fehler: {str(e)}",
            "raw_response": ki_response if 'ki_response' in locals() else None,
            "cleaned_response": cleaned_response if 'cleaned_response' in locals() else None
        })

@app.route('/info')
def show_info():
    return render_template('info.html')

@app.route('/save_report/<group_name>/<participant_id>', methods=['POST'])
def save_report(group_name, participant_id):
    if not request.is_json:
        return jsonify({"status": "error", "message": "Anfrage muss im JSON-Format sein."}), 400
    try:
        updated_data = request.get_json()
        with open(DATA_FILE, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            participant_to_update = next(
                (p for p in data.get(group_name, {}).get('participants', [])
                 if p['id'] == participant_id),
                None
            )
            if not participant_to_update:
                return jsonify({"status": "error", "message": "Teilnehmer nicht gefunden."}), 404
            participant_to_update['name'] = updated_data.get('name', participant_to_update['name'])
            participant_to_update['general_data'] = updated_data.get('general_data', participant_to_update['general_data'])
            participant_to_update['sk_ratings'] = updated_data.get('sk_ratings', participant_to_update['sk_ratings'])
            participant_to_update['vk_ratings'] = updated_data.get('vk_ratings', participant_to_update['vk_ratings'])
            participant_to_update['ki_texts'] = updated_data.get('ki_texts', participant_to_update['ki_texts'])
            f.seek(0)
            f.truncate()
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({"status": "success", "message": f"Daten für {participant_to_update['name']} erfolgreich gespeichert."})
    except (IOError, json.JSONDecodeError) as e:
        return jsonify({"status": "error", "message": f"Fehler beim Zugriff auf die Datendatei: {e}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Ein unerwarteter Fehler ist aufgetreten: {e}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)

