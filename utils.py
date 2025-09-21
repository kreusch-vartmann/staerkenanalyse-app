"""
Hilfsfunktionen für das Stärkenanalyse-Tool.

Enthält Funktionen zum Verarbeiten von Dateien und Bereinigen von Daten.
"""
import io
import mimetypes
import re

from docx import Document
from pdfminer.high_level import extract_text as pdf_extract_text

def get_file_content(file):
    """Liest den Inhalt von hochgeladenen Dateien (PDF, DOCX, TXT)."""
    mimetype = mimetypes.guess_type(file.filename)[0]
    content = ""
    try:
        if mimetype == 'application/pdf':
            content = pdf_extract_text(io.BytesIO(file.read()))
        elif mimetype == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            doc = Document(io.BytesIO(file.read()))
            content = "\n".join([para.text for para in doc.paragraphs])
        elif mimetype and mimetype.startswith('text/'):
            content = file.read().decode('utf-8')
        else:
            content = f"Fehler: Dateityp {mimetype} wird nicht unterstützt."
    except Exception as e:
        # Eine allgemeine Exception ist hier sinnvoll, da viele Fehler
        # beim Parsen von Dateien auftreten können (z.B. beschädigte Datei).
        content = f"Fehler beim Lesen der Datei {file.filename}: {e}"
    return content

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
