"""
ReportGenerator Service - HTML-Rendering und PDF-Generierung für Abschlussberichte.

Architektur:
- build_html(mode): Orchestriert alle Module, mode steuert Sidebar-Inhalt
  - 'combined': Gesamt-PDF (Sidebar minimal, ohne Metadaten)
  - 'standalone_se': Nur Selbsteinschätzung (Sidebar voll)
  - 'standalone_fe': Nur Fremdeinschätzung (Sidebar voll)
- _render_sidebar(): Shared Sidebar-Komponente mit zwei Modi
- _render_*(): Rendert einzelne Module
- _generate_css(): Theme-CSS + Sidebar-CSS + Screen-/Print-CSS
- to_pdf(mode): Konvertiert HTML zu PDF
"""

import base64
import json
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from flask import render_template_string
from weasyprint import CSS, HTML

from models import (ClientLogo, CompanyLogo, ExplanationBlock, Group,
                    Participant, ReportConfiguration, ReportTemplate,
                    SelfAssessment)


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

    # =========================================================================
    # Seitenzählung
    # =========================================================================

    def _count_pages(self, mode: str = "combined") -> int:
        """Berechnet die Gesamtseitenzahl basierend auf Modus und aktiven Modulen."""
        if mode == "standalone_se":
            return 1
        if mode == "standalone_fe":
            return 2

        total = 0
        mc = self.modules_config
        if mc.get("cover_page", {}).get("enabled"):
            total += 1
        if mc.get("self_assessment", {}).get("enabled") and self.self_assessment:
            total += 1
        if (
            mc.get("external_assessment", {}).get("enabled")
            and self.participant_ki_texts
        ):
            total += 2  # FE ist immer 2 Seiten
        if mc.get("closing_page", {}).get("enabled"):
            total += 1
        if mc.get("info_page", {}).get("enabled"):
            total += 1
        return max(total, 1)

    # =========================================================================
    # Shared Sidebar-Komponente
    # =========================================================================

    def _render_sidebar(
        self,
        page_num: int,
        total_pages: int,
        sidebar_mode: str = "full",
        leitung_label: str = "",
    ) -> str:
        """
        Rendert die Sidebar (linker Seitenstreifen).

        Args:
            page_num: Aktuelle Seitennummer
            total_pages: Gesamtseitenzahl
            sidebar_mode: 'full' (mit Metadaten) oder 'minimal' (nur Design)
            leitung_label: 'fe', 'se', oder '' für beide
        """
        primary = self.theme.get("primary_color", "#5A7D7C")
        group = self.group

        # Logo
        logo_html = '<div class="sb-logo">🔍</div>'
        if self.company_logo:
            logo_path = (
                (self.project_root / self.company_logo.logo_path).resolve().as_uri()
            )
            logo_html = f'<img src="{logo_path}" class="sb-logo-img" alt="Logo">'

        # Teilnehmername
        name_html = f"""<h1 class="sb-title">Stärkenanalyse für<br>
            <span class="sb-participant-name">{self.participant.name}</span>
        </h1>"""

        # Metadaten (nur im 'full'-Modus)
        metadata_html = ""
        if sidebar_mode == "full":
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

            metadata_lines = [f'<p><strong>Zeitraum:</strong> {date_range or "–"}</p>']
            if location:
                metadata_lines.append(f"<p><strong>Ort:</strong> {location}</p>")

            if leitung_label == "fe" and leitung_fe:
                metadata_lines.append(
                    f"<p><strong>Leitung FE:</strong> {leitung_fe}</p>"
                )
            elif leitung_label == "se" and leitung_se:
                metadata_lines.append(
                    f"<p><strong>Leitung SE:</strong> {leitung_se}</p>"
                )
            else:
                if leitung_fe:
                    metadata_lines.append(
                        f"<p><strong>Leitung FE:</strong> {leitung_fe}</p>"
                    )
                if leitung_se:
                    metadata_lines.append(
                        f"<p><strong>Leitung SE:</strong> {leitung_se}</p>"
                    )

            if beob1 or beob2:
                beobachter_str = beob1
                if beob2:
                    beobachter_str += f", {beob2}"
                metadata_lines.append(
                    f"<p><strong>Beobachter:</strong> {beobachter_str}</p>"
                )

            metadata_html = f"""<div class="sb-metadata">
                <h2 class="sb-metadata-title">RAHMENDATEN</h2>
                {''.join(metadata_lines)}
            </div>"""

        return f"""<aside class="sb-sidebar" style="background-color: {primary};">
            <div class="sb-header">
                {logo_html}
                {name_html}
            </div>
            <div class="sb-spacer"></div>
            {metadata_html}
            <div class="sb-footer"><p>Seite {page_num} von {total_pages}</p></div>
        </aside>"""

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

        total_pages = self._count_pages(mode)
        sidebar_mode = "minimal" if mode == "combined" else "full"

        modules_html = []
        current_page = 0

        if mode == "standalone_se":
            current_page += 1
            modules_html.append(
                self._render_self_assessment(
                    context, current_page, total_pages, sidebar_mode="full"
                )
            )

        elif mode == "standalone_fe":
            pages = self._render_external_assessment(
                context, 1, total_pages, sidebar_mode="full"
            )
            modules_html.append(pages)

        else:
            # Gesamt-PDF: Alle aktivierten Module
            mc = self.modules_config

            if mc.get("cover_page", {}).get("enabled"):
                current_page += 1
                modules_html.append(self._render_cover_page(context))

            if mc.get("self_assessment", {}).get("enabled"):
                current_page += 1
                modules_html.append(
                    self._render_self_assessment(
                        context, current_page, total_pages, sidebar_mode=sidebar_mode
                    )
                )

            if mc.get("external_assessment", {}).get("enabled"):
                current_page += 1
                pages = self._render_external_assessment(
                    context, current_page, total_pages, sidebar_mode=sidebar_mode
                )
                modules_html.append(pages)
                current_page += 1  # FE hat 2 Seiten

            if mc.get("closing_page", {}).get("enabled"):
                current_page += 1
                modules_html.append(
                    self._render_closing_page(
                        context, current_page, total_pages, sidebar_mode=sidebar_mode
                    )
                )

            if mc.get("info_page", {}).get("enabled"):
                current_page += 1
                modules_html.append(self._render_info_page(context))

        base_html = render_template_string(
            self._get_base_template(),
            modules="\n".join(modules_html),
            theme=self.theme,
            css=self._generate_css(),
            participant=self.participant,
        )

        return base_html

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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Stärkenanalyse - {{ participant.name }}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Montserrat:wght@400;700&family=Source+Serif+Pro:wght@400;700&display=swap" rel="stylesheet">
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

    def _generate_css(self) -> str:
        primary = self.theme.get("primary_color", "#5A7D7C")
        secondary = self.theme.get("secondary_color", "#F0F5FF")
        accent = self.theme.get("accent_color", "#FF6B6B")
        font_family = self.theme.get("font_family", "'Inter', sans-serif")
        font_size = self.theme.get("font_size_base", "11pt")

        return f"""
        /* === Reset === */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: {font_family};
            font-size: {font_size};
            line-height: 1.6;
            color: #333;
            background: #fff;
        }}

        @page {{
            size: A4;
            margin: 0;
        }}

        .report-container {{ width: 100%; }}

        /* === Sidebar-Layout (Shared für SE, FE, Abschluss) === */
        .sb-page {{
            display: flex;
            width: 210mm;
            min-height: 297mm;
            overflow: hidden;
            page-break-after: always;
            box-sizing: border-box;
        }}
        .sb-page:last-child {{ page-break-after: avoid; }}

        .sb-sidebar {{
            width: 30%;
            color: white;
            padding: 25px;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            font-family: 'Montserrat', 'Inter', sans-serif;
            font-size: 10pt;
        }}
        .sb-header {{ flex-shrink: 0; }}
        .sb-spacer {{ flex-grow: 1; }}
        .sb-logo {{ font-size: 2.5em; font-weight: 700; margin-bottom: 30px; }}
        .sb-logo-img {{ max-width: 120px; max-height: 80px; margin-bottom: 30px; }}
        .sb-title {{ font-size: 1.2em; line-height: 1.3; font-weight: 400; }}
        .sb-participant-name {{ font-size: 1.2em; font-weight: 700; display: block; margin-top: 5px; word-wrap: break-word; }}
        .sb-metadata {{ flex-shrink: 0; margin-bottom: 20px; font-size: 0.85em; line-height: 1.8; }}
        .sb-metadata-title {{ font-weight: 700; letter-spacing: 1px; opacity: 0.8; margin-bottom: 10px; font-size: 1em; }}
        .sb-metadata p {{ margin-bottom: 2px; text-align: left; }}
        .sb-footer {{ flex-shrink: 0; opacity: 0.7; font-size: 0.85em; }}
        .sb-footer p {{ text-align: left; }}

        .sb-main {{
            width: 70%;
            padding: 35px;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
        }}
        .sb-main-spacer {{ flex-grow: 1; }}

        /* === Inhalts-Styles innerhalb sb-main === */
        .sb-subtitle {{
            font-family: 'Montserrat', 'Inter', sans-serif;
            color: #888;
            margin-bottom: 25px;
            text-align: center;
            font-size: 1.1em;
        }}
        .sb-section {{ margin-bottom: 25px; }}
        .sb-section-title {{
            font-family: 'Montserrat', 'Inter', sans-serif;
            font-size: 1.3em;
            font-weight: 700;
            color: {primary};
            margin-bottom: 12px;
        }}
        .sb-text-content {{
            font-size: 10.5pt;
            line-height: 1.7;
            text-align: justify;
        }}
        .sb-chart-container {{
            width: 100%;
            max-width: 320px;
            margin: 20px auto 0 auto;
            text-align: center;
        }}
        .sb-chart-container img {{ max-width: 100%; height: auto; }}

        /* === Deckblatt (eigenständig, ohne Sidebar) === */
        .page {{
            page-break-after: always;
            min-height: 297mm;
            width: 210mm;
            box-sizing: border-box;
        }}
        .page:last-child {{ page-break-after: avoid; }}

        .cover-page {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 40mm 30mm;
        }}
        .cover-page .logo {{ max-width: 200pt; max-height: 100pt; margin: 20pt 0; }}
        .cover-page h1 {{
            color: {primary};
            font-size: 36pt;
            margin: 30pt 0 15pt 0;
            border-bottom: 3pt solid {primary};
            padding-bottom: 15pt;
        }}
        .cover-page .cover-subtitle {{
            font-size: 18pt;
            color: {accent};
            margin: 15pt 0;
        }}
        .cover-page .cover-meta {{
            font-size: 13pt;
            color: #555;
            margin: 8pt 0;
        }}

        /* === Info-Boxen === */
        .info-box {{
            background: {secondary};
            border-left: 4pt solid {primary};
            padding: 15pt;
            margin: 12pt 0;
            border-radius: 3pt;
        }}
        .info-box h3 {{
            color: {primary};
            font-size: 12pt;
            margin-bottom: 8pt;
        }}

        /* === Hinweisblatt (eigenständig, ohne Sidebar) === */
        .info-page {{
            padding: 30mm;
        }}
        .info-page h2 {{
            color: {primary};
            font-size: 18pt;
            margin-bottom: 20pt;
            border-bottom: 2pt solid {primary};
            padding-bottom: 8pt;
        }}

        /* === Unterschriften === */
        .signature-block {{
            margin-top: 40pt;
        }}
        .signature-item {{
            display: inline-block;
            width: 45%;
            margin: 20pt 2%;
            text-align: center;
            vertical-align: top;
        }}
        .signature-item img {{
            max-width: 150px;
            max-height: 60px;
            margin-bottom: 5pt;
        }}
        .signature-line {{
            border-bottom: 1pt solid #000;
            width: 100%;
            margin-top: 10pt;
            padding-top: 5pt;
            text-align: center;
            font-size: 9pt;
            color: #555;
        }}
        .signature-name {{
            font-size: 10pt;
            font-weight: 600;
            margin-top: 5pt;
            color: #333;
        }}

        /* === Ratings-Tabelle === */
        .rating-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 12pt 0;
            font-size: 10pt;
        }}
        .rating-table th, .rating-table td {{
            border: 1pt solid #ddd;
            padding: 8pt;
            text-align: left;
        }}
        .rating-table th {{
            background: {secondary};
            color: {primary};
            font-weight: bold;
        }}

        /* === Screen: Jede Seite als visuelles A4-Blatt === */
        @media screen {{
            body {{ background: #e0e0e0; }}
            .report-container {{
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 20px 0;
                gap: 30px;
            }}
            .sb-page, .page {{
                background: #fff;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }}
        }}

        /* === Print/PDF: Kein visueller Chrome === */
        @media print {{
            body {{ background: #fff; }}
            .sb-page, .page {{ box-shadow: none; margin: 0; }}
        }}
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
            buf, format="png", bbox_inches="tight", transparent=True, pad_inches=0.2
        )
        plt.close(fig)
        buf.seek(0)

        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/png;base64,{img_base64}"

    # =========================================================================
    # Modul-Renderer
    # =========================================================================

    def _render_cover_page(self, context) -> str:
        """Rendert das Deckblatt (eigenständiges Layout, ohne Sidebar)."""
        config = context["modules_config"].get("cover_page", {})

        html_parts = ['<div class="page cover-page">']

        if config.get("show_company_logo") and self.company_logo:
            logo_path = (
                (self.project_root / self.company_logo.logo_path).resolve().as_uri()
            )
            html_parts.append(f'<img src="{logo_path}" class="logo" alt="Firmenlogo">')

        if config.get("show_client_logo") and self.client_logo:
            logo_path = (
                (self.project_root / self.client_logo.logo_path).resolve().as_uri()
            )
            html_parts.append(
                f'<img src="{logo_path}" class="logo" alt="Auftraggeber-Logo">'
            )

        if config.get("show_title"):
            html_parts.append(f'<h1>{config.get("title", "Stärkenanalyse")}</h1>')

        if config.get("show_participant_name"):
            html_parts.append(
                f'<p class="cover-meta" style="font-size: 16pt;">'
                f'<strong>{context["participant"].name}</strong></p>'
            )

        if config.get("show_group_name"):
            html_parts.append(
                f'<p class="cover-meta"><strong>Gruppe:</strong> {context["group"].name}</p>'
            )

        if config.get("show_date"):
            html_parts.append(
                f'<p class="cover-meta"><strong>Datum:</strong> '
                f'{context["report_date"].strftime("%d.%m.%Y")}</p>'
            )

        if config.get("subtitle"):
            html_parts.append(
                f'<p class="cover-subtitle">{config.get("subtitle", "Entwicklungsprofil")}</p>'
            )

        html_parts.append("</div>")
        return "\n".join(html_parts)

    def _render_self_assessment(
        self,
        context,
        page_num: int = 1,
        total_pages: int = 1,
        sidebar_mode: str = "minimal",
    ) -> str:
        """Rendert die Selbsteinschätzung mit Sidebar-Layout."""
        if not context["self_assessment"]:
            sidebar = self._render_sidebar(
                page_num, total_pages, sidebar_mode, leitung_label="se"
            )
            return f"""<div class="sb-page">
                {sidebar}
                <main class="sb-main">
                    <h2 class="sb-subtitle">Selbsteinschätzung</h2>
                    <p><em>Keine Selbsteinschätzung vorhanden</em></p>
                </main>
            </div>"""

        sa = context["self_assessment"]
        sidebar = self._render_sidebar(
            page_num, total_pages, sidebar_mode, leitung_label="se"
        )

        return f"""<div class="sb-page">
            {sidebar}
            <main class="sb-main">
                <h2 class="sb-subtitle">Selbsteinschätzung</h2>
                <section class="sb-section">
                    <p style="font-size: 9pt; color: #888; margin-bottom: 12pt;">
                        Geführt am: {sa.created_at.strftime("%d.%m.%Y")}
                    </p>
                    <div class="sb-text-content">{sa.content}</div>
                </section>
                <div class="sb-main-spacer"></div>
            </main>
        </div>"""

    def _render_external_assessment(
        self,
        context,
        page_num: int = 1,
        total_pages: int = 2,
        sidebar_mode: str = "minimal",
    ) -> str:
        """
        Rendert die Fremdeinschätzung als 2-Seiten-Sidebar-Layout.
        Seite 1: Soziale Kompetenzen + Radardiagramm
        Seite 2: Verbale Kompetenzen + Radardiagramm + optional Zusammenfassung
        """
        ki_texts = context["ki_texts"]

        if not ki_texts or not any(
            [ki_texts.get("social_text"), ki_texts.get("verbal_text")]
        ):
            sidebar = self._render_sidebar(
                page_num, total_pages, sidebar_mode, leitung_label="fe"
            )
            return f"""<div class="sb-page">
                {sidebar}
                <main class="sb-main">
                    <h2 class="sb-subtitle">Fremdeinschätzung</h2>
                    <p><em>Keine KI-Analyse durchgeführt</em></p>
                </main>
            </div>"""

        primary = self.theme.get("primary_color", "#5A7D7C")
        sk_ratings = context["sk_ratings"]
        vk_ratings = context["vk_ratings"]

        # Radardiagramme
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
            "#2F4F4F",
        )

        # Seite 1
        sidebar1 = self._render_sidebar(
            page_num, total_pages, sidebar_mode, leitung_label="fe"
        )
        page1 = f"""<div class="sb-page">
            {sidebar1}
            <main class="sb-main">
                <h2 class="sb-subtitle">Fremdeinschätzung (KI-Analyse)</h2>
                <section class="sb-section">
                    <h3 class="sb-section-title">Soziale Kompetenzen</h3>
                    <div class="sb-text-content">{ki_texts.get("social_text", "")}</div>
                    <div class="sb-chart-container">
                        <img src="{sk_chart}" alt="Radardiagramm Soziale Kompetenzen">
                    </div>
                </section>
                <div class="sb-main-spacer"></div>
            </main>
        </div>"""

        # Seite 2
        sidebar2 = self._render_sidebar(
            page_num + 1, total_pages, sidebar_mode, leitung_label="fe"
        )

        summary_html = ""
        if ki_texts.get("summary_text"):
            summary_html = f"""<section class="sb-section">
                    <h3 class="sb-section-title">Zusammenfassung</h3>
                    <div class="sb-text-content">{ki_texts.get("summary_text", "")}</div>
                </section>"""

        page2 = f"""<div class="sb-page">
            {sidebar2}
            <main class="sb-main">
                <section class="sb-section">
                    <h3 class="sb-section-title">Verbale Kompetenzen</h3>
                    <div class="sb-text-content">{ki_texts.get("verbal_text", "")}</div>
                    <div class="sb-chart-container">
                        <img src="{vk_chart}" alt="Radardiagramm Verbale Kompetenzen">
                    </div>
                </section>
                {summary_html}
                <div class="sb-main-spacer"></div>
            </main>
        </div>"""

        return page1 + page2

    def _render_closing_page(
        self,
        context,
        page_num: int = 1,
        total_pages: int = 1,
        sidebar_mode: str = "minimal",
    ) -> str:
        """Rendert das Abschlussblatt mit Unterschriften (Sidebar-Layout)."""
        config = context["modules_config"].get("closing_page", {})
        sidebar = self._render_sidebar(page_num, total_pages, sidebar_mode)

        # Zusatztext
        additional_html = ""
        if config.get("additional_text"):
            additional_html = (
                f'<div class="info-box"><p>{config["additional_text"]}</p></div>'
            )

        # Unterschriften mit JPG-Bildern
        leitung_fe = getattr(self.group, "leitung_fremdeinschatzung", "") or ""
        leitung_se = getattr(self.group, "leitung_selbsteinschatzung", "") or ""

        sig_fe_img = ""
        if self.signature_fe:
            sig_path = (
                (self.project_root / self.signature_fe.image_path).resolve().as_uri()
            )
            sig_fe_img = f'<img src="{sig_path}" alt="Unterschrift Leitung FE">'

        sig_se_img = ""
        if self.signature_se:
            sig_path = (
                (self.project_root / self.signature_se.image_path).resolve().as_uri()
            )
            sig_se_img = f'<img src="{sig_path}" alt="Unterschrift Leitung SE">'

        signatures_html = f"""
        <div class="signature-block" style="margin-top: 60pt;">
            <div class="signature-item">
                {sig_fe_img}
                <div class="signature-line">Leitung Fremdeinschätzung</div>
                <div class="signature-name">{leitung_fe}</div>
            </div>
            <div class="signature-item">
                {sig_se_img}
                <div class="signature-line">Leitung Selbsteinschätzung</div>
                <div class="signature-name">{leitung_se}</div>
            </div>
        </div>"""

        return f"""<div class="sb-page">
            {sidebar}
            <main class="sb-main">
                <h2 class="sb-subtitle">Abschlussblatt</h2>
                {additional_html}
                {signatures_html}
                <div class="sb-main-spacer"></div>
            </main>
        </div>"""

    def _render_info_page(self, context) -> str:
        """Rendert das Hinweisblatt (eigenständig, OHNE Sidebar)."""
        if not self.explanation_blocks:
            return """<div class="page info-page">
                <h2>Hinweise und Informationen</h2>
                <div class="info-box">
                    <em>Keine Erklärungstexte ausgewählt.</em>
                </div>
            </div>"""

        blocks_html = []
        for block in self.explanation_blocks:
            blocks_html.append(
                f"""<div class="info-box">
                <h3>{block.title}</h3>
                <div>{block.content}</div>
            </div>"""
            )

        return f"""<div class="page info-page">
            <h2>Hinweise und Informationen</h2>
            {''.join(blocks_html)}
        </div>"""

    # =========================================================================
    # PDF-Export
    # =========================================================================

    def to_pdf(self, mode: str = "combined") -> bytes:
        """Konvertiert HTML zu PDF."""
        html_string = self.build_html(mode=mode)
        pdf_bytes = HTML(
            string=html_string, base_url=str(self.project_root)
        ).write_pdf()
        return pdf_bytes

    def to_file(self, filepath: str, mode: str = "combined") -> str:
        """Speichert das PDF in eine Datei."""
        pdf_bytes = self.to_pdf(mode=mode)
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        return filepath
