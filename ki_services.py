"""
KI-Integration für Berichtserstellung und Aufgaben-Generierung.
Unterstützt Mistral und Google Gemini APIs.
"""

import json
import os
import re
import ast
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

# Knowledge Base Import
try:
    from services.task_knowledge_base import get_knowledge_for_prompt
except ImportError:
    from task_knowledge_base import get_knowledge_for_prompt  # Fallback für Tests

# Google AI Setup
try:
    from google.generativeai import GenerativeModel, configure
    try:
        from google.api_core.exceptions import NotFound
    except ImportError:
        NotFound = None
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-flash-latest")
    GEMINI_FALLBACK_MODELS = [
        GEMINI_MODEL,
        "models/gemini-flash-latest",
        "models/gemini-2.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-flash-lite-latest",
        "models/gemini-pro-latest",
        "models/gemini-2.5-pro",
    ]
    GEMINI_FALLBACK_MODELS = [m for m in GEMINI_FALLBACK_MODELS if m]
    if GOOGLE_API_KEY:
        configure(api_key=GOOGLE_API_KEY)
        genai_client = True
    else:
        genai_client = None
except ImportError:
    GenerativeModel = None
    NotFound = None
    GEMINI_MODEL = None
    GEMINI_FALLBACK_MODELS = []
    genai_client = None

# Mistral Setup
try:
    from mistralai.client import MistralClient
    from mistralai.exceptions import MistralAPIException
    from mistralai.models.chat_completion import ChatMessage

    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
    if MISTRAL_API_KEY:
        MISTRAL_CLIENT = MistralClient(api_key=MISTRAL_API_KEY)
    else:
        MISTRAL_CLIENT = None
        print("WARNUNG: MISTRAL_API_KEY nicht gefunden. Mistral-Modelle sind nicht verf\u00fcgbar.")
except ImportError:
    MistralClient, ChatMessage, MistralAPIException, MISTRAL_CLIENT = (
        None,
        None,
        None,
        None,
    )
    print("WARNUNG: mistralai nicht installiert. Mistral-Modelle nicht verf\u00fcgbar.")


def _call_gemini(system_prompt_text: str, user_prompt_text: str, max_output_tokens: int = 8000) -> tuple[str, str]:
    if not genai_client or GenerativeModel is None:
        raise RuntimeError("Google Gemini ist nicht konfiguriert")
    last_error = None
    generation_config = {"max_output_tokens": max_output_tokens}
    for model_name in GEMINI_FALLBACK_MODELS:
        try:
            model = GenerativeModel(model_name=model_name, system_instruction=system_prompt_text)
            response = model.generate_content(user_prompt_text, generation_config=generation_config)
            return response.text, model_name
        except Exception as e:
            message = str(e).lower()
            if (NotFound and isinstance(e, NotFound)) or "not found" in message:
                last_error = e
                continue
            raise
    raise last_error if last_error else RuntimeError("Kein unterstütztes Gemini-Modell verfügbar")


# =============================================================================
# KI-GYM: RAW RESPONSE CAPTURE
# =============================================================================

def save_ai_raw_response(response_text: str, response_type: str, context_id: int, 
                         ki_model: str, observation_area: str = None, 
                         context_metadata: dict = None) -> int:
    """
    Speichert die unbearbeitete KI-Antwort für spätere Lernzwecke.
    
    Args:
        response_text: Originale KI-Antwort (unverändert)
        response_type: 'task' oder 'report'
        context_id: task_id oder participant_id
        ki_model: z.B. 'mistral-large-latest' oder 'gemini-flash-latest'
        observation_area: Optional, z.B. 'Soziale Kompetenzen'
        context_metadata: Optional, z.B. {'prompt': '...', 'temperature': 0.7}
    
    Returns:
        raw_response_id: ID des gespeicherten Records
    """
    from extensions import db
    from models import AIRawResponse
    
    try:
        raw_response = AIRawResponse(
            type=response_type,
            context_id=context_id,
            ki_model=ki_model,
            raw_response=response_text,
            processing_status='pending',
            observation_area=observation_area,
            context_metadata=context_metadata or {}
        )
        db.session.add(raw_response)
        db.session.flush()  # Get ID without committing
        
        print(f"   📦 KI-Gym: Raw response #{raw_response.id} gespeichert ({len(response_text)} chars)")
        
        return raw_response.id
    except Exception as e:
        print(f"   ⚠️  Fehler beim Speichern der Raw Response: {e}")
        # Non-critical: return None but don't break the main flow
        return None


def compute_content_diff(raw_content: str, final_content: str) -> dict:
    """
    Berechnet metrische Unterschiede zwischen Raw AI Output und finaler User-Version.
    
    Args:
        raw_content: Originale KI-Antwort
        final_content: Bearbeitete finale Version
    
    Returns:
        {
            'char_diff_percent': float (0-100),
            'char_diff_absolute': int,
            'length_change_percent': float,
            'structural_changes': str (summary),
            'edit_magnitude': str ('minor'|'moderate'|'major')
        }
    """
    import difflib
    from html.parser import HTMLParser
    
    # Simple Zeichenanzahl-Metriken
    raw_len = len(raw_content)
    final_len = len(final_content)
    char_diff = abs(raw_len - final_len)
    char_diff_percent = (char_diff / raw_len * 100) if raw_len > 0 else 0
    length_change_percent = ((final_len - raw_len) / raw_len * 100) if raw_len > 0 else 0
    
    # Sequence Matcher für Gesamtähnlichkeit
    similarity = difflib.SequenceMatcher(None, raw_content, final_content).ratio()
    similarity_percent = similarity * 100
    
    # Strukturelle Änderungen (einfache HTML Tag Zählung)
    try:
        class TagCounter(HTMLParser):
            def __init__(self):
                super().__init__()
                self.tags = []
            def handle_starttag(self, tag, attrs):
                self.tags.append(tag)
        
        raw_counter = TagCounter()
        final_counter = TagCounter()
        raw_counter.feed(raw_content)
        final_counter.feed(final_content)
        
        tag_diff = abs(len(raw_counter.tags) - len(final_counter.tags))
        structural_changes = f"{tag_diff} Tag-Änderungen" if tag_diff > 0 else "Keine strukturellen Änderungen"
    except:
        structural_changes = "Konnte nicht berechnen"
    
    # Edit Magnitude Klassifikation
    if similarity_percent > 90 and char_diff_percent < 10:
        edit_magnitude = "minor"
    elif similarity_percent > 70 and char_diff_percent < 30:
        edit_magnitude = "moderate"
    else:
        edit_magnitude = "major"
    
    return {
        'char_diff_percent': round(char_diff_percent, 2),
        'char_diff_absolute': char_diff,
        'length_change_percent': round(length_change_percent, 2),
        'similarity_percent': round(similarity_percent, 2),
        'structural_changes': structural_changes,
        'edit_magnitude': edit_magnitude
    }


# =============================================================================
# BEOBACHTUNGSAUFGABEN-GENERIERUNG (NEUE FUNKTIONEN)
# =============================================================================


def _clean_html_output(html_content: str) -> str:
    """
    Bereinigt HTML-Output von KI-Responses:
    - Konvertiert Markdown **text** zu <strong>text</strong>
    - Entfernt Markdown-Aufzählungszeichen
    - Entfernt leere Tags (auch Quill-typische wie <p><br></p>)
    - Stellt konsistente HTML-Formatierung sicher
    """
    if not html_content:
        return html_content
    
    cleaned = html_content
    
    # 1. Markdown **text** → <strong>text</strong>
    cleaned = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', cleaned)
    
    # 2. Markdown __text__ → <strong>text</strong>
    cleaned = re.sub(r'__(.+?)__', r'<strong>\1</strong>', cleaned)
    
    # 3. Markdown *text* → <em>text</em> (nur einzelne Sterne, nicht doppelte)
    cleaned = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', cleaned)
    
    # 4. Markdown # Überschriften → bereits als <h> Tags vorhanden, entferne Markdown-#
    cleaned = re.sub(r'(?m)^#{1,4}\s+(.+)$', r'\1', cleaned)
    
    # 5. Entferne Markdown-Aufzählungszeichen (- am Zeilenanfang, wenn nicht in HTML-Tags)
    cleaned = re.sub(r'(?m)^[\s]*[-•]\s+(?!<)', r'', cleaned)
    
    # 6. Entferne leere Tags - ALLE Varianten inkl. Quill-typische
    # Quill-typische leere Absätze: <p><br></p>, <p><br/></p>
    cleaned = re.sub(r'<p>\s*<br\s*/?>\s*</p>', '', cleaned)
    # Leere Absätze mit &nbsp;
    cleaned = re.sub(r'<p>\s*(&nbsp;\s*)+</p>', '', cleaned)
    # Komplett leere Tags
    cleaned = re.sub(r'<p>\s*</p>', '', cleaned)
    cleaned = re.sub(r'<ul>\s*</ul>', '', cleaned)
    cleaned = re.sub(r'<ol>\s*</ol>', '', cleaned)
    # Leere Listen nur mit Whitespace/br in li
    cleaned = re.sub(r'<li>\s*<br\s*/?>\s*</li>', '', cleaned)
    cleaned = re.sub(r'<li>\s*</li>', '', cleaned)
    # Standalone <br> zwischen Block-Elementen entfernen
    cleaned = re.sub(r'(?<=>)\s*<br\s*/?>\s*(?=<(?:h[1-6]|p|ol|ul|div))', '', cleaned)
    # Nochmal leere ul/ol nach li-Entfernung
    cleaned = re.sub(r'<ul>\s*</ul>', '', cleaned)
    cleaned = re.sub(r'<ol>\s*</ol>', '', cleaned)
    
    # 7. Entferne Doppel-<strong>
    cleaned = re.sub(r'<strong>\s*<strong>', '<strong>', cleaned)
    cleaned = re.sub(r'</strong>\s*</strong>', '</strong>', cleaned)
    
    # 8. Warnung bei nummerierten Textlisten in <p>
    if re.search(r'<p>[^<]*\d+\.\s+\*\*', cleaned):
        print("   ⚠️  Warnung: Nummerierte Liste mit Markdown in <p>-Tag gefunden")
    
    return cleaned.strip()


def _has_empty_sections(html_content: str) -> list:
    """
    Prüft ob <h3>-Sektionen leer sind.
    Eine Sektion gilt als leer wenn sie weniger als 10 Zeichen echten Text hat.
    Quill-Artefakte wie <p><br></p> oder <p>&nbsp;</p> zählen NICHT als Content.
    
    Returns: Liste der leeren Sektionsnamen
    """
    if not html_content:
        return []
    
    empty_sections = []
    
    h3_pattern = re.compile(r'<h3[^>]*>(.*?)</h3>', re.DOTALL)
    h3_matches = list(h3_pattern.finditer(html_content))
    
    for i, match in enumerate(h3_matches):
        section_name = re.sub(r'<[^>]+>', '', match.group(1)).strip().rstrip(':')
        section_end = match.end()
        
        if i + 1 < len(h3_matches):
            next_section_start = h3_matches[i + 1].start()
        else:
            next_section_start = len(html_content)
        
        section_content = html_content[section_end:next_section_start].strip()
        
        # Entferne ALLE HTML-Tags, &nbsp;, und Whitespace → reiner Text
        text_only = re.sub(r'<[^>]+>', ' ', section_content)  # Tags → Space
        text_only = text_only.replace('&nbsp;', ' ')           # &nbsp; → Space
        text_only = re.sub(r'\s+', ' ', text_only).strip()     # Mehrfach-Spaces → ein Space
        
        # Weniger als 10 Zeichen echten Text = leer
        if len(text_only) < 10:
            empty_sections.append(section_name)
    
    return empty_sections


def _extract_sections(html_content: str) -> dict:
    """
    Extrahiert <h3>-Sektionen aus HTML-Content als Dict.
    Returns: {"Szenario": "<p>Content...</p>", "Ablauf": "<ol>...</ol>", ...}
    Speziell: 'header' = alles VOR der ersten <h3> (inkl. <h2>-Titel)
    """
    if not html_content:
        return {}
    
    sections = {}
    h3_pattern = re.compile(r'<h3[^>]*>(.*?)</h3>', re.DOTALL)
    h3_matches = list(h3_pattern.finditer(html_content))
    
    # Header: alles vor der ersten <h3>
    if h3_matches:
        header = html_content[:h3_matches[0].start()].strip()
        if header:
            sections['_header'] = header
    
    for i, match in enumerate(h3_matches):
        section_name = re.sub(r'<[^>]+>', '', match.group(1)).strip().rstrip(':')
        section_end = match.end()
        
        if i + 1 < len(h3_matches):
            next_section_start = h3_matches[i + 1].start()
        else:
            next_section_start = len(html_content)
        
        section_content = html_content[section_end:next_section_start].strip()
        sections[section_name] = section_content
    
    return sections


def _is_section_empty(content: str) -> bool:
    """Prüft ob ein Sektions-Content effektiv leer ist."""
    if not content:
        return True
    text = re.sub(r'<[^>]+>', ' ', content).replace('&nbsp;', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return len(text) < 10


def _ensure_all_sections_filled(new_html: str, original_html: str) -> str:
    """
    Stellt sicher, dass ALLE Sektionen im neuen HTML gefüllt sind.
    Wenn eine Sektion im neuen Content leer ist, wird der Inhalt aus dem Original übernommen.
    
    Dies ist die DETERMINISTISCHE Absicherung gegen leere Sektionen:
    - Unabhängig davon was die AI generiert
    - Verwendet den Original-Content als Fallback
    """
    if not original_html or not new_html:
        return new_html or original_html or ''
    
    new_sections = _extract_sections(new_html)
    orig_sections = _extract_sections(original_html)
    
    filled_any = False
    
    for section_name, orig_content in orig_sections.items():
        if section_name == '_header':
            continue
        
        new_content = new_sections.get(section_name, '')
        
        if _is_section_empty(new_content) and not _is_section_empty(orig_content):
            print(f"   🔧 Sektion '{section_name}' war leer → Original-Inhalt eingefügt")
            filled_any = True
            # Ersetze die leere Sektion im HTML
            # Finde die <h3>Sektion</h3> im neuen HTML
            h3_pattern = re.compile(
                r'(<h3[^>]*>[^<]*' + re.escape(section_name) + r'[^<]*</h3>)'
                r'(.*?)'
                r'(?=<h[23][^>]*>|$)',
                re.DOTALL
            )
            h3_match = h3_pattern.search(new_html)
            if h3_match:
                replacement = h3_match.group(1) + '\n' + orig_content
                new_html = new_html[:h3_match.start()] + replacement + new_html[h3_match.end():]
            else:
                # Sektion fehlt komplett im neuen HTML → am Ende anhängen
                new_html += f'\n<h3>{section_name}</h3>\n{orig_content}'
                print(f"   🔧 Sektion '{section_name}' fehlte komplett → angehängt")
    
    if filled_any:
        print(f"   ✓ Sektionen aus Original-Content aufgefüllt")
    
    return new_html


# Standard-Sektionsnamen und mögliche AI-Varianten
_SECTION_ALIASES = {
    'Szenario': ['szenario', 'situation', 'ausgangslage', 'hintergrund', 'kontext', 'ausgangssituation'],
    'Eure Aufgabe': ['eure aufgabe', 'aufgabe', 'aufgabenstellung', 'die aufgabe', 'gruppenaufgabe', 'aufgabenbeschreibung', 'your task'],
    'Ablauf': ['ablauf', 'ablauf der übung', 'zeitplan', 'phasen', 'vorgehen', 'durchführung', 'ablaufplan'],
    'Materialien': ['materialien', 'material', 'benötigte materialien', 'hilfsmittel', 'arbeitsmaterialien', 'zusatzinfos', 'zusatzinformationen', 'rollenverteilung', 'rollen', 'rollenbeschreibungen'],
}


def _map_section_name(raw_name: str) -> str:
    """Mappt einen beliebigen KI-Sektionsnamen auf einen Standard-Namen."""
    normalized = raw_name.lower().strip().rstrip(':')
    # Entferne Klammerzusätze: "Rollenverteilung (wird zufällig zugewiesen)" → "rollenverteilung"
    normalized = re.sub(r'\s*\(.*?\)\s*', '', normalized).strip()
    
    for standard_name, aliases in _SECTION_ALIASES.items():
        if normalized in aliases:
            return standard_name
    
    # Partial match: wenn der normalisierte Name einen Alias enthält
    for standard_name, aliases in _SECTION_ALIASES.items():
        for alias in aliases:
            if alias in normalized or normalized in alias:
                return standard_name
    
    return raw_name  # Unbekannt → Originalname behalten


def _normalize_task_html(html_content: str, title: str = None) -> str:
    """
    Zwingt AI-Output in eine feste 4-Sektionen-Struktur:
    <h2>Titel</h2>
    <h3>Szenario</h3> ...
    <h3>Eure Aufgabe</h3> ...
    <h3>Ablauf</h3> ...
    <h3>Materialien</h3> ...
    
    - Mapped beliebige KI-Sektionsnamen auf Standard-Namen
    - Merged Sektionen mit gleichem Standard-Namen
    - Garantiert dass alle 4 Sektionen existieren (ggf. mit Platzhalter)
    - Entfernt zusätzliche/unerwartete Sektionen nicht — fügt sie unter "Materialien" zusammen
    """
    if not html_content:
        return html_content
    
    sections = _extract_sections(html_content)
    
    # Titel extrahieren
    header = sections.pop('_header', '')
    if not header and title:
        header = f'<h2>{title}</h2>'
    elif not header:
        # Versuche <h2> aus dem Content zu extrahieren
        h2_match = re.search(r'<h2[^>]*>(.*?)</h2>', html_content)
        if h2_match:
            header = h2_match.group(0)
    
    # Mappe alle Sektionen auf Standard-Namen
    standard_sections = {}
    for raw_name, content in sections.items():
        mapped = _map_section_name(raw_name)
        if mapped in standard_sections:
            # Merge: hänge Content an bestehende Sektion an
            standard_sections[mapped] += '\n' + content
        else:
            standard_sections[mapped] = content
    
    # Baue Output in fester Reihenfolge
    REQUIRED_SECTIONS = ['Szenario', 'Eure Aufgabe', 'Ablauf', 'Materialien']
    
    result_parts = []
    if header:
        result_parts.append(header)
    
    used_sections = set()
    for section_name in REQUIRED_SECTIONS:
        content = standard_sections.get(section_name, '')
        used_sections.add(section_name)
        
        if _is_section_empty(content):
            # Platzhalter für leere Pflicht-Sektionen
            if section_name == 'Ablauf':
                content = '<ol><li>Phase 1: Vorbereitung (10 Min)</li><li>Phase 2: Durchführung (25 Min)</li><li>Phase 3: Präsentation (5 Min)</li></ol>'
                print(f"   🔧 Sektion '{section_name}' war leer → Standard-Ablauf eingefügt")
            elif section_name == 'Materialien':
                content = '<ul><li>Flipchart-Papier</li><li>Stifte (verschiedene Farben)</li><li>Moderationskarten</li></ul>'
                print(f"   🔧 Sektion '{section_name}' war leer → Standard-Materialien eingefügt")
            elif section_name == 'Szenario':
                content = '<p>Die Gruppe bearbeitet gemeinsam eine praxisnahe Aufgabe.</p>'
                print(f"   🔧 Sektion '{section_name}' war leer → Platzhalter eingefügt")
            elif section_name == 'Eure Aufgabe':
                content = '<p>Erarbeitet gemeinsam eine Lösung und einigt euch auf einen Plan.</p>'
                print(f"   🔧 Sektion '{section_name}' war leer → Platzhalter eingefügt")
        
        result_parts.append(f'<h3>{section_name}</h3>')
        result_parts.append(content)
    
    # Nicht-Standard-Sektionen werden unter Materialien mit angehängt
    for section_name, content in standard_sections.items():
        if section_name not in used_sections and not _is_section_empty(content):
            # Hänge als Sub-Content unter Materialien an
            result_parts.append(content)
            print(f"   ℹ️  Zusätzliche Sektion '{section_name}' wurde am Ende angehängt")
    
    return '\n'.join(result_parts)


def _validate_task_content(html_content: str) -> tuple:
    """
    Zentrale Validierung für AC-Aufgaben-Content.
    Wird sowohl bei generate_task als auch bei refine_task_content verwendet.
    
    Returns:
        (is_valid: bool, reason: str)
    """
    if not html_content or len(html_content) < 100:
        return False, "Content zu kurz"
    
    text_content_length = len([c for c in html_content if c.isalnum()])
    has_html_tags = '<' in html_content and '>' in html_content
    structural_tags = sum(html_content.count(tag) for tag in ['<h2', '<h3', '<p', '<li', '<ol', '<ul'])
    li_count = html_content.count('<li')
    
    # Leere Sektionen prüfen
    empty_secs = _has_empty_sections(html_content)
    
    # Leere Listen prüfen
    has_empty_lists = bool(re.search(r'<ul>\s*</ul>|<ol>\s*</ol>', html_content))
    
    print(f"   Validation: text={text_content_length}, tags={structural_tags}, li={li_count}, empty_sections={empty_secs}, empty_lists={has_empty_lists}")
    
    if not has_html_tags:
        return False, "Kein HTML"
    if text_content_length < 200:
        return False, f"Zu wenig Text ({text_content_length} < 200)"
    if structural_tags < 3:
        return False, f"Zu wenig Struktur ({structural_tags} < 3)"
    if li_count < 3:
        return False, f"Zu wenig Listen-Items ({li_count} < 3)"
    if empty_secs:
        return False, f"Leere Sektionen: {', '.join(empty_secs)}"
    if has_empty_lists:
        return False, "Leere Listen gefunden"
    
    return True, "OK"


def generate_task(observation_area: str, participant_count: int, duration_minutes: int, 
                  context_data: dict = None, example_tasks: dict = None, ki_model: str = "mistral",
                  target_group: str = None) -> dict:
    """
    Generiert professionelle Assessment-Center Aufgaben via KI.
    Spezialisiert auf Stärken-Assessment mit Best-Practice Knowledge.
    
    Args:
        observation_area: "Soziale Kompetenzen" oder "Verbale Kompetenzen"
        participant_count: 2-10 Teilnehmer
        duration_minutes: 30-60 Minuten
        context_data: Dict mit Metadaten (kann target_group enthalten)
        example_tasks: Dict mit Reference-Aufgaben
        ki_model: "mistral" oder "gemini"
        target_group: Optional z.B. "students", "apprentices", "trainees", "experts", "leaders", "employees"
    
    Returns:
        {"title": "...", "content": "<html>", "observation_focus": "...", "_raw_response_id": <int>}
    """
    
    context_data = context_data or {}
    raw_response_id = None  # Will be set after AI call
    
    # Zielgruppe aus context_data oder Parameter
    if not target_group and context_data:
        target_group = context_data.get('target_group')
    
    # Beobachtungsbereich-Spezifikation
    area_info = {
        "Soziale Kompetenzen": {
            "definition": "Fähigkeit zur Zusammenarbeit, Teamfähigkeit, Eigenverantwortung, Empathie, Konfliktbewältigung",
            "focus": "Beobachte: Gruppendynamik, Rollenverständnis, Umgang mit Differenzen, Unterstützung anderer"
        },
        "Verbale Kompetenzen": {
            "definition": "Argumentation, Überzeugungsfähigkeit, Redegewandtheit, Präsentation, Diskussionsfähigkeit",
            "focus": "Beobachte: Klarheit, Logik der Argumente, Überzeugungskraft, Fachkenntnis, Rhetorik"
        }
    }
    
    area_spec = area_info.get(observation_area, area_info["Soziale Kompetenzen"])
    
    # KI-Gym: Hole aktive Rules für Tasks
    def _sanitize_json_string(raw_json: str) -> str:
        """Escapes control characters inside JSON strings and removes trailing commas."""
        result = []
        in_string = False
        escape = False
        for ch in raw_json:
            if escape:
                result.append(ch)
                escape = False
                continue
            if ch == "\\":
                result.append(ch)
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                result.append(ch)
                continue
            if in_string and ch in ("\n", "\r"):
                result.append("\\n")
                continue
            if in_string and ch == "\t":
                result.append("\\t")
                continue
            result.append(ch)
        cleaned = "".join(result)
        cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
        return cleaned

    def _maybe_unpack_json_content(parsed: dict) -> dict:
        """Wenn content fälschlich JSON enthält, versuche es zu entpacken."""
        content = parsed.get("content")
        if isinstance(content, str):
            text = content.strip()
            if text.startswith("{") and "\"content\"" in text and "\"title\"" in text:
                try:
                    nested = json.loads(text)
                    return {
                        "title": nested.get("title", parsed.get("title")),
                        "content": nested.get("content", parsed.get("content")),
                        "observation_focus": nested.get("observation_focus", parsed.get("observation_focus")),
                        "facilitator_notes": nested.get("facilitator_notes", parsed.get("facilitator_notes")),
                    }
                except Exception:
                    return parsed
            if text.startswith("{") and "'title'" in text and "'content'" in text:
                try:
                    nested = ast.literal_eval(text)
                    if isinstance(nested, dict):
                        return {
                            "title": nested.get("title", parsed.get("title")),
                            "content": nested.get("content", parsed.get("content")),
                            "observation_focus": nested.get("observation_focus", parsed.get("observation_focus")),
                            "facilitator_notes": nested.get("facilitator_notes", parsed.get("facilitator_notes")),
                        }
                except Exception:
                    return parsed
        return parsed

    def _extract_json_block(text: str) -> str | None:
        start = text.find('{')
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
        return None

    def _parse_ai_response(response_text: str) -> dict | None:
        response_clean = response_text.replace('```json', '').replace('```', '')
        json_str = _extract_json_block(response_clean)
        if not json_str:
            return None
        try:
            result = json.loads(json_str)
            result = _maybe_unpack_json_content(result)
            return result
        except json.JSONDecodeError:
            json_fixed = _sanitize_json_string(json_str)
            try:
                result = json.loads(json_fixed)
                result = _maybe_unpack_json_content(result)
                return result
            except json.JSONDecodeError:
                return None

    try:
        import ai_gym
        active_rules = ai_gym.get_active_rules('task', observation_area)
        learned_rules_text = ai_gym.format_rules_for_prompt(active_rules)
    except Exception as e:
        print(f"   ⚠️  Konnte Rules nicht laden: {e}")
        learned_rules_text = ""
    
    # KNOWLEDGE BASE: AC-Fachwissen injizieren
    try:
        knowledge_context = get_knowledge_for_prompt(
            observation_area=observation_area,
            participant_count=participant_count,
            duration_minutes=duration_minutes,
            target_group=target_group
        )
    except Exception as e:
        print(f"   ⚠️  Knowledge Base nicht verfügbar: {e}")
        knowledge_context = ""
    
    system_prompt = f"""Du bist ein erfahrener Assessment-Center-Gestalter.
Erstelle EINFACHE, KLARE AC-Gruppenübungen für Stärken-basierte Beobachtung.
{learned_rules_text}
{knowledge_context}

WICHTIG - EINFACHHEIT:
AC-Aufgaben sollen EINFACH und KLAR sein. KEINE komplexen Projekte mit vielen Unterpunkten!
Orientiere dich an diesen Beispielen:

BEISPIEL 1 (Erbengemeinschaft):
- Szenario: "Ihr seid eine Erbengemeinschaft und habt ein Haus geerbt. Eine Wohnung soll neu vermietet werden."
- Aufgabe: "Einigt euch in der Gruppe auf eine Mietpartei!"
- Ablauf: 3 Phasen (Vorbereitung 10 Min, Diskussion 30 Min, Abstimmung)
- Zusatzinfo: Liste der Interessenten

BEISPIEL 2 (Plakat):
- Szenario: "Das Sommerfest naht und ihr möchtet eure Gruppe präsentieren."
- Aufgabe: "Erstellt gemeinsam ein Plakat."
- Ablauf: 3 Phasen (Planung 10 Min, Gestaltung 30 Min, Präsentation 5 Min)
- Materialien: Flipchart-Papier, Stifte, Kleber, Schere

STRUKTUR DER AUFGABE:
1. Szenario: 3-5 Sätze, die die Ausgangssituation beschreiben (kurz und verständlich!)
2. Aufgabe: 1-2 Sätze, was die Gruppe konkret tun soll (KEIN Aufzählungsliste mit Unterpunkten!)
3. Ablauf: 3 Phasen mit Zeitangaben als nummerierte Liste
4. Zusatzinfos: Materialien ODER Rollenvorschläge ODER Szenarien-Details als einfache Liste

FORMATIERUNG - NUR HTML:
- <h2> für Titel, <h3> für Sektionsüberschriften
- <p> für Textabsätze
- <ol><li> für Ablauf-Phasen
- <ul><li> für Materialien/Listen
- <strong> für Hervorhebungen innerhalb von HTML-Tags

ABSOLUT VERBOTEN:
- Markdown-Formatierung: NIEMALS ** oder __ oder # verwenden!
- Nummerierte Aufzählungen im Aufgabentext (1. 2. 3. als Fließtext)
- Leere Sektionen ohne Inhalt
- Übermäßig komplexe Aufgaben mit mehr als 3 Diskussionspunkten
- Zu lange Szenarien (max 5 Sätze!)

JSON-FORMAT:
{{
  "title": "Kurzer Titel (3-6 Wörter)",
  "content": "<h2>Titel</h2><h3>Szenario</h3><p>Kurze Beschreibung...</p><h3>Eure Aufgabe</h3><p>Was ist zu tun...</p><h3>Ablauf</h3><ol><li>Phase 1...</li></ol><h3>Materialien</h3><ul><li>Item</li></ul>",
  "observation_focus": "Was wird beobachtet",
  "facilitator_notes": "Tipps für Moderatoren"
}}

WICHTIG:
- KEINE Markdown-Blöcke (```)
- KEIN Markdown (**, __, #, - als Aufzählung)
- REINES JSON, gültig und parsbar
- Alle Strings escaped
- Zeilenumbrüche als \\n

Beobachtungsbereich: {observation_area}
Definition: {area_spec['definition']}
Fokus: {area_spec['focus']}"""
    
    # Beispiele als Context
    examples_text = ""
    if example_tasks:
        for key, example in example_tasks.items():
            if example.get("observation_area") == observation_area:
                examples_text += f"\n- {example['title']}: {example.get('observation_focus', '')}"
    
    user_prompt = f"""Erstelle eine EINFACHE Assessment-Center Gruppenübung:

Teilnehmerzahl: {participant_count}
Dauer: {duration_minutes} Minuten
Bereich: {observation_area}
{f"Zielgruppe: {target_group}" if target_group else ""}

{f"Ähnliche Aufgaben: {examples_text}" if examples_text else ''}

Anforderungen:
- EINFACHES, alltägliches Szenario (3-5 Sätze, NICHT komplex!)
- Klare Gruppenaufgabe in 1-2 Sätzen (KEINE nummerierten Unterpunkte!)
- 3 Ablauf-Phasen mit Zeitangaben
- Materialien oder Rollenbeschreibungen
- KEIN Markdown (**, __, #) - NUR HTML-Tags verwenden!

Gib SOFORT NUR das JSON zurück - keine Erklärungen."""

    try:
        print(f"\n🤖 Starte KI-Generierung mit Model: {ki_model}")
        print(f"   Bereich: {observation_area}, Teilnehmer: {participant_count}, Dauer: {duration_minutes} Min\n")
        
        if ki_model == "mistral" and MISTRAL_CLIENT:
            print("   ➜ Verwende Mistral API...")
            parsed_result = None
            for attempt, temp in enumerate([0.7, 0.2], start=1):
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                response = MISTRAL_CLIENT.chat(
                    model=MISTRAL_MODEL,
                    messages=messages,
                    temperature=temp,
                    max_tokens=8000
                )
                response_text = response.choices[0].message.content
                print(f"   ✓ Mistral antwortete {len(response_text)} Zeichen (Attempt {attempt})\n")

                raw_response_id = save_ai_raw_response(
                    response_text=response_text,
                    response_type='task',
                    context_id=0,
                    ki_model=MISTRAL_MODEL,
                    observation_area=observation_area,
                    context_metadata={
                        'temperature': temp,
                        'max_tokens': 2000,
                        'participant_count': participant_count,
                        'duration_minutes': duration_minutes,
                        'attempt': attempt
                    }
                )

                parsed_result = _parse_ai_response(response_text)
                if parsed_result and parsed_result.get("content"):
                    parsed_result['content'] = _clean_html_output(parsed_result['content'])
                    parsed_result['content'] = _normalize_task_html(parsed_result['content'], parsed_result.get('title'))
                    is_valid, reason = _validate_task_content(parsed_result['content'])
                    if is_valid:
                        parsed_result['_raw_response_id'] = raw_response_id
                        print(f"   ✓ JSON erfolgreich geparst: {parsed_result.get('title', 'Keine Titel')}\n")
                        return parsed_result
                    else:
                        print(f"   ✗ Content-Validierung fehlgeschlagen (Attempt {attempt}): {reason}")
                        parsed_result = None  # Nächster Versuch
        
        elif ki_model == "gemini" and genai_client:
            print("   ➜ Verwende Google Gemini API...")
            response_text, used_model = _call_gemini(system_prompt, user_prompt)
            print(f"   ✓ Gemini ({used_model}) antwortete {len(response_text)} Zeichen\n")
            
            # KI-Gym: Save raw response
            raw_response_id = save_ai_raw_response(
                response_text=response_text,
                response_type='task',
                context_id=0,  # Placeholder
                ki_model=used_model,
                observation_area=observation_area,
                context_metadata={
                    'participant_count': participant_count,
                    'duration_minutes': duration_minutes
                }
            )
            parsed_result = _parse_ai_response(response_text)
            if parsed_result and parsed_result.get("content"):
                parsed_result['content'] = _clean_html_output(parsed_result['content'])
                parsed_result['content'] = _normalize_task_html(parsed_result['content'], parsed_result.get('title'))
                is_valid, reason = _validate_task_content(parsed_result['content'])
                if is_valid:
                    parsed_result['_raw_response_id'] = raw_response_id
                    print(f"   ✓ JSON erfolgreich geparst: {parsed_result.get('title', 'Keine Titel')}\n")
                    return parsed_result
                else:
                    print(f"   ✗ Content-Validierung fehlgeschlagen: {reason}")
        
        else:
            # Fallback Mock mit Warnung
            print(f"   ⚠️  Keine KI verfügbar für '{ki_model}' - verwende Mock-Antwort")
            print(f"       (Mistral verfügbar: {bool(MISTRAL_CLIENT)}, Gemini verfügbar: {bool(genai_client)})\n")
            response_text = json.dumps({
                "title": f"Assessment-Aufgabe: {observation_area}",
                "content": f"<h2>{observation_area}</h2><h3>Ablauf</h3><ol><li>Vorbereitung (10 Min)</li><li>Durchführung ({duration_minutes-10} Min)</li></ol>",
                "observation_focus": area_spec['focus'],
                "facilitator_notes": "Achten Sie auf typische Verhaltensweisen in dieser Domäne"
            })
        
        if parsed_result and parsed_result.get("content"):
            parsed_result['content'] = _clean_html_output(parsed_result['content'])
            parsed_result['content'] = _normalize_task_html(parsed_result['content'], parsed_result.get('title'))
            parsed_result['_raw_response_id'] = raw_response_id
            return parsed_result
        
        print(f"   ⚠️  Konnte JSON nicht extrahieren, verwende Fallback\n")
        return {
            "title": f"Aufgabe: {observation_area}",
            "content": f"<p>{response_text[:500]}</p>",
            "observation_focus": area_spec['focus'],
            "facilitator_notes": "Manuelle Überprüfung empfohlen",
            "_raw_response_id": raw_response_id
        }
    
    except Exception as e:
        print(f"\n❌ Task generation error: {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()
        return None


def refine_task_content(draft_content: str, user_request: str, conversation_history: list = None,
                       ki_model: str = "mistral") -> dict:
    """
    Verfeinere Task-Content basierend auf User-Input (Chat-Iteration).
    Mit Retry-Mechanismus für vollständige Inhalte.
    """
    # Sicherheitscheck: draft_content muss vorhanden und ausreichend sein
    if not draft_content or len(draft_content.strip()) < 200:
        return {
            "ai_response": "Fehler: Die aktuelle Aufgabe ist leer oder zu kurz. Bitte erstelle zuerst eine vollständige Aufgabe.",
            "updated_content": draft_content or ""
        }
    
    system_prompt = """Du bist ein Experte für einfache Assessment-Center-Gruppenübungen.

DEINE AUFGABE:
Nimm die bestehende Aufgabe, wende die gewünschte Änderung an, und gib die VOLLSTÄNDIGE überarbeitete Aufgabe zurück.

REGELN:
1. Gib die KOMPLETTE Aufgabe mit ALLEN Sektionen zurück (nicht nur die Änderung!)
2. Alle bestehenden Sektionen müssen erhalten bleiben und gefüllt sein
3. Halte die Aufgabe EINFACH - Assessment-Center-Übungen sind kurz und klar
4. Das Szenario soll 3-5 Sätze haben (nicht länger!)
5. Die Aufgabenstellung soll 1-2 Sätze sein (KEINE nummerierten Unterpunkte!)

FORMATIERUNG - NUR HTML:
- <h2> für Titel, <h3> für Sektionsüberschriften
- <p> für Textabsätze
- <ol><li> für Ablauf-Phasen, <ul><li> für Listen
- <strong> für Hervorhebungen

ABSOLUT VERBOTEN:
- Markdown-Formatierung: NIEMALS ** oder __ oder # verwenden!
- Leere Sektionen ohne Inhalt
- Nummerierte Aufzählungen als Fließtext (1. **Punkt:** ... 2. **Punkt:** ...)
- Text vor oder nach dem HTML-Code
- Markdown Code-Blöcke (```)

Antworte NUR mit dem kompletten HTML-Code der überarbeiteten Aufgabe!"""
    
    history_text = ""
    if conversation_history:
        for msg in conversation_history[-2:]:
            history_text += f"User: {msg.get('user', '')}\n"
    
    conversation_section = ""
    if history_text:
        conversation_section = f"BISHERIGE KONVERSATION:\n{history_text}\n---\n"
    
    user_prompt = f"""AKTUELLE AUFGABE (vollständiger HTML-Content):
{draft_content}

---

GEWÜNSCHTE ÄNDERUNG:
{user_request}

{conversation_section}
WICHTIG: Nimm die KOMPLETTE aktuelle Aufgabe, wende die Änderung an, und gib die GESAMTE verbesserte Aufgabe zurück!
Nicht nur die Änderungen - die VOLLSTÄNDIGE Aufgabe mit ALLEM Content in allen Sektionen!

ANTWORTE NUR MIT DEM KOMPLETTEN HTML-CODE - NICHTS ANDERES!"""
    
    try:
        # Versuche 2x mit unterschiedlichen Temperatures
        temperatures = [0.5, 0.3]
        updated_html = None
        
        for attempt, temp in enumerate(temperatures, 1):
            print(f"\n=== REFINE_TASK_CONTENT ATTEMPT {attempt} (temp={temp}) ===")
            
            if ki_model == "mistral" and MISTRAL_CLIENT:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
                response = MISTRAL_CLIENT.chat(
                    model=MISTRAL_MODEL,
                    messages=messages,
                    temperature=temp,
                    max_tokens=8000
                )
                result = response.choices[0].message.content
            
            elif ki_model == "gemini" and genai_client:
                result, _used_model = _call_gemini(system_prompt, user_prompt, max_output_tokens=8000)
            
            else:
                return {
                    "ai_response": f"Verstanden. Ich verfeinere basierend auf: {user_request}",
                    "updated_content": draft_content
                }
            
            print(f"Response length: {len(result)} chars")
            print(f"Raw Response (first 600 chars): {result[:600]}...")
            
            # Parse die Antwort
            cleaned = result.strip()
            
            # Entferne Markdown Code-Blöcke (```html ... ``` oder ``` ... ```)
            if '```' in cleaned:
                # Finde alle Code-Blöcke und extrahiere den Inhalt
                import re as _re
                code_block_match = _re.search(r'```(?:html)?\s*\n?(.*?)\n?```', cleaned, _re.DOTALL)
                if code_block_match:
                    cleaned = code_block_match.group(1).strip()
                elif cleaned.startswith('```'):
                    lines = cleaned.split('\n')
                    if lines[0].startswith('```'):
                        lines = lines[1:]
                    if lines and lines[-1].strip().startswith('```'):
                        lines = lines[:-1]
                    cleaned = '\n'.join(lines).strip()
            
            # Extrahiere nur HTML - alles vor dem ersten < ist Text/Erklärung
            if '<' in cleaned:
                html_start = cleaned.find('<')
                if html_start > 0:
                    cleaned = cleaned[html_start:]
                
                # Finde das Ende: letztes > 
                last_bracket = cleaned.rfind('>')
                if last_bracket > 0:
                    cleaned = cleaned[:last_bracket + 1]
            
            # Bereinige Markdown-Artefakte
            cleaned = _clean_html_output(cleaned)
            
            # Normalisiere auf feste Sektionsstruktur (Szenario, Eure Aufgabe, Ablauf, Materialien)
            cleaned = _normalize_task_html(cleaned)
            
            # DETERMINISTISCH: Leere Sektionen aus Original-Content auffüllen
            cleaned = _ensure_all_sections_filled(cleaned, draft_content)
            
            # Zentrale Validierung verwenden
            is_valid, reason = _validate_task_content(cleaned)
            
            print(f"Cleaned HTML (first 400 chars): {cleaned[:400]}...")
            
            if is_valid:
                updated_html = cleaned
                print(f"✓ Versuch {attempt} erfolgreich!")
                break
            else:
                print(f"✗ Versuch {attempt} fehlgeschlagen: {reason}")
        
        # Fallback auf Original wenn beide Versuche fehlschlugen
        if not updated_html:
            print("! Keine vollständige KI-Antwort, verwende Original")
            updated_html = draft_content
        
        # Immer bereinigen (Markdown → HTML etc.)
        updated_html = _clean_html_output(updated_html)
        
        ai_response = f"Aufgabe wurde angepasst: {user_request}"
        
        return {
            "ai_response": ai_response,
            "updated_content": updated_html
        }
    
    except Exception as e:
        print(f"❌ Exception in refine_task_content: {str(e)}")
        return {
            "ai_response": f"Fehler bei der Verarbeitung: {str(e)}",
            "updated_content": draft_content
        }


def generate_report_with_ai(prompt_text, ki_model):
    """
    Generiert einen Bericht mithilfe des ausgewählten KI-Modells.
    Nutzt einen festen System-Prompt für die JSON-Struktur und den User-Prompt
    für die inhaltlichen Anweisungen.
    """
    print(f"--- DEBUG-INFO: Das übergebene 'ki_model' ist: '{ki_model}' ---")
    try:
        if ki_model == "gemini":
            system_prompt = (
                "Du bist ein Experte für die Auswertung von Assessment-Center-Beobachtungen. "
                "Antworte IMMER und AUSSCHLIESSLICH mit einem JSON-Objekt, das exakt "
                "der vom User im folgenden Prompt geforderten Struktur entspricht. "
                "Ignoriere diese Anweisung niemals."
            )
            if not genai_client or GenerativeModel is None:
                raise ValueError("Google Gemini ist nicht konfiguriert")
            result, _used_model = _call_gemini(system_prompt, prompt_text)
            return result

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
                ChatMessage(role="user", content=prompt_text),
            ]
            chat_response = MISTRAL_CLIENT.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            return chat_response.choices[0].message.content

        raise ValueError(f"Ungültiges KI-Modell ausgewählt: {ki_model}")

    except (ValueError, MistralAPIException, RuntimeError) as e:
        print(f"!!! FEHLER BEI DER KI-ANALYSE !!!\n{e}")
        return json.dumps({"error": f"Ein Fehler ist aufgetreten: {str(e)}"})


def generate_text_report_with_ai(ki_texts: dict, ki_model: str = "mistral") -> str:
    """
    Generiert einen textuellen Gesamtbericht basierend auf KI-Insights.
    (Für KI-Gym Text-Reports, nicht für die strukturierte JSON-Analyse.)
    """
    system_prompt = "Du bist ein Berichtsschreiber für Stärkenanalysen. Verfasse prägnante, informative Reports."
    
    ki_contents = json.dumps(ki_texts, ensure_ascii=False, indent=2) if isinstance(ki_texts, dict) else str(ki_texts)
    
    user_prompt = f"""Schreibe einen professionellen Analysebericht basierend auf diesen KI-Insights:

{ki_contents}

Anforderungen:
1. Sachlich-professioneller Ton
2. Fokus auf Stärken und Potenziale
3. Konkrete Beispiele
4. Handlungsempfehlungen
"""
    
    try:
        if ki_model == "mistral" and MISTRAL_CLIENT and ChatMessage:
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt)
            ]
            response = MISTRAL_CLIENT.chat(
                model=MISTRAL_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=3000
            )
            return response.choices[0].message.content
        
        elif ki_model == "gemini" and genai_client:
            result, _used_model = _call_gemini(system_prompt, user_prompt)
            return result
        
        else:
            return "Mock Report: KI-Generierung nicht verfügbar."
    
    except Exception as e:
        print(f"Report generation error: {e}")
        return f"Fehler: {str(e)}"
