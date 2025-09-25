import io
import mimetypes
import re

from docx import Document
from pdfminer.high_level import extract_text as pdf_extract_text
from pdfminer.layout import LAParams

def get_file_content(file):
    """
    Liest den Inhalt von hochgeladenen Dateien (PDF, DOCX, TXT) robust.
    Behandelt Dateizeiger und Parsing-Fehler und gibt klares Feedback.
    """
    filename = file.filename
    
    try:
        # Liest die gesamte Datei EINMAL in einen In-Memory-Puffer.
        # Das verhindert Probleme mit erschöpften Dateizeigern.
        file_buffer = io.BytesIO(file.read())
        
        mimetype = mimetypes.guess_type(filename)[0]

        if mimetype == 'application/pdf':
            # Nutzt den Puffer für die Textextraktion.
            content = pdf_extract_text(file_buffer, laparams=LAParams())
        
        elif mimetype == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            # Nutzt den Puffer für die Dokumentenanalyse.
            doc = Document(file_buffer)
            content = "\n".join([para.text for para in doc.paragraphs if para.text])
        
        elif mimetype and mimetype.startswith('text/'):
            # Dekodiert aus dem Puffer.
            content = file_buffer.read().decode('utf-8', errors='ignore')
        
        else:
            content = f"--- FEHLER: Dateityp '{mimetype}' von '{filename}' wird nicht unterstützt. ---"

        # Wenn nach all dem der Inhalt immer noch leer ist, machen wir es explizit.
        if not content or not content.strip():
            content = f"--- HINWEIS: Aus der Datei '{filename}' konnte kein Text extrahiert werden. Ist die Datei leer oder enthält sie nur Bilder? ---"

    except Exception as e:
        content = f"--- KRITISCHER FEHLER beim Verarbeiten der Datei '{filename}': {str(e)} ---"
    
    # Fügt einen klaren Header hinzu, um den Inhalt im Prompt zu identifizieren und bereinigt Whitespace.
    return f"--- START INHALT AUS DATEI: {filename} ---\n{content.strip()}\n--- ENDE INHALT AUS DATEI: {filename} ---"

def clean_json_response(raw_response):
    """
    Bereinigt die JSON-Antwort von KI-Modellen, entfernt Code-Blöcke
    und Zeilenumbrüche.
    """
    # Entfernt Markdown-Code-Blöcke
    if '```json' in raw_response:
        raw_response = raw_response.split('```json', 1)[-1]
        raw_response = raw_response.rsplit('```', 1)[0]

    # Entfernt alle Arten von Zeilenumbrüchen
    cleaned_response = re.sub(r'[\r\n]+', '', raw_response)
    return cleaned_response.strip()