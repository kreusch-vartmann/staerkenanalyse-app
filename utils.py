"""Dieses Modul enthält Hilfsfunktionen für Dateiverarbeitung und Textbereinigung."""

import io
import mimetypes
import os
import re
import secrets
import string

import bleach
from docx import Document
from pdfminer.high_level import extract_text as pdf_extract_text
from pdfminer.layout import LAParams
from pdfminer.pdfparser import PDFSyntaxError
from werkzeug.utils import secure_filename

# Konstanten für File Upload Security
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".odt"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB pro Datei

# Erlaubte HTML-Tags für Rich-Text (Quill.js Output)
ALLOWED_HTML_TAGS = [
    "p",
    "br",
    "strong",
    "em",
    "u",
    "ol",
    "ul",
    "li",
    "h1",
    "h2",
    "h3",
    "s",
    "blockquote",
    "code",
    "pre",
]

ALLOWED_HTML_ATTRIBUTES = {"*": ["class"]}  # Quill fügt .ql-* Klassen hinzu


def sanitize_html(html_content):
    """
    Bereinigt HTML-Content gegen XSS-Angriffe.
    Erlaubt nur sichere Tags die Quill.js generiert.

    Args:
        html_content (str): HTML string from Quill editor

    Returns:
        str: Sanitized HTML safe for database storage
    """
    if not html_content:
        return ""

    # Bleach entfernt alle nicht-erlaubten Tags/Attribute
    cleaned = bleach.clean(
        html_content,
        tags=ALLOWED_HTML_TAGS,
        attributes=ALLOWED_HTML_ATTRIBUTES,
        strip=True,  # Entferne Tags statt escape
    )

    return cleaned


def validate_upload_file(file):
    """
    Validiert Upload-Dateien auf Sicherheit:
    - Prüft ob Datei vorhanden
    - Sanitisiert Dateinamen
    - Validiert Dateityp gegen Whitelist
    - Prüft Dateigröße (max 5MB)

    Returns:
        str: Sanitisierter Dateiname

    Raises:
        ValueError: Bei Validierungsfehlern
    """
    if not file or file.filename == "":
        raise ValueError("Keine Datei ausgewählt")

    # Sanitize filename
    filename = secure_filename(file.filename)

    if not filename:
        raise ValueError("Ungültiger Dateiname")

    # Check extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Dateityp {ext} nicht erlaubt. Erlaubt: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Check file size (read position to get size)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    if size > MAX_FILE_SIZE:
        raise ValueError(f"Datei zu groß ({size/1024/1024:.1f}MB). Maximum: 5MB")

    if size == 0:
        raise ValueError("Datei ist leer")

    return filename


def get_file_content(file):
    """
    Liest den Inhalt von hochgeladenen Dateien (PDF, DOCX, TXT) robust.
    Validiert die Datei zuerst auf Sicherheit.
    """
    # Validiere Datei zuerst
    try:
        filename = validate_upload_file(file)
    except ValueError as e:
        return f"--- FEHLER: Datei-Validierung fehlgeschlagen: {str(e)} ---"

    content = ""
    try:
        file_buffer = io.BytesIO(file.read())
        mimetype = mimetypes.guess_type(filename)[0]

        if mimetype == "application/pdf":
            content = pdf_extract_text(file_buffer, laparams=LAParams())
        elif (
            mimetype
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            doc = Document(file_buffer)
            content = "\n".join([para.text for para in doc.paragraphs if para.text])
        elif mimetype and mimetype.startswith("text/"):
            content = file_buffer.read().decode("utf-8", errors="ignore")
        else:
            mimetype_str = mimetype if mimetype else "Unbekannt"
            content = (
                f"--- FEHLER: Dateityp '{mimetype_str}' wird nicht unterstützt. ---"
            )
        if not content or not content.strip():
            content = (
                f"--- HINWEIS: Aus '{filename}' konnte kein Text extrahiert werden. ---"
            )
    except (PDFSyntaxError, ValueError, IOError) as e:
        content = f"--- FEHLER beim Verarbeiten von '{filename}': {str(e)} ---"
    return (
        f"--- START INHALT AUS DATEI: {filename} ---\n"
        f"{content.strip()}\n"
        f"--- ENDE INHALT AUS DATEI: {filename} ---"
    )


def clean_json_response(raw_response):
    """
    Bereinigt die JSON-Antwort von KI-Modellen, entfernt Code-Blöcke
    und Zeilenumbrüche.
    """
    if "```json" in raw_response:
        raw_response = raw_response.split("```json", 1)[-1]
        raw_response = raw_response.rsplit("```", 1)[0]
    cleaned_response = re.sub(r"[\r\n]+", "", raw_response)
    return cleaned_response.strip()


def generate_secure_password(length: int = 16) -> str:
    """
    Generiert ein kryptographisch sicheres Zufallspasswort.
    
    Verwendet Python's `secrets`-Modul (cryptographically strong random generator).
    Enthält Großbuchstaben, Kleinbuchstaben, Ziffern und Sonderzeichen.
    
    Args:
        length: Länge des Passworts (Standard: 16 Zeichen ~95-100 Bit Entropie)
    
    Returns:
        str: Ein 16-Zeichen-Passwort mit hoher Entropie
    
    Beispiel:
        password = generate_secure_password()
        # Output: "k7$Xp2mR!wQ9nL4s" (zufällig generiert)
    """
    # Character set: A-Z, a-z, 0-9, Sonderzeichen
    chars = string.ascii_letters + string.digits + string.punctuation
    
    # Entferne problematische Sonderzeichen die in manchen Kontexten Probleme machen
    # aber behalte genug für Sicherheit (nicht " oder \ oder backtick)
    chars = "".join(c for c in chars if c not in '"\'\\`')
    
    # Generiere sicheres Passwort
    password = "".join(secrets.choice(chars) for _ in range(length))
    
    return password
