"""
Layout-Regressionstests für die PDF-Berichte (services/report_generator.py).

Hintergrund: Die Fremdeinschätzung ging von genau 2 Seiten aus. Bei längeren
Texten entstand eine Leerseite (nur Sidebar), und der Rest der Zusammenfassung
wurde abgeschnitten. Diese Tests rendern echte PDFs mit WeasyPrint und prüfen:

- keine Seite ohne Inhalt (nur Sidebar)
- kein Textverlust: der letzte Satz jedes Textes steht im PDF
- Sidebar und "Seite X von Y" auf jeder Sidebar-Seite, auch auf Folgeseiten
- Warnung, wenn ein Text mehr Seiten braucht als vorgesehen
"""

import json
import re
from datetime import date
from io import BytesIO
from uuid import uuid4

import pytest

try:
    import weasyprint  # noqa: F401

    WEASYPRINT_AVAILABLE = True
except Exception:  # System-Bibliotheken (Pango/Cairo) fehlen
    WEASYPRINT_AVAILABLE = False

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not WEASYPRINT_AVAILABLE, reason="WeasyPrint/Pango nicht verfügbar"
    ),
]

from models import (ExplanationBlock, Group, Participant, ReportConfiguration,
                    ReportTemplate, SelfAssessment)
from services.report_generator import ReportGenerator

SENTENCE = (
    "Er greift Beiträge anderer auf, entwickelt sie weiter und bindet "
    "zurückhaltende Mitglieder gezielt ein, etwa durch direkte Ansprache oder "
    "offene Fragen. "
)
END_SOCIAL = "Schlusswort Sozial endet hier."
END_VERBAL = "Schlusswort Verbal endet hier."
END_SUMMARY = "Schlusswort Zusammenfassung endet hier."

ALL_MODULES = {
    "cover_page": {
        "enabled": True,
        "show_title": True,
        "title": "Stärkenanalyse",
        "show_participant_name": True,
        "show_group_name": True,
        "show_date": True,
        "subtitle": "Entwicklungsprofil",
    },
    "self_assessment": {"enabled": True},
    "external_assessment": {"enabled": True},
    "closing_page": {"enabled": True, "additional_text": "Vielen Dank."},
    "info_page": {"enabled": True},
}


def _text(sentences: int, ending: str) -> str:
    return SENTENCE * sentences + ending


def _normalize(text: str) -> str:
    """Entfernt Silbentrennung am Zeilenende und vereinheitlicht Leerraum."""
    text = re.sub(r"-\s*\n\s*", "", text)
    return re.sub(r"\s+", " ", text)


def _pdf_pages(pdf_bytes: bytes) -> list:
    """Text je Seite."""
    from pdfminer.high_level import extract_text
    from pdfminer.pdfpage import PDFPage

    count = len(list(PDFPage.get_pages(BytesIO(pdf_bytes))))
    return [
        extract_text(BytesIO(pdf_bytes), page_numbers=[i]) for i in range(count)
    ]


@pytest.fixture
def make_generator(db):
    """Baut einen ReportGenerator mit frei wählbaren Texten und Modulen."""

    def _make(
        social=None,
        verbal=None,
        summary=None,
        modules=None,
        self_assessment=None,
        name="Stefan Peper",
    ):
        group = Group(
            name="Layout-Gruppe",
            date_from=date(2026, 9, 18),
            date_to=date(2026, 9, 20),
            location="Bad Waldliesborn",
            leitung_fremdeinschatzung="Timo Kreusch-Vartmann",
            leitung_selbsteinschatzung="Jana Weber",
            beobachter1="Timo Kreusch-Vartmann",
            beobachter2="Jana Weber",
        )
        db.session.add(group)
        db.session.flush()

        ki_texts = {
            "social_text": social if social is not None else _text(3, END_SOCIAL),
            "verbal_text": verbal if verbal is not None else _text(3, END_VERBAL),
            "summary_text": summary if summary is not None else _text(6, END_SUMMARY),
        }
        participant = Participant(
            name=name,
            group_id=group.id,
            observations="{}",
            sk_ratings=json.dumps(
                {
                    "flexibility": 6.5,
                    "team_orientation": 9,
                    "process_orientation": 3.5,
                    "results_orientation": 4,
                }
            ),
            vk_ratings=json.dumps(
                {
                    "flexibility": 6.5,
                    "consulting": 8.5,
                    "objectivity": 4.5,
                    "goal_orientation": 7,
                }
            ),
            ki_texts=json.dumps(ki_texts),
            footer_data="{}",
        )
        template = ReportTemplate(
            name=f"Layout-Template-{uuid4().hex}",
            design_config=json.dumps(
                {"primary_color": "#0052CC", "font_family": "Inter, sans-serif"}
            ),
        )
        db.session.add_all([participant, template])
        db.session.flush()

        if self_assessment is not None:
            db.session.add(
                SelfAssessment(participant_id=participant.id, content=self_assessment)
            )

        modules = dict(modules if modules is not None else ALL_MODULES)
        if modules.get("info_page", {}).get("enabled"):
            block = ExplanationBlock(
                title="Hinweis", content="<p>Erklärungstext.</p>", order=1
            )
            db.session.add(block)
            db.session.flush()
            modules["info_page"] = {"enabled": True, "selected_block_ids": [block.id]}

        config = ReportConfiguration(
            group_id=group.id,
            template_id=template.id,
            modules_config=json.dumps(modules),
        )
        db.session.add(config)
        db.session.commit()
        return ReportGenerator(group, participant, config)

    return _make


def _assert_sidebar_pages(pages, name="STEFAN PEPER", first=0, last=None):
    """Jede Sidebar-Seite zeigt Name und 'Seite X von Y' mit korrektem Y."""
    total = len(pages)
    last = total - 1 if last is None else last
    for index in range(first, last + 1):
        text = pages[index]
        assert name.lower() in text.lower(), f"Sidebar fehlt auf Seite {index + 1}"
        assert f"Seite {index + 1} von {total}" in _normalize(text), (
            f"Seitenzahl falsch/fehlt auf Seite {index + 1}"
        )


def _assert_no_blank_pages(pages, min_chars=150):
    for index, text in enumerate(pages):
        content = re.sub(r"\s+", "", text)
        assert len(content) > min_chars, f"Seite {index + 1} ist (fast) leer"


class TestForeignAssessmentLayout:
    def test_normal_length_is_three_clean_pages(self, make_generator):
        generator = make_generator()
        pages = _pdf_pages(generator.to_pdf(mode="standalone_fe"))

        assert len(pages) == 3
        assert generator.render_warnings == []
        _assert_sidebar_pages(pages)
        _assert_no_blank_pages(pages)
        assert "Soziale Kompetenzen" in pages[0] and END_SOCIAL in _normalize(pages[0])
        assert "Verbale Kompetenzen" in pages[1] and END_VERBAL in _normalize(pages[1])
        assert "Zusammenfassung" in pages[2] and END_SUMMARY in _normalize(pages[2])

    def test_without_summary_is_two_pages(self, make_generator):
        generator = make_generator(summary="")
        pages = _pdf_pages(generator.to_pdf(mode="standalone_fe"))

        assert len(pages) == 2
        assert generator.render_warnings == []
        _assert_sidebar_pages(pages)
        _assert_no_blank_pages(pages)

    def test_long_texts_flow_on_without_blank_page_or_loss(self, make_generator):
        """Der ursprüngliche Fehler: zu langer Text -> Leerseite + abgeschnittener Rest."""
        generator = make_generator(
            social=_text(30, END_SOCIAL),
            verbal=_text(30, END_VERBAL),
            summary=_text(30, END_SUMMARY),
        )
        pages = _pdf_pages(generator.to_pdf(mode="standalone_fe"))

        assert len(pages) > 3
        _assert_sidebar_pages(pages)
        _assert_no_blank_pages(pages)

        full_text = _normalize(" ".join(pages))
        for ending in (END_SOCIAL, END_VERBAL, END_SUMMARY):
            assert ending in full_text, f"Text abgeschnitten: {ending}"

        # Reihenfolge bleibt erhalten, jeder Abschnitt beginnt auf neuer Seite
        assert (
            full_text.index(END_SOCIAL)
            < full_text.index("Verbale Kompetenzen")
            < full_text.index(END_VERBAL)
            < full_text.index("Zusammenfassung")
            < full_text.index(END_SUMMARY)
        )

    def test_overflow_is_reported_as_warning(self, make_generator):
        generator = make_generator(social=_text(40, END_SOCIAL))
        generator.to_pdf(mode="standalone_fe")

        assert any(
            "Fremdeinschätzung" in warning and "statt 3 Seiten" in warning
            for warning in generator.render_warnings
        )

    def test_plain_text_with_line_breaks_becomes_paragraphs(self, make_generator):
        generator = make_generator(summary="Erster Absatz.\nZweiter Absatz.")
        html = generator.build_html(mode="standalone_fe")

        assert "<p>Erster Absatz.</p><p>Zweiter Absatz.</p>" in html

    def test_text_is_sanitized(self, make_generator):
        generator = make_generator(
            social='<p>Sicher</p><script>alert(1)</script>',
            verbal="a < b & c > d",
            name="Anna <b>Test</b>",
        )
        html = generator.build_html(mode="standalone_fe")

        assert "<script>" not in html
        assert "<b>Test</b>" not in html
        assert "a &lt; b &amp; c &gt; d" in html
        # trotzdem renderbar
        assert _pdf_pages(generator.to_pdf(mode="standalone_fe"))


class TestSelfAssessmentLayout:
    def test_short_text_is_one_page(self, make_generator):
        generator = make_generator(self_assessment="Ich bin teamfähig.")
        pages = _pdf_pages(generator.to_pdf(mode="standalone_se"))

        assert len(pages) == 1
        _assert_sidebar_pages(pages)

    def test_long_text_flows_onto_further_pages(self, make_generator):
        long_text = "<p>" + SENTENCE * 60 + END_SOCIAL + "</p>"
        generator = make_generator(self_assessment=long_text)
        pages = _pdf_pages(generator.to_pdf(mode="standalone_se"))

        assert len(pages) > 1
        _assert_sidebar_pages(pages)
        _assert_no_blank_pages(pages)
        assert END_SOCIAL in _normalize(" ".join(pages))
        assert any("Selbsteinschätzung" in warning for warning in generator.render_warnings)


class TestCombinedReportLayout:
    def test_all_modules_have_consistent_pages_and_numbers(self, make_generator):
        generator = make_generator(self_assessment="Ich bin teamfähig.")
        pages = _pdf_pages(generator.to_pdf(mode="combined"))

        # Deckblatt, SE, FE (3), Abschluss, Hinweisblatt
        assert len(pages) == 7
        assert generator.render_warnings == []

        # Deckblatt und Hinweisblatt ohne Sidebar/Seitenzahl
        assert "Stärkenanalyse" in pages[0]
        assert "Seite 1 von" not in pages[0]
        assert "Hinweise und Informationen" in pages[-1]
        assert "von 7" not in pages[-1]

        # Alle Seiten dazwischen: Sidebar + korrekte Seitenzählung über das ganze Dokument
        _assert_sidebar_pages(pages, first=1, last=5)

        # Combined: Sidebar minimal, ohne Rahmendaten
        assert "RAHMENDATEN" not in " ".join(pages)

    def test_long_foreign_assessment_keeps_numbering_correct(self, make_generator):
        generator = make_generator(
            self_assessment="Kurz.", summary=_text(30, END_SUMMARY)
        )
        pages = _pdf_pages(generator.to_pdf(mode="combined"))

        assert len(pages) > 7
        _assert_sidebar_pages(pages, first=1, last=len(pages) - 2)
        assert END_SUMMARY in _normalize(" ".join(pages))
        assert "Hinweise und Informationen" in pages[-1]

    def test_standalone_has_metadata_in_sidebar(self, make_generator):
        generator = make_generator()
        pages = _pdf_pages(generator.to_pdf(mode="standalone_fe"))

        for text in pages:
            assert "RAHMENDATEN" in text
            assert "Timo Kreusch-Vartmann" in _normalize(text)


class TestReportRoutesUseSameLayout:
    """Download, Vorschau und Alt-URL liefern dasselbe Layout."""

    def test_standalone_fe_download_and_inline_preview(self, client, make_generator):
        generator = make_generator()
        participant_id = generator.participant.id

        download = client.get(
            f"/reports/standalone/foreign-assessment/{participant_id}/pdf"
        )
        assert download.status_code == 200
        assert "attachment" in download.headers["Content-Disposition"]
        assert download.headers["X-Frame-Options"] == "DENY"
        assert len(_pdf_pages(download.data)) == 3

        inline = client.get(
            f"/reports/standalone/foreign-assessment/{participant_id}/pdf?inline=1"
        )
        assert inline.status_code == 200
        assert "attachment" not in inline.headers.get("Content-Disposition", "")
        assert inline.headers["X-Frame-Options"] == "SAMEORIGIN"
        assert len(_pdf_pages(inline.data)) == 3

        preview = client.get(
            f"/reports/standalone/foreign-assessment/{participant_id}/preview"
        )
        assert preview.status_code == 200
        assert b"foreign-assessment/%d/pdf?inline=1" % participant_id in preview.data

    def test_combined_download_matches_generator(self, client, make_generator):
        generator = make_generator(self_assessment="Kurz.")
        response = client.get(
            f"/reports/{generator.group.id}/generate-pdf/{generator.participant.id}"
        )

        assert response.status_code == 200
        assert len(_pdf_pages(response.data)) == 7

    def test_legacy_url_redirects_to_unified_pipeline(self, client, make_generator):
        generator = make_generator()
        response = client.get(f"/bericht/{generator.participant.id}/pdf")

        assert response.status_code == 302
        assert "/reports/standalone/foreign-assessment/" in response.headers["Location"]
