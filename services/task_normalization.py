"""
Helpers for normalizing and validating task HTML content.
"""

import logging
import re

logger = logging.getLogger(__name__)


def _clean_html_output(html_content: str) -> str:
    """
    Bereinigt HTML-Output von KI-Responses.
    """
    if not html_content:
        return html_content

    cleaned = html_content

    cleaned = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', cleaned)
    cleaned = re.sub(r'__(.+?)__', r'<strong>\1</strong>', cleaned)
    cleaned = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'<em>\1</em>', cleaned)
    cleaned = re.sub(r'(?m)^#{1,4}\s+(.+)$', r'\1', cleaned)
    cleaned = re.sub(r'(?m)^[\s]*[-•]\s+(?!<)', r'', cleaned)

    cleaned = re.sub(r'<p>\s*<br\s*/?>\s*</p>', '', cleaned)
    cleaned = re.sub(r'<p>\s*(&nbsp;\s*)+</p>', '', cleaned)
    cleaned = re.sub(r'<p>\s*</p>', '', cleaned)
    cleaned = re.sub(r'<ul>\s*</ul>', '', cleaned)
    cleaned = re.sub(r'<ol>\s*</ol>', '', cleaned)
    cleaned = re.sub(r'<li>\s*<br\s*/?>\s*</li>', '', cleaned)
    cleaned = re.sub(r'<li>\s*</li>', '', cleaned)
    cleaned = re.sub(r'(?<=>)\s*<br\s*/?>\s*(?=<(?:h[1-6]|p|ol|ul|div))', '', cleaned)
    cleaned = re.sub(r'<ul>\s*</ul>', '', cleaned)
    cleaned = re.sub(r'<ol>\s*</ol>', '', cleaned)

    cleaned = re.sub(r'<strong>\s*<strong>', '<strong>', cleaned)
    cleaned = re.sub(r'</strong>\s*</strong>', '</strong>', cleaned)

    if re.search(r'<p>[^<]*\d+\.\s+\*\*', cleaned):
        logger.warning("Nummerierte Liste mit Markdown in <p>-Tag gefunden")

    return cleaned.strip()


def _has_empty_sections(html_content: str) -> list:
    """Prüft ob <h3>-Sektionen leer sind."""
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

        text_only = re.sub(r'<[^>]+>', ' ', section_content)
        text_only = text_only.replace('&nbsp;', ' ')
        text_only = re.sub(r'\s+', ' ', text_only).strip()

        if len(text_only) < 10:
            empty_sections.append(section_name)

    return empty_sections


def _extract_sections(html_content: str) -> dict:
    """
    Extrahiert <h3>-Sektionen aus HTML-Content als Dict.
    """
    if not html_content:
        return {}

    sections = {}
    h3_pattern = re.compile(r'<h3[^>]*>(.*?)</h3>', re.DOTALL)
    h3_matches = list(h3_pattern.finditer(html_content))

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
            logger.info("Sektion '%s' war leer → Original-Inhalt eingefügt", section_name)
            filled_any = True
            h3_pattern = re.compile(
                r'(<h3[^>]*>[^<]*' + re.escape(section_name) + r'[^<]*</h3>)'
                r'(.*?)'
                r'(?=<h[23][^>]*>|$)',
                re.DOTALL,
            )
            h3_match = h3_pattern.search(new_html)
            if h3_match:
                replacement = h3_match.group(1) + '\n' + orig_content
                new_html = new_html[:h3_match.start()] + replacement + new_html[h3_match.end():]
            else:
                new_html += f'\n<h3>{section_name}</h3>\n{orig_content}'
                logger.info("Sektion '%s' fehlte komplett → angehängt", section_name)

    if filled_any:
        logger.info("Sektionen aus Original-Content aufgefüllt")

    return new_html


_SECTION_ALIASES = {
    'Szenario': ['szenario', 'situation', 'ausgangslage', 'hintergrund', 'kontext', 'ausgangssituation'],
    'Eure Aufgabe': ['eure aufgabe', 'aufgabe', 'aufgabenstellung', 'die aufgabe', 'gruppenaufgabe', 'aufgabenbeschreibung', 'your task'],
    'Ablauf': ['ablauf', 'ablauf der übung', 'zeitplan', 'phasen', 'vorgehen', 'durchführung', 'ablaufplan'],
    'Materialien': ['materialien', 'material', 'benötigte materialien', 'hilfsmittel', 'arbeitsmaterialien', 'zusatzinfos', 'zusatzinformationen', 'rollenverteilung', 'rollen', 'rollenbeschreibungen'],
}


def _map_section_name(raw_name: str) -> str:
    """Mappt einen beliebigen KI-Sektionsnamen auf einen Standard-Namen."""
    normalized = raw_name.lower().strip().rstrip(':')
    normalized = re.sub(r'\s*\(.*?\)\s*', '', normalized).strip()

    for standard_name, aliases in _SECTION_ALIASES.items():
        if normalized in aliases:
            return standard_name

    for standard_name, aliases in _SECTION_ALIASES.items():
        for alias in aliases:
            if alias in normalized or normalized in alias:
                return standard_name

    return raw_name


def _normalize_task_html(html_content: str, title: str | None = None) -> str:
    """
    Zwingt AI-Output in eine feste 4-Sektionen-Struktur.
    """
    if not html_content:
        return html_content

    sections = _extract_sections(html_content)

    header = sections.pop('_header', '')
    if not header and title:
        header = f'<h2>{title}</h2>'
    elif not header:
        h2_match = re.search(r'<h2[^>]*>(.*?)</h2>', html_content)
        if h2_match:
            header = h2_match.group(0)

    standard_sections = {}
    for raw_name, content in sections.items():
        mapped = _map_section_name(raw_name)
        if mapped in standard_sections:
            standard_sections[mapped] += '\n' + content
        else:
            standard_sections[mapped] = content

    required_sections = ['Szenario', 'Eure Aufgabe', 'Ablauf', 'Materialien']

    result_parts = []
    if header:
        result_parts.append(header)

    used_sections = set()
    for section_name in required_sections:
        content = standard_sections.get(section_name, '')
        used_sections.add(section_name)

        if _is_section_empty(content):
            if section_name == 'Ablauf':
                content = '<ol><li>Phase 1: Vorbereitung (10 Min)</li><li>Phase 2: Durchführung (25 Min)</li><li>Phase 3: Präsentation (5 Min)</li></ol>'
                logger.info("Sektion '%s' war leer → Standard-Ablauf eingefügt", section_name)
            elif section_name == 'Materialien':
                content = '<ul><li>Flipchart-Papier</li><li>Stifte (verschiedene Farben)</li><li>Moderationskarten</li></ul>'
                logger.info("Sektion '%s' war leer → Standard-Materialien eingefügt", section_name)
            elif section_name == 'Szenario':
                content = '<p>Die Gruppe bearbeitet gemeinsam eine praxisnahe Aufgabe.</p>'
                logger.info("Sektion '%s' war leer → Platzhalter eingefügt", section_name)
            elif section_name == 'Eure Aufgabe':
                content = '<p>Erarbeitet gemeinsam eine Lösung und einigt euch auf einen Plan.</p>'
                logger.info("Sektion '%s' war leer → Platzhalter eingefügt", section_name)

        result_parts.append(f'<h3>{section_name}</h3>')
        result_parts.append(content)

    for section_name, content in standard_sections.items():
        if section_name not in used_sections and not _is_section_empty(content):
            result_parts.append(content)
            logger.info("Zusätzliche Sektion '%s' wurde am Ende angehängt", section_name)

    return '\n'.join(result_parts)


def _validate_task_content(html_content: str) -> tuple:
    """
    Zentrale Validierung für AC-Aufgaben-Content.
    """
    if not html_content or len(html_content) < 100:
        return False, "Content zu kurz"

    text_content_length = len([c for c in html_content if c.isalnum()])
    has_html_tags = '<' in html_content and '>' in html_content
    structural_tags = sum(html_content.count(tag) for tag in ['<h2', '<h3', '<p', '<li', '<ol', '<ul'])
    li_count = html_content.count('<li')

    empty_secs = _has_empty_sections(html_content)
    has_empty_lists = bool(re.search(r'<ul>\s*</ul>|<ol>\s*</ol>', html_content))

    logger.debug(
        "Validation: text=%s, tags=%s, li=%s, empty_sections=%s, empty_lists=%s",
        text_content_length,
        structural_tags,
        li_count,
        empty_secs,
        has_empty_lists,
    )

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
