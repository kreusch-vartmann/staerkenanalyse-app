"""
Import von Aufgaben-Inhalten aus TXT/DOCX-Dateien (Einzelimport: 1 Datei
= 1 Aufgabe).

Der DOCX-Parser ist bewusst die Umkehrung von services/task_export.py's
_TaskHtmlToDocx: Er nutzt dieselben Stil-Konventionen (Heading 1/2,
List Number/List Bullet, bold-Runs), damit ein Export → externes
Bearbeiten in Word → Re-Import verlustfrei funktioniert.
"""

from __future__ import annotations

import re


class TaskImportError(ValueError):
    """Fehler beim Import einer Aufgaben-Datei."""


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _runs_to_html(paragraph) -> str:
    """Wandelt die Runs eines DOCX-Absatzes in HTML um (bold->strong, italic->em)."""
    parts = []
    for run in paragraph.runs:
        text = _escape(run.text)
        if not text:
            continue
        if run.bold:
            text = f"<strong>{text}</strong>"
        if run.italic:
            text = f"<em>{text}</em>"
        parts.append(text)
    if parts:
        return "".join(parts)
    # Fallback: manche DOCX-Exporte (z. B. aus LibreOffice) liefern den Text
    # nicht über .runs zugänglich - dann paragraph.text als Ganzes nutzen.
    return _escape(paragraph.text)


def parse_task_docx(file_storage) -> str:
    """Liest eine .docx-Datei und liefert den Inhalt als normalisierbares HTML.

    Erkennt Word-Formatvorlagen: "Title"/"Heading 1" -> <h2>, "Heading 2"
    (oder höher) -> <h3>, "List Number" -> <ol><li>, "List Bullet" ->
    <ul><li>, alles andere -> <p>. Wird anschließend durch
    services/task_normalization._normalize_task_html() auf die
    Aufgabe/Rahmenbedingungen-Struktur normalisiert.
    """
    try:
        import docx
    except Exception as e:
        raise TaskImportError(f"python-docx konnte nicht geladen werden: {e}") from e

    try:
        document = docx.Document(file_storage.stream)
    except Exception as e:
        raise TaskImportError(f"DOCX-Datei konnte nicht gelesen werden: {e}") from e

    html_parts: list[str] = []
    current_list: str | None = None  # "ol" oder "ul"

    def close_list():
        nonlocal current_list
        if current_list:
            html_parts.append(f"</{current_list}>")
            current_list = None

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue

        style = (paragraph.style.name or "").lower()
        content = _runs_to_html(paragraph)

        if style in ("title", "heading 1"):
            close_list()
            html_parts.append(f"<h2>{content}</h2>")
        elif style.startswith("heading"):
            close_list()
            html_parts.append(f"<h3>{content}</h3>")
        elif style == "list number":
            if current_list != "ol":
                close_list()
                html_parts.append("<ol>")
                current_list = "ol"
            html_parts.append(f"<li>{content}</li>")
        elif style == "list bullet":
            if current_list != "ul":
                close_list()
                html_parts.append("<ul>")
                current_list = "ul"
            html_parts.append(f"<li>{content}</li>")
        else:
            close_list()
            html_parts.append(f"<p>{content}</p>")

    close_list()

    if not html_parts:
        raise TaskImportError("Die DOCX-Datei enthält keinen lesbaren Text.")

    return "\n".join(html_parts)


def parse_task_txt(file_storage) -> str:
    """Liest eine TXT-Datei; leere Zeilen trennen Absätze.

    Erste nicht-leere Zeile wird als Titel (<h2>) interpretiert, wenn sie
    kurz ist (< 80 Zeichen) und danach eine Leerzeile folgt - sonst wird
    alles als Fließtext-Absätze behandelt (Struktur ergibt sich dann erst
    durch die Normalisierung/manuelle Nachbearbeitung im Editor).
    """
    raw = file_storage.read()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise TaskImportError("Die Datei konnte nicht gelesen werden (unbekannte Zeichenkodierung).")

    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if not blocks:
        raise TaskImportError("Die Datei ist leer.")

    html_parts = []
    first = blocks[0]
    if len(first) < 80 and "\n" not in first:
        html_parts.append(f"<h2>{_escape(first)}</h2>")
        blocks = blocks[1:]

    for block in blocks:
        html_parts.append(f"<p>{_escape(block)}</p>")

    return "\n".join(html_parts)


_PARSERS = {
    ".docx": parse_task_docx,
    ".txt": parse_task_txt,
}


def extract_task_content_from_file(file_storage) -> str:
    """Liest eine hochgeladene Datei (.docx/.txt) und liefert den
    Aufgabeninhalt als HTML (vor der Normalisierung)."""
    import os

    filename = file_storage.filename or ""
    extension = os.path.splitext(filename)[1].lower()

    parser = _PARSERS.get(extension)
    if parser is None:
        raise TaskImportError(
            f"Format {extension or '(unbekannt)'} wird nicht unterstützt. "
            f"Möglich: {', '.join(sorted(_PARSERS))}"
        )

    file_storage.stream.seek(0)
    return parser(file_storage)
