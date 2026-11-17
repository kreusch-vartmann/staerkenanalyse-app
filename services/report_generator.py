"""
ReportGenerator Service - HTML-Rendering und PDF-Generierung für Abschlussberichte.

Architektur (alle PDF-Berichte laufen durch diese Klasse):
- build_html(mode): Orchestriert alle Module, mode steuert Sidebar-Inhalt
  - 'combined': Gesamt-PDF (Sidebar minimal, ohne Metadaten)
  - 'standalone_se': Nur Selbsteinschätzung (Sidebar voll)
  - 'standalone_fe': Nur Fremdeinschätzung (Sidebar voll)
- Seitenlayout (WeasyPrint, CSS Paged Media):
  - Die Sidebar ist KEINE Flex-Spalte im Seiteninhalt, sondern Teil der
    Seitengestaltung: Hintergrund per @page (SVG), Inhalte (Name, Rahmendaten)
    als "running elements" in den linken Randboxen, "Seite X von Y" über
    counter(page)/counter(pages). Der Inhalt fließt frei über beliebig viele
    Seiten; Sidebar und Seitenzahl wiederholen sich automatisch.
  - Seitentypen über benannte Seiten: cover, sb-se, sb-fe, sb-closing, info.
- _render_*(): Rendert einzelne Module
- _generate_css(): Theme-CSS + @page-Regeln
- render_document()/to_pdf(): Konvertiert HTML zu PDF und prüft die Seitenzahlen
"""

import base64
import json
import logging
import re
from collections import Counter
from datetime import datetime
from html import escape
from io import BytesIO
from pathlib import Path
from urllib.parse import quote

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from flask import render_template_string

from models import (ClientLogo, CompanyLogo, ExplanationBlock, Group,
                    Participant, ReportConfiguration, ReportTemplate,
                    SelfAssessment)
from utils import sanitize_html

logger = logging.getLogger(__name__)

# Seitengeometrie in mm (A4)
PAGE_WIDTH_MM = 210
PAGE_HEIGHT_MM = 297
SIDEBAR_WIDTH_MM = 56
SIDEBAR_PADDING_MM = 6.5
MARGIN_TOP_MM = 20
MARGIN_BOTTOM_MM = 20
MARGIN_RIGHT_MM = 14
CONTENT_GUTTER_MM = 11

# Seitentypen mit Sidebar: Kennung -> (CSS-Seitenname, Kopfzeile, Name der Rahmendaten)
SIDEBAR_PAGES = {
    "se": ("sb-se", "Selbsteinschätzung", "sbMetaSe"),
    "fe": ("sb-fe", "Fremdeinschätzung", "sbMetaFe"),
    "closing": ("sb-closing", "Abschlussblatt", "sbMetaAll"),
}

PAGE_LABELS = {
    "cover": "Deckblatt",
    "sb-se": "Selbsteinschätzung",
    "sb-fe": "Fremdeinschätzung",
    "sb-closing": "Abschlussblatt",
}

DEFAULT_FONT_FAMILY = "Inter, 'Helvetica Neue', Arial, sans-serif"

_HTML_TAG_RE = re.compile(
    r"<\s*/?\s*(p|br|ul|ol|li|strong|em|u|s|h[1-3]|blockquote|div|span)\b", re.I
)
_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{3,8}$")
_FONT_FAMILY_RE = re.compile(r"^[\w\s,'\"\-]+$")


def _safe_color(value, default: str) -> str:
    """Lässt nur Hex-Farben durch (Theme-Werte landen in CSS und SVG)."""
    if isinstance(value, str) and _COLOR_RE.match(value.strip()):
        return value.strip()
    return default


def _safe_font_family(value, default: str = DEFAULT_FONT_FAMILY) -> str:
    if isinstance(value, str) and _FONT_FAMILY_RE.match(value.strip()):
        return value.strip()
    return default


def _rich_text(value) -> str:
    """
    Macht Berichtstexte PDF-tauglich und sicher.

    - HTML (Quill-Editor): wird bereinigt (erlaubte Tags, Rest escaped/entfernt)
    - Klartext (z. B. direkt aus der KI): wird escaped, Zeilenumbrüche werden
      zu Absätzen.
    """
    if not value:
        return ""
    text = str(value)
    if _HTML_TAG_RE.search(text):
        return sanitize_html(text)
    paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    return "".join(f"<p>{escape(p)}</p>" for p in paragraphs)


def _svg_data_uri(svg: str) -> str:
    return "data:image/svg+xml;charset=utf-8," + quote(svg)


class ReportGenerator:
    """
    Generiert komplette Abschlussberichte (HTML oder PDF) für Teilnehmer.
    Nutzt Jinja2 Templates und WeasyPrint für PDF-Export.
    """

    def __init__(
        self, group: Group, participant: Participant, config: ReportConfiguration
    ):
        self.group = group
        self.participant = participant
        self.config = config

        # Parse JSON-Konfigurationen
        self.modules_config = (
            json.loads(config.modules_config) if config.modules_config else {}
        )

        # Lade Design/Theme
        self.template = config.template
        self.theme = (
            json.loads(config.template.design_config)
            if config.template and config.template.design_config
            else {}
        )

        # Logos
        self.company_logo = config.company_logo
        self.client_logo = config.client_logo

        # Projekt-Root für absolute Pfade
        self.project_root = Path(__file__).resolve().parents[1]

        # Participant-Daten
        self.participant_observations = (
            json.loads(participant.observations) if participant.observations else {}
        )
        self.participant_ratings_sk = (
            json.loads(participant.sk_ratings) if participant.sk_ratings else {}
        )
        self.participant_ratings_vk = (
            json.loads(participant.vk_ratings) if participant.vk_ratings else {}
        )
        self.participant_ki_texts = (
            json.loads(participant.ki_texts) if participant.ki_texts else {}
        )

        # Self-Assessment
        self.self_assessment = SelfAssessment.query.filter_by(
            participant_id=participant.id
        ).first()

        # Erklärungstexte (Hinweisblatt)
        info_config = self.modules_config.get("info_page", {})
        selected_ids = info_config.get("selected_block_ids", [])
        if selected_ids:
            self.explanation_blocks = (
                ExplanationBlock.query.filter(ExplanationBlock.id.in_(selected_ids))
                .order_by(ExplanationBlock.order, ExplanationBlock.id)
                .all()
            )
        else:
            self.explanation_blocks = []

        # Signature Images (graceful if model doesn't exist yet)
        self.signature_fe = None
        self.signature_se = None
        try:
            from models import SignatureImage

            self.signature_fe = SignatureImage.query.filter_by(
                role="leitung_fe", is_active=True
            ).first()
            self.signature_se = SignatureImage.query.filter_by(
                role="leitung_se", is_active=True
            ).first()
        except Exception:
            pass

        # Wird bei build_html()/render_document() befüllt
        self.expected_pages = {}
        self.render_warnings = []

    # =========================================================================
    # Theme-Werte
    # =========================================================================

    @property
    def primary(self) -> str:
        return _safe_color(self.theme.get("primary_color"), "#2c3e50")

    @property
    def primary_light(self) -> str:
        return _safe_color(self.theme.get("primary_light"), "#34495e")

    @property
    def secondary(self) -> str:
        return _safe_color(self.theme.get("secondary_color"), "#ecf0f1")

    @property
    def font_family(self) -> str:
        return _safe_font_family(self.theme.get("font_family"))

    def _file_uri(self, relative_path: str):
        """file://-URI für eine hochgeladene Datei, None wenn sie fehlt."""
        path = (self.project_root / relative_path).resolve()
        if not path.is_file():
            logger.warning("Bild für Bericht nicht gefunden: %s", path)
            return None
        return path.as_uri()

    # =========================================================================
    # Sidebar: "running elements" (Inhalt) – Gestaltung steckt im @page-CSS
    # =========================================================================

    def _render_sidebar_content(
        self, sidebar_mode: str = "full", leitung_label: str = ""
    ) -> str:
        """
        Erzeugt die Sidebar-Inhalte als "running elements".

        Sie stehen im Fluss nicht sichtbar, werden aber von WeasyPrint in die
        linken Randboxen jeder Seite dieses Seitentyps gesetzt (siehe
        _sidebar_page_css) – also automatisch auch auf Folgeseiten.

        Args:
            sidebar_mode: 'full' (mit Rahmendaten) oder 'minimal' (nur Name)
            leitung_label: 'fe', 'se', oder '' für beide
        """
        group = self.group

        logo_html = ""
        if self.company_logo:
            logo_uri = self._file_uri(self.company_logo.logo_path)
            if logo_uri:
                logo_html = f'<img src="{logo_uri}" class="sb-logo-img" alt="Logo">'

        head = f"""<div class="sb-run-head">
            {logo_html}
            <div class="sb-title">Stärkenanalyse für</div>
            <div class="sb-participant-name">{escape(self.participant.name or "")}</div>
        </div>"""

        if sidebar_mode != "full":
            return head

        date_range = ""
        if group.date_from:
            date_range = group.date_from.strftime("%d.%m.%Y")
            if group.date_to:
                date_range += f' – {group.date_to.strftime("%d.%m.%Y")}'

        location = group.location or ""
        leitung_fe = getattr(group, "leitung_fremdeinschatzung", "") or ""
        leitung_se = getattr(group, "leitung_selbsteinschatzung", "") or ""
        beob1 = getattr(group, "beobachter1", "") or ""
        beob2 = getattr(group, "beobachter2", "") or ""

        lines = [f"<p><strong>Zeitraum:</strong> {escape(date_range) or '–'}</p>"]
        if location:
            lines.append(f"<p><strong>Ort:</strong> {escape(location)}</p>")

        if leitung_label in ("fe", "") and leitung_fe:
            lines.append(
                "<p><strong>Leitung Fremdeinschätzung:</strong> "
                f"{escape(leitung_fe)}</p>"
            )
        if leitung_label in ("se", "") and leitung_se:
            lines.append(
                "<p><strong>Leitung Selbsteinschätzung:</strong> "
                f"{escape(leitung_se)}</p>"
            )

        if beob1 or beob2:
            beobachter = ", ".join(escape(b) for b in (beob1, beob2) if b)
            lines.append(f"<p><strong>Beobachter:</strong> {beobachter}</p>")

        meta_class = {
            "fe": "sb-run-meta-fe",
            "se": "sb-run-meta-se",
        }.get(leitung_label, "sb-run-meta-all")
        meta = f"""<div class="sb-meta {meta_class}">
            <h2 class="sb-metadata-title">RAHMENDATEN</h2>
            {''.join(lines)}
        </div>"""
        return head + meta

    # =========================================================================
    # build_html() — mit mode-Parameter
    # =========================================================================

    def build_html(self, mode: str = "combined") -> str:
        """
        Erstellt das komplette HTML-Dokument.

        Args:
            mode: 'combined' (Gesamt-PDF), 'standalone_se', 'standalone_fe'
        """
        context = {
            "group": self.group,
            "participant": self.participant,
            "config": self.config,
            "modules_config": self.modules_config,
            "theme": self.theme,
            "company_logo": self.company_logo,
            "client_logo": self.client_logo,
            "observations": self.participant_observations,
            "sk_ratings": self.participant_ratings_sk,
            "vk_ratings": self.participant_ratings_vk,
            "ki_texts": self.participant_ki_texts,
            "self_assessment": self.self_assessment,
            "report_date": datetime.now(),
        }

        sidebar_mode = "minimal" if mode == "combined" else "full"
        self.expected_pages = {}

        modules_html = []

        if mode == "standalone_se":
            modules_html.append(self._render_self_assessment(context, "full"))

        elif mode == "standalone_fe":
            modules_html.append(self._render_external_assessment(context, "full"))

        else:
            # Gesamt-PDF: Alle aktivierten Module
            mc = self.modules_config

            if mc.get("cover_page", {}).get("enabled"):
                modules_html.append(self._render_cover_page(context))

            if mc.get("self_assessment", {}).get("enabled"):
                modules_html.append(
                    self._render_self_assessment(context, sidebar_mode)
                )

            if mc.get("external_assessment", {}).get("enabled"):
                modules_html.append(
                    self._render_external_assessment(context, sidebar_mode)
                )

            if mc.get("closing_page", {}).get("enabled"):
                modules_html.append(self._render_closing_page(context, sidebar_mode))

            if mc.get("info_page", {}).get("enabled"):
                modules_html.append(self._render_info_page(context))

        return render_template_string(
            self._get_base_template(),
            modules="\n".join(modules_html),
            css=self._generate_css(sidebar_mode),
            participant=self.participant,
        )

    # =========================================================================
    # Basis-Template
    # =========================================================================

    def _get_base_template(self) -> str:
        """
        WICHTIG: {{ css|safe }} und {{ modules|safe }} — ohne |safe escaped
        Jinja2 das HTML und CSS, was zu unlesbarer Ausgabe führt!
        """
        return """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Stärkenanalyse - {{ participant.name }}</title>
    <style>
        {{ css|safe }}
    </style>
</head>
<body>
    <div class="report-container">
        {{ modules|safe }}
    </div>
</body>
</html>"""

    # =========================================================================
    # CSS-Generierung
    # =========================================================================

    def _font_face_css(self) -> str:
        """Inter liegt lokal in static/fonts (kein Abruf bei Google beim Rendern)."""
        faces = []
        for weight in (400, 500, 600, 700):
            font_path = self.project_root / "static" / "fonts" / f"Inter-{weight}.ttf"
            if font_path.is_file():
                faces.append(
                    f"@font-face {{ font-family: 'Inter'; font-style: normal; "
                    f"font-weight: {weight}; src: url('{font_path.as_uri()}') "
                    f"format('truetype'); }}"
                )
        return "\n".join(faces)

    def _sidebar_background_uri(self) -> str:
        """Seitenhintergrund: Sidebar mit Farbverlauf links, Inhaltsfläche rechts."""
        w, h = PAGE_WIDTH_MM, PAGE_HEIGHT_MM
        sb = SIDEBAR_WIDTH_MM
        footer_line_y = h - MARGIN_BOTTOM_MM
        pad = SIDEBAR_PADDING_MM
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">
<defs>
<linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{self.primary}"/><stop offset="1" stop-color="{self.primary_light}"/>
</linearGradient>
<clipPath id="c"><rect width="{sb}" height="{h}"/></clipPath>
</defs>
<rect width="{w}" height="{h}" fill="#fafbfc"/>
<rect width="{sb}" height="{h}" fill="url(#g)"/>
<circle cx="{sb - 8}" cy="14" r="26" fill="#ffffff" fill-opacity="0.06" clip-path="url(#c)"/>
<line x1="{pad}" y1="{footer_line_y}" x2="{sb - pad}" y2="{footer_line_y}" stroke="#ffffff" stroke-opacity="0.25" stroke-width="0.3"/>
</svg>"""
        return _svg_data_uri(svg)

    def _cover_background_uri(self) -> str:
        w, h = PAGE_WIDTH_MM, PAGE_HEIGHT_MM
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="0 0 {w} {h}">
<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{self.primary}"/><stop offset="1" stop-color="{self.primary_light}"/>
</linearGradient>
<clipPath id="c"><rect width="{w}" height="{h}"/></clipPath>
</defs>
<rect width="{w}" height="{h}" fill="url(#g)"/>
<g clip-path="url(#c)">
<circle cx="{w - 10}" cy="30" r="55" fill="#ffffff" fill-opacity="0.10"/>
<circle cx="15" cy="{h - 25}" r="48" fill="#ffffff" fill-opacity="0.08"/>
</g>
</svg>"""
        return _svg_data_uri(svg)

    def _sidebar_page_css(self, sidebar_mode: str) -> str:
        """@page-Regeln für alle Seitentypen mit Sidebar."""
        bg = self._sidebar_background_uri()
        pad = SIDEBAR_PADDING_MM
        rules = []
        for page_name, title, meta_name in SIDEBAR_PAGES.values():
            meta_box = ""
            if sidebar_mode == "full":
                meta_box = f"""
            @left-bottom {{
                content: element({meta_name});
                vertical-align: bottom;
                padding: 0 {pad}mm 4mm {pad}mm;
            }}"""
            rules.append(
                f"""
        @page {page_name} {{
            size: A4;
            margin: {MARGIN_TOP_MM}mm {MARGIN_RIGHT_MM}mm {MARGIN_BOTTOM_MM}mm {SIDEBAR_WIDTH_MM}mm;
            background-image: url("{bg}");
            background-repeat: no-repeat;
            background-size: {PAGE_WIDTH_MM}mm {PAGE_HEIGHT_MM}mm;
            background-position: 0 0;
            background-attachment: fixed;

            @top-center {{
                content: "{title}";
                font-family: {self.font_family};
                font-size: 10.5pt;
                font-weight: 500;
                letter-spacing: 0.3px;
                color: #718096;
                padding-left: {CONTENT_GUTTER_MM}mm;
                vertical-align: middle;
            }}
            @left-top {{
                content: element(sbHead);
                vertical-align: top;
                padding: 0 {pad}mm;
            }}{meta_box}
            @bottom-left-corner {{
                content: "Seite " counter(page) " von " counter(pages);
                font-family: {self.font_family};
                font-size: 8.5pt;
                color: rgba(255, 255, 255, 0.78);
                text-align: left;
                vertical-align: middle;
                padding-left: {pad}mm;
            }}
        }}"""
            )
        return "\n".join(rules)

    def _generate_css(self, sidebar_mode: str = "full") -> str:
        """
        CSS für Report-Templates (WeasyPrint, CSS Paged Media).

        Seitenaufbau steckt in @page (Sidebar, Kopfzeile, Seitenzahl); der Inhalt
        fließt als normaler Block und darf beliebig viele Seiten füllen.
        """
        primary = self.primary
        secondary = self.secondary
        font_family = self.font_family
        font_size = (
            self.theme.get("font_size_base")
            if re.match(r"^\d+(\.\d+)?(pt|px)$", str(self.theme.get("font_size_base")))
            else "11pt"
        )

        pad = SIDEBAR_PADDING_MM

        return f"""
        {self._font_face_css()}

        /* ========================================
           RESET & FOUNDATIONS
           ======================================== */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: {font_family};
            font-size: {font_size};
            line-height: 1.65;
            color: #2d3748;
        }}

        @page {{
            size: A4;
            margin: 0;
            font-family: {font_family};
        }}

        /* ========================================
           SEITENTYPEN
           ======================================== */
        @page cover {{
            size: A4;
            margin: 0;
            background-image: url("{self._cover_background_uri()}");
            background-repeat: no-repeat;
            background-size: {PAGE_WIDTH_MM}mm {PAGE_HEIGHT_MM}mm;
            background-position: 0 0;
            background-attachment: fixed;
        }}

        @page info {{
            size: A4;
            margin: 22mm 24mm;
        }}

        {self._sidebar_page_css(sidebar_mode)}

        /* ========================================
           SIDEBAR-INHALTE (running elements)
           ======================================== */
        .sb-run-head {{ position: running(sbHead); }}
        .sb-run-meta-fe {{ position: running(sbMetaFe); }}
        .sb-run-meta-se {{ position: running(sbMetaSe); }}
        .sb-run-meta-all {{ position: running(sbMetaAll); }}

        .sb-run-head, .sb-meta {{
            color: #ffffff;
            font-family: {font_family};
        }}

        .sb-logo-img {{
            display: block;
            max-width: 32mm;
            max-height: 20mm;
            margin-bottom: 7mm;
            border-radius: 1mm;
        }}

        .sb-title {{
            font-size: 9pt;
            line-height: 1.4;
            font-weight: 400;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 1.5mm;
        }}

        .sb-participant-name {{
            font-size: 12pt;
            font-weight: 700;
            text-transform: uppercase;
            line-height: 1.3;
            overflow-wrap: break-word;
        }}

        .sb-meta {{
            font-size: 8.5pt;
            line-height: 1.55;
        }}

        .sb-metadata-title {{
            font-size: 8pt;
            font-weight: 700;
            letter-spacing: 1.1px;
            opacity: 0.85;
            margin-bottom: 3mm;
            text-transform: uppercase;
        }}

        .sb-meta p {{
            margin-bottom: 1.6mm;
            text-align: left;
            opacity: 0.95;
            overflow-wrap: break-word;
        }}

        /* ========================================
           INHALT NEBEN DER SIDEBAR
           ======================================== */
        .sb-flow {{
            margin-left: {CONTENT_GUTTER_MM}mm;
        }}
        .sb-flow.page-se {{ page: sb-se; }}
        .sb-flow.page-fe {{ page: sb-fe; }}
        .sb-flow.page-closing {{ page: sb-closing; }}

        .sb-flow > .sb-pagebreak {{ break-before: page; }}

        .sb-section {{ margin-bottom: 8mm; }}

        .sb-title-wrap {{
            margin-bottom: 4mm;
            break-after: avoid;
        }}

        .sb-section-title {{
            display: inline-block;
            font-family: {font_family};
            font-size: 13pt;
            font-weight: 700;
            color: {primary};
            padding-bottom: 2mm;
            border-bottom: 0.6mm solid {primary};
            break-after: avoid;
        }}

        .sb-text-content {{
            font-size: 10.5pt;
            line-height: 1.7;
            text-align: justify;
            hyphens: auto;
            color: #4a5568;
            orphans: 3;
            widows: 3;
        }}

        .sb-text-content p {{ margin-bottom: 3mm; }}
        .sb-text-content p:last-child {{ margin-bottom: 0; }}
        .sb-text-content ul, .sb-text-content ol {{
            margin: 0 0 3mm 5mm;
            text-align: left;
        }}
        .sb-text-content h1, .sb-text-content h2, .sb-text-content h3 {{
            font-size: 11.5pt;
            color: {primary};
            margin: 4mm 0 2mm 0;
            break-after: avoid;
        }}
        .sb-text-content em {{ font-style: italic; }}

        .sb-meta-line {{
            font-size: 9pt;
            color: #888;
            margin-bottom: 4mm;
        }}

        .sb-chart-container {{
            width: 104mm;
            margin: 9mm auto 0 auto;
            text-align: center;
            break-inside: avoid;
        }}

        .sb-chart-container img {{
            display: block;
            width: 100%;
            height: auto;
        }}

        .sb-callout {{
            background: #ffffff;
            border-left: 1.2mm solid {primary};
            border-radius: 1.5mm;
            padding: 6mm 7mm;
        }}

        .sb-empty {{ color: #718096; font-style: italic; }}

        /* ========================================
           COVER PAGE (Full-Width, No Sidebar)
           ======================================== */
        .cover-page {{
            page: cover;
            height: 296mm;
            padding: 45mm 35mm;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            color: white;
        }}

        .cover-page .logo {{
            max-width: 180pt;
            max-height: 90pt;
            margin: 0 0 30pt 0;
            border-radius: 4px;
        }}

        .cover-page h1 {{
            color: white;
            font-size: 38pt;
            margin: 25pt 0 15pt 0;
            font-weight: 700;
            letter-spacing: -0.5px;
            line-height: 1.2;
        }}

        .cover-page .cover-subtitle {{
            font-size: 16pt;
            color: rgba(255,255,255,0.95);
            margin: 15pt 0 40pt 0;
            font-weight: 400;
        }}

        .cover-page .cover-meta {{
            font-size: 12pt;
            color: rgba(255,255,255,0.85);
            margin: 30pt 0 0 0;
            line-height: 1.8;
        }}

        /* ========================================
           INFO BOXES
           ======================================== */
        .info-box {{
            background: white;
            border-left: 4px solid {primary};
            padding: 16pt 16pt 16pt 18pt;
            margin: 14pt 0;
            border-radius: 3px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            break-inside: avoid;
        }}

        .info-box h3 {{
            color: {primary};
            font-size: 11pt;
            margin-bottom: 8pt;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .info-box p {{
            font-size: 10pt;
            line-height: 1.6;
            color: #4a5568;
            margin-bottom: 6pt;
        }}

        /* ========================================
           INFO PAGE (Hinweisblatt, ohne Sidebar)
           ======================================== */
        .info-page {{ page: info; }}

        .info-page h2 {{
            color: {primary};
            font-size: 18pt;
            margin-bottom: 25pt;
            border-bottom: 2px solid {primary};
            padding-bottom: 12pt;
            font-weight: 700;
            break-after: avoid;
        }}

        .info-page h3 {{
            color: {primary};
            font-size: 13pt;
            margin-top: 18pt;
            margin-bottom: 10pt;
            font-weight: 700;
        }}

        .info-page p {{
            font-size: 10.5pt;
            line-height: 1.7;
            color: #4a5568;
            text-align: justify;
            hyphens: auto;
            margin-bottom: 10pt;
        }}

        /* ========================================
           SIGNATURES
           ======================================== */
        .signature-block {{
            margin-top: 45pt;
            display: flex;
            justify-content: space-between;
            gap: 20pt;
            break-inside: avoid;
        }}

        .signature-item {{
            flex: 1;
            text-align: center;
        }}

        .signature-item img {{
            max-width: 150px;
            max-height: 60px;
            margin-bottom: 8pt;
            border-radius: 2px;
        }}

        .signature-line {{
            border-bottom: 1.5pt solid #2d3748;
            width: 100%;
            margin-bottom: 6pt;
            padding-top: 30pt;
        }}

        .signature-name {{
            font-size: 10pt;
            font-weight: 600;
            color: #2d3748;
            margin-top: 6pt;
        }}

        /* ========================================
           TABLES
           ======================================== */
        .rating-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 14pt 0;
            font-size: 10pt;
            background: white;
        }}

        .rating-table th, .rating-table td {{
            border: 1pt solid #e2e8f0;
            padding: 10pt;
            text-align: left;
        }}

        .rating-table th {{
            background: {secondary};
            color: {primary};
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 9pt;
        }}

        .rating-table td {{ color: #4a5568; }}
        .rating-table tbody tr:nth-child(even) {{ background: #f7fafc; }}
        """

    # =========================================================================
    # Radar-Chart Helper
    # =========================================================================

    def _create_radar_chart(self, ratings_dict, keys, labels, color):
        """Erzeugt ein Radardiagramm und gibt es als Base64-Data-URI zurück."""
        values = [ratings_dict.get(key, 0) for key in keys]
        num_vars = len(labels)
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        values_plot = values + values[:1]
        angles_plot = angles + angles[:1]

        fig, ax = plt.subplots(figsize=(5, 5), subplot_kw={"polar": True})
        ax.fill(angles_plot, values_plot, color=color, alpha=0.2)
        ax.plot(angles_plot, values_plot, color=color, linewidth=2)
        ax.grid(color="#E0E0E0", linestyle="-", linewidth=0.7)
        ax.spines["polar"].set_edgecolor("#E0E0EE")
        ax.set_yticklabels([])
        ax.set_rlim(0, 10)
        ax.set_xticks(angles)
        ax.set_xticklabels(labels, size=11, fontfamily="sans-serif")
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.tick_params(axis="x", pad=12)

        buf = BytesIO()
        plt.savefig(
            buf,
            format="png",
            dpi=200,
            bbox_inches="tight",
            transparent=True,
            pad_inches=0.2,
        )
        plt.close(fig)
        buf.seek(0)

        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/png;base64,{img_base64}"

    # =========================================================================
    # Modul-Renderer
    # =========================================================================

    def _sidebar_section(
        self,
        kind: str,
        body: str,
        sidebar_mode: str,
        expected_pages: int,
    ) -> str:
        """
        Umhüllt den Inhalt eines Moduls mit Sidebar-Seitentyp und Sidebar-Inhalten.

        kind: 'se', 'fe' oder 'closing' (siehe SIDEBAR_PAGES)
        """
        page_name = SIDEBAR_PAGES[kind][0]
        leitung_label = {"se": "se", "fe": "fe"}.get(kind, "")
        self.expected_pages[page_name] = (
            self.expected_pages.get(page_name, 0) + expected_pages
        )
        sidebar = self._render_sidebar_content(sidebar_mode, leitung_label)
        return f"""<div class="sb-flow page-{kind}">
            {sidebar}
            {body}
        </div>"""

    @staticmethod
    def _section(title: str, content_html: str, extra_class: str = "") -> str:
        return f"""<section class="sb-section {extra_class}">
            <div class="sb-title-wrap"><h3 class="sb-section-title">{escape(title)}</h3></div>
            {content_html}
        </section>"""

    def _render_cover_page(self, context) -> str:
        """Rendert das Deckblatt (eigenständiges Layout, ohne Sidebar)."""
        config = context["modules_config"].get("cover_page", {})
        self.expected_pages["cover"] = 1

        html_parts = ['<div class="cover-page">']

        if config.get("show_company_logo") and self.company_logo:
            logo_uri = self._file_uri(self.company_logo.logo_path)
            if logo_uri:
                html_parts.append(f'<img src="{logo_uri}" class="logo" alt="Firmenlogo">')

        if config.get("show_client_logo") and self.client_logo:
            logo_uri = self._file_uri(self.client_logo.logo_path)
            if logo_uri:
                html_parts.append(
                    f'<img src="{logo_uri}" class="logo" alt="Auftraggeber-Logo">'
                )

        if config.get("show_title"):
            html_parts.append(
                f'<h1>{escape(config.get("title", "Stärkenanalyse"))}</h1>'
            )

        if config.get("show_participant_name"):
            html_parts.append(
                f'<p class="cover-meta" style="font-size: 16pt;">'
                f'<strong>{escape(context["participant"].name or "")}</strong></p>'
            )

        if config.get("show_group_name"):
            html_parts.append(
                f'<p class="cover-meta"><strong>Gruppe:</strong> '
                f'{escape(context["group"].name or "")}</p>'
            )

        if config.get("show_date"):
            html_parts.append(
                f'<p class="cover-meta"><strong>Datum:</strong> '
                f'{context["report_date"].strftime("%d.%m.%Y")}</p>'
            )

        if config.get("subtitle"):
            html_parts.append(
                f'<p class="cover-subtitle">{escape(config.get("subtitle", ""))}</p>'
            )

        html_parts.append("</div>")
        return "\n".join(html_parts)

    def _render_self_assessment(self, context, sidebar_mode: str = "minimal") -> str:
        """Rendert die Selbsteinschätzung (Sidebar-Seitentyp 'sb-se')."""
        sa = context["self_assessment"]

        if not sa:
            body = '<p class="sb-empty">Keine Selbsteinschätzung vorhanden</p>'
        else:
            body = f"""<section class="sb-section">
                <p class="sb-meta-line">Geführt am: {sa.created_at.strftime("%d.%m.%Y")}</p>
                <div class="sb-text-content">{_rich_text(sa.content)}</div>
            </section>"""

        return self._sidebar_section("se", body, sidebar_mode, expected_pages=1)

    def _render_external_assessment(
        self, context, sidebar_mode: str = "minimal"
    ) -> str:
        """
        Rendert die Fremdeinschätzung. Jeder Abschnitt beginnt auf einer neuen Seite:
        Seite 1: Soziale Kompetenzen + Radardiagramm
        Seite 2: Verbale Kompetenzen + Radardiagramm
        Seite 3: Zusammenfassung (nur wenn vorhanden)
        Ist ein Text länger als eine Seite, läuft er auf eine Folgeseite weiter
        (Sidebar und Seitenzahl wiederholen sich).
        """
        ki_texts = context["ki_texts"]

        if not ki_texts or not any(
            [ki_texts.get("social_text"), ki_texts.get("verbal_text")]
        ):
            body = '<p class="sb-empty">Keine Fremdeinschätzung vorhanden</p>'
            return self._sidebar_section("fe", body, sidebar_mode, expected_pages=1)

        primary = self.primary
        sk_ratings = context["sk_ratings"]
        vk_ratings = context["vk_ratings"]

        sk_chart = self._create_radar_chart(
            sk_ratings,
            [
                "flexibility",
                "team_orientation",
                "process_orientation",
                "results_orientation",
            ],
            [
                "Flexibilität",
                "Team-\norientierung",
                "Prozess-\norientierung",
                "Ergebnis-\norientierung",
            ],
            primary,
        )
        vk_chart = self._create_radar_chart(
            vk_ratings,
            ["flexibility", "consulting", "objectivity", "goal_orientation"],
            ["Flexibilität", "Beratung", "Sachlichkeit", "Ziel-\norientierung"],
            primary,
        )

        social = self._section(
            "Soziale Kompetenzen",
            f"""<div class="sb-text-content">{_rich_text(ki_texts.get("social_text"))}</div>
            <div class="sb-chart-container">
                <img src="{sk_chart}" alt="Radardiagramm Soziale Kompetenzen">
            </div>""",
        )
        verbal = self._section(
            "Verbale Kompetenzen",
            f"""<div class="sb-text-content">{_rich_text(ki_texts.get("verbal_text"))}</div>
            <div class="sb-chart-container">
                <img src="{vk_chart}" alt="Radardiagramm Verbale Kompetenzen">
            </div>""",
            extra_class="sb-pagebreak",
        )
        sections = [social, verbal]

        if ki_texts.get("summary_text"):
            sections.append(
                self._section(
                    "Zusammenfassung",
                    f"""<div class="sb-callout">
                        <div class="sb-text-content">{_rich_text(ki_texts.get("summary_text"))}</div>
                    </div>""",
                    extra_class="sb-pagebreak",
                )
            )

        return self._sidebar_section(
            "fe", "\n".join(sections), sidebar_mode, expected_pages=len(sections)
        )

    def _render_closing_page(self, context, sidebar_mode: str = "minimal") -> str:
        """Rendert das Abschlussblatt mit Unterschriften (Sidebar-Seitentyp)."""
        config = context["modules_config"].get("closing_page", {})

        additional_html = ""
        if config.get("additional_text"):
            additional_html = (
                f'<div class="info-box">{_rich_text(config["additional_text"])}</div>'
            )

        leitung_fe = getattr(self.group, "leitung_fremdeinschatzung", "") or ""
        leitung_se = getattr(self.group, "leitung_selbsteinschatzung", "") or ""

        sig_fe_img = ""
        if self.signature_fe:
            sig_uri = self._file_uri(self.signature_fe.image_path)
            if sig_uri:
                sig_fe_img = (
                    f'<img src="{sig_uri}" alt="Unterschrift Leitung Fremdeinschätzung">'
                )

        sig_se_img = ""
        if self.signature_se:
            sig_uri = self._file_uri(self.signature_se.image_path)
            if sig_uri:
                sig_se_img = (
                    f'<img src="{sig_uri}" alt="Unterschrift Leitung Selbsteinschätzung">'
                )

        body = f"""{additional_html}
        <div class="signature-block" style="margin-top: 60pt;">
            <div class="signature-item">
                {sig_fe_img}
                <div class="signature-line">Leitung Fremdeinschätzung</div>
                <div class="signature-name">{escape(leitung_fe)}</div>
            </div>
            <div class="signature-item">
                {sig_se_img}
                <div class="signature-line">Leitung Selbsteinschätzung</div>
                <div class="signature-name">{escape(leitung_se)}</div>
            </div>
        </div>"""

        return self._sidebar_section("closing", body, sidebar_mode, expected_pages=1)

    def _render_info_page(self, context) -> str:
        """Rendert das Hinweisblatt (eigenständig, OHNE Sidebar, darf mehrseitig sein)."""
        if not self.explanation_blocks:
            return """<div class="info-page">
                <h2>Hinweise und Informationen</h2>
                <div class="info-box">
                    <em>Keine Erklärungstexte ausgewählt.</em>
                </div>
            </div>"""

        blocks_html = []
        for block in self.explanation_blocks:
            blocks_html.append(
                f"""<div class="info-box">
                <h3>{escape(block.title or "")}</h3>
                <div>{_rich_text(block.content)}</div>
            </div>"""
            )

        return f"""<div class="info-page">
            <h2>Hinweise und Informationen</h2>
            {''.join(blocks_html)}
        </div>"""

    # =========================================================================
    # PDF-Export
    # =========================================================================

    def _check_page_counts(self, document) -> list:
        """
        Vergleicht die tatsächliche Seitenzahl je Modul mit der vorgesehenen.

        Läuft ein Text auf Folgeseiten über, ist das Ergebnis weiterhin
        vollständig und korrekt – aber das vorgesehene Layout ist verlassen.
        """
        counts = Counter()
        for page in document.pages:
            page_box = getattr(page, "_page_box", None)
            page_type = getattr(page_box, "page_type", None)
            counts[getattr(page_type, "name", None)] += 1

        warnings = []
        for page_name, expected in self.expected_pages.items():
            actual = counts.get(page_name, 0)
            if actual > expected:
                label = PAGE_LABELS.get(page_name, page_name)
                warnings.append(
                    f"{label}: {actual} statt {expected} Seiten – "
                    "der Text ist länger als vorgesehen."
                )
        return warnings

    def render_document(self, mode: str = "combined"):
        """Rendert das Layout mit WeasyPrint und prüft die Seitenzahlen."""
        # Lazy-load WeasyPrint um App-Startup nicht zu blockieren
        try:
            from weasyprint import HTML
        except Exception as e:
            raise RuntimeError(
                f"WeasyPrint konnte nicht geladen werden. "
                f"Bitte installieren Sie die erforderlichen System-Bibliotheken (Pango, Cairo). "
                f"Details: {e}"
            ) from e

        html_string = self.build_html(mode=mode)
        document = HTML(string=html_string, base_url=str(self.project_root)).render()

        self.render_warnings = self._check_page_counts(document)
        for warning in self.render_warnings:
            logger.warning(
                "Bericht für %s (Modus %s): %s", self.participant.name, mode, warning
            )
        return document

    def to_pdf(self, mode: str = "combined") -> bytes:
        """Konvertiert HTML zu PDF."""
        return self.render_document(mode=mode).write_pdf()

    def to_file(self, filepath: str, mode: str = "combined") -> str:
        """Speichert das PDF in eine Datei."""
        pdf_bytes = self.to_pdf(mode=mode)
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        return filepath
