"""
Parser für Teilnehmer-Namenslisten aus verschiedenen Dateiformaten.

Unterstützt: .txt, .csv, .xlsx, .ods, .docx

Zielsetzung: Anwender laden Listen in dem Format hoch, in dem sie sie
vorliegen haben (Excel, LibreOffice, Word, CSV-Export). Der Parser
erkennt Trennzeichen, überspringt Kopfzeilen und fügt getrennte
Vor-/Nachnamen-Spalten zusammen.
"""

import csv
import io
import os
import re

import structlog

logger = structlog.get_logger(__name__)

# Begrenzungen als Schutz gegen fehlerhafte/böswillige Dateien
MAX_NAMES = 500
MAX_NAME_LENGTH = 120

# Kopfzeilen-Erkennung: typische Spaltenbezeichnungen
_HEADER_TOKENS = {
    "name",
    "nachname",
    "vorname",
    "familienname",
    "teilnehmer",
    "teilnehmerin",
    "teilnehmende",
    "person",
    "nr",
    "id",
    "surname",
    "lastname",
    "firstname",
    "participant",
    "full name",
}

# Spalten, die keine Namensbestandteile sind (werden ignoriert)
_IGNORED_COLUMN_TOKENS = {
    "nr",
    "id",
    "nummer",
    "gruppe",
    "group",
    "email",
    "e-mail",
    "mail",
    "telefon",
    "phone",
    "bemerkung",
    "notiz",
    "datum",
}


class ImportParseError(ValueError):
    """Fehler beim Parsen einer Import-Datei."""


def _decode(raw: bytes) -> str:
    """Dekodiert Bytes robust (UTF-8 mit BOM, dann typische Windows-Encodings)."""
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportParseError(
        "Die Datei konnte nicht gelesen werden (unbekannte Zeichenkodierung)."
    )


def _clean_cell(value) -> str:
    """Normalisiert einen Zellwert zu einem String ohne Mehrfach-Leerzeichen."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = str(value).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_header(cells: list[str]) -> bool:
    """Erkennt, ob eine Zeile eine Kopfzeile ist."""
    filled = [c.lower() for c in cells if c]
    if not filled:
        return False
    return any(cell in _HEADER_TOKENS for cell in filled)


def _row_to_name(cells: list[str]) -> str:
    """Setzt aus den Zellen einer Zeile einen Namen zusammen.

    - Eine Spalte: wird direkt als vollständiger Name verwendet.
    - Mehrere Spalten: Namensbestandteile werden verbunden; reine
      Metadaten-Spalten (Nr., E-Mail, Gruppe ...) werden ignoriert.
    - Enthält eine Zelle ein Komma ("Meier, Anna"), wird sie zu
      "Anna Meier" gedreht.
    """
    values = [c for c in cells if c]
    if not values:
        return ""

    if len(values) == 1:
        return _normalize_comma_form(values[0])

    parts = []
    for value in values:
        lowered = value.lower()
        if lowered in _IGNORED_COLUMN_TOKENS:
            continue
        # Reine Zahlen (Laufnummern) und E-Mail-Adressen überspringen
        if re.fullmatch(r"\d+([.,]\d+)?", value):
            continue
        if "@" in value:
            continue
        parts.append(value)

    if not parts:
        return ""
    if len(parts) == 1:
        return _normalize_comma_form(parts[0])
    return " ".join(parts)


def _normalize_comma_form(value: str) -> str:
    """Wandelt "Nachname, Vorname" in "Vorname Nachname"."""
    if value.count(",") == 1:
        last, first = [p.strip() for p in value.split(",")]
        if last and first:
            return f"{first} {last}"
    return value


def _finalize(rows: list[list[str]]) -> list[str]:
    """Erzeugt aus geparsten Zeilen die endgültige Namensliste."""
    names: list[str] = []
    seen: set[str] = set()

    for cells in rows:
        cleaned = [_clean_cell(c) for c in cells]
        if not any(cleaned):
            continue
        # Kopfzeilen an beliebiger Position überspringen: In DOCX stehen
        # Tabellenköpfe nach den Absätzen, nicht in Zeile 0.
        if _looks_like_header(cleaned):
            continue

        name = _row_to_name(cleaned)
        if not name:
            continue
        if len(name) > MAX_NAME_LENGTH:
            name = name[:MAX_NAME_LENGTH].strip()

        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        names.append(name)

        if len(names) >= MAX_NAMES:
            logger.warning("Import auf Maximum begrenzt", max_names=MAX_NAMES)
            break

    return names


def _parse_text(raw: bytes) -> list[list[str]]:
    """Textdatei: ein Name pro Zeile."""
    return [[line] for line in _decode(raw).splitlines()]


def _parse_csv(raw: bytes) -> list[list[str]]:
    """CSV/TSV mit automatischer Trennzeichen-Erkennung."""
    text = _decode(raw)
    sample = text[:4096]

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
        delimiter = dialect.delimiter
    except csv.Error:
        # Fallback: häufigstes Trennzeichen in der ersten Zeile
        first_line = sample.splitlines()[0] if sample.splitlines() else ""
        delimiter = max(";,\t|", key=first_line.count)
        if first_line.count(delimiter) == 0:
            delimiter = ","

    return [row for row in csv.reader(io.StringIO(text), delimiter=delimiter)]


def _parse_xlsx(raw: bytes) -> list[list[str]]:
    """Excel-Datei (erstes Arbeitsblatt)."""
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover
        raise ImportParseError("XLSX-Unterstützung fehlt (openpyxl).") from exc

    try:
        workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception as exc:
        raise ImportParseError(f"XLSX-Datei konnte nicht gelesen werden: {exc}") from exc

    try:
        sheet = workbook[workbook.sheetnames[0]]
        return [list(row) for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()


def _parse_ods(raw: bytes) -> list[list[str]]:
    """OpenDocument-Tabelle (erstes Arbeitsblatt)."""
    try:
        from odf.opendocument import load
        from odf.table import Table, TableCell, TableRow
        from odf.text import P
    except ImportError as exc:  # pragma: no cover
        raise ImportParseError("ODS-Unterstützung fehlt (odfpy).") from exc

    try:
        document = load(io.BytesIO(raw))
    except Exception as exc:
        raise ImportParseError(f"ODS-Datei konnte nicht gelesen werden: {exc}") from exc

    tables = document.getElementsByType(Table)
    if not tables:
        return []

    rows = []
    for table_row in tables[0].getElementsByType(TableRow):
        cells = []
        for cell in table_row.getElementsByType(TableCell):
            text = " ".join(
                str(paragraph) for paragraph in cell.getElementsByType(P)
            ).strip()
            # Wiederholte Zellen (komprimierte Leerspalten) einmal übernehmen
            repeat = cell.getAttribute("numbercolumnsrepeated")
            count = int(repeat) if repeat and repeat.isdigit() else 1
            cells.extend([text] * min(count, 8))
        rows.append(cells)
    return rows


def _parse_docx(raw: bytes) -> list[list[str]]:
    """Word-Dokument: Absätze und Tabellenzeilen."""
    try:
        import docx
    except ImportError as exc:  # pragma: no cover
        raise ImportParseError("DOCX-Unterstützung fehlt (python-docx).") from exc

    try:
        document = docx.Document(io.BytesIO(raw))
    except Exception as exc:
        raise ImportParseError(f"DOCX-Datei konnte nicht gelesen werden: {exc}") from exc

    rows = [[paragraph.text] for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            rows.append([cell.text for cell in row.cells])
    return rows


_PARSERS = {
    ".txt": _parse_text,
    ".csv": _parse_csv,
    ".xlsx": _parse_xlsx,
    ".ods": _parse_ods,
    ".docx": _parse_docx,
}

SUPPORTED_EXTENSIONS = tuple(sorted(_PARSERS))


def extract_names_from_file(file_storage) -> list[str]:
    """Liest Teilnehmernamen aus einer hochgeladenen Datei.

    Args:
        file_storage: Werkzeug-FileStorage (bereits validiert).

    Returns:
        Liste eindeutiger Namen in Dateireihenfolge.

    Raises:
        ImportParseError: Bei nicht unterstütztem Format oder Leseproblemen.
    """
    filename = file_storage.filename or ""
    extension = os.path.splitext(filename)[1].lower()

    parser = _PARSERS.get(extension)
    if parser is None:
        raise ImportParseError(
            f"Format {extension or '(unbekannt)'} wird nicht unterstützt. "
            f"Möglich: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    file_storage.stream.seek(0)
    raw = file_storage.read()
    if not raw:
        raise ImportParseError("Die Datei ist leer.")

    names = _finalize(parser(raw))
    logger.info(
        "Namensliste geparst",
        filename=filename,
        extension=extension,
        names_found=len(names),
    )
    return names
