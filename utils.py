"""Dieses Modul enthält Hilfsfunktionen für Dateiverarbeitung und Textbereinigung."""

import io
import mimetypes
import re

from docx import Document
from pdfminer.high_level import extract_text as pdf_extract_text
from pdfminer.layout import LAParams
from pdfminer.pdfparser import PDFSyntaxError


def get_file_content(file):
    """
    Liest den Inhalt von hochgeladenen Dateien (PDF, DOCX, TXT) robust.
    """
    filename = file.filename
    content = ""
    try:
        file_buffer = io.BytesIO(file.read())
        mimetype = mimetypes.guess_type(filename)[0]

        if mimetype == 'application/pdf':
            content = pdf_extract_text(file_buffer, laparams=LAParams())
        elif mimetype == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            doc = Document(file_buffer)
            content = "\n".join([para.text for para in doc.paragraphs if para.text])
        elif mimetype and mimetype.startswith('text/'):
            content = file_buffer.read().decode('utf-8', errors='ignore')
        else:
            mimetype_str = mimetype if mimetype else "Unbekannt"
            content = f"--- FEHLER: Dateityp '{mimetype_str}' wird nicht unterstützt. ---"
        if not content or not content.strip():
            content = f"--- HINWEIS: Aus '{filename}' konnte kein Text extrahiert werden. ---"
    except (PDFSyntaxError, ValueError, IOError) as e:
        content = f"--- FEHLER beim Verarbeiten von '{filename}': {str(e)} ---"
    return (f"--- START INHALT AUS DATEI: {filename} ---\n"
            f"{content.strip()}\n"
            f"--- ENDE INHALT AUS DATEI: {filename} ---")


def clean_json_response(raw_response):
    """
    Bereinigt die JSON-Antwort von KI-Modellen, entfernt Code-Blöcke
    und Zeilenumbrüche.
    """
    if '```json' in raw_response:
        raw_response = raw_response.split('```json', 1)[-1]
        raw_response = raw_response.rsplit('```', 1)[0]
    cleaned_response = re.sub(r'[\r\n]+', '', raw_response)
    return cleaned_response.strip()
