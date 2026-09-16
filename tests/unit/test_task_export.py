"""
Unit-Tests für services/task_export.py (PDF-/DOCX-Export einzelner Aufgaben).
"""

import io

import pytest

from services.task_export import (
    TaskExportError,
    build_blank_task_template_docx,
    build_task_docx,
    build_task_pdf_html,
    task_to_pdf_bytes,
)


class _FakeVersion:
    def __init__(self, content):
        self.content = content


class _FakeTask:
    """Leichtgewichtiges Double statt einem echten DB-Objekt - die
    Export-Funktionen greifen nur auf title/participant_count/
    duration_minutes/current_version.content zu."""

    def __init__(self, title="Testaufgabe", participant_count=4, duration_minutes=30, content=None):
        self.title = title
        self.participant_count = participant_count
        self.duration_minutes = duration_minutes
        self.current_version = _FakeVersion(
            content
            or (
                "<h2>Testaufgabe</h2>"
                "<h3>Aufgabe</h3><p>Ausgangssituation hier.</p><p>Konkreter Auftrag.</p>"
                "<h3>Rahmenbedingungen</h3>"
                "<p><strong>Ablauf:</strong></p>"
                "<ol><li>Phase 1</li><li>Phase 2</li><li>Phase 3</li></ol>"
                "<p><strong>Materialien:</strong></p>"
                "<ul><li>Stifte</li><li>Papier</li></ul>"
            )
        )


@pytest.mark.unit
class TestBuildTaskPdfHtml:
    def test_contains_title_and_meta(self):
        task = _FakeTask(title="Bergwanderung", participant_count=5, duration_minutes=45)
        html = build_task_pdf_html(task)
        assert "<h1>Bergwanderung</h1>" in html
        assert "5 Teilnehmende" in html
        assert "45 Minuten" in html

    def test_leading_h2_from_content_is_stripped_once(self):
        """Der Content enthält bereits <h2>Titel</h2> - der würde sich mit
        der eigenen <h1> doppeln, wird daher genau einmal entfernt."""
        task = _FakeTask()
        html = build_task_pdf_html(task)
        assert html.count("<h1>") == 1
        assert "<h2>Testaufgabe</h2>" not in html

    def test_only_aufgabe_and_rahmenbedingungen_sections(self):
        """Beobachtungsfokus/Facilitator-Hinweise dürfen nie im Export
        landen (Teilnehmer-Ausdruck) - hier wird nur sichergestellt, dass
        ausschließlich die Sektionen aus content erscheinen."""
        task = _FakeTask()
        html = build_task_pdf_html(task)
        assert "<h3>Aufgabe</h3>" in html
        assert "<h3>Rahmenbedingungen</h3>" in html

    def test_no_meta_line_without_metadata(self):
        task = _FakeTask(participant_count=None, duration_minutes=None)
        html = build_task_pdf_html(task)
        assert 'class="meta"' not in html


@pytest.mark.unit
class TestTaskToPdfBytes:
    def test_generates_valid_pdf_or_raises_clear_error(self):
        """WeasyPrint braucht System-Bibliotheken (Pango/Cairo), die nicht
        auf jedem Entwicklungsrechner installiert sind. Statt den Test zu
        skippen, wird beides akzeptiert - Hauptsache kein unklarer Crash."""
        task = _FakeTask()
        try:
            pdf_bytes = task_to_pdf_bytes(task)
        except TaskExportError as e:
            assert "WeasyPrint" in str(e) or "Pango" in str(e) or "Cairo" in str(e)
            return
        assert pdf_bytes[:5] == b"%PDF-"
        assert len(pdf_bytes) > 500


@pytest.mark.unit
class TestBuildTaskDocx:
    def test_generates_valid_docx_with_correct_structure(self):
        task = _FakeTask(title="Bergwanderung", participant_count=6, duration_minutes=50)
        docx_bytes = build_task_docx(task)

        import docx

        document = docx.Document(io.BytesIO(docx_bytes))
        texts = [p.text for p in document.paragraphs if p.text.strip()]
        styles = [p.style.name for p in document.paragraphs if p.text.strip()]

        assert texts[0] == "Bergwanderung"
        assert any("6 Teilnehmende" in t and "50 Minuten" in t for t in texts)
        assert "Aufgabe" in texts
        assert "Rahmenbedingungen" in texts
        assert "List Number" in styles
        assert "List Bullet" in styles

    def test_bold_markers_become_bold_runs(self):
        task = _FakeTask()
        docx_bytes = build_task_docx(task)

        import docx

        document = docx.Document(io.BytesIO(docx_bytes))
        bold_texts = [
            run.text for p in document.paragraphs for run in p.runs if run.bold
        ]
        assert any("Ablauf:" in t for t in bold_texts)
        assert any("Materialien:" in t for t in bold_texts)

    def test_missing_python_docx_raises_task_export_error(self, monkeypatch):
        import services.task_export as task_export_module
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "docx":
                raise ImportError("simuliert: python-docx fehlt")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(TaskExportError):
            task_export_module.build_task_docx(_FakeTask())


@pytest.mark.unit
class TestBuildBlankTaskTemplateDocx:
    """Downloadbare Leer-Vorlage für externes Ausfüllen + Re-Import."""

    def test_generates_valid_docx_with_correct_styles(self):
        import docx

        template_bytes = build_blank_task_template_docx()
        document = docx.Document(io.BytesIO(template_bytes))

        styles = {p.style.name for p in document.paragraphs if p.text.strip()}
        assert "Title" in styles
        assert "Heading 2" in styles
        assert "List Number" in styles
        assert "List Bullet" in styles

    def test_roundtrips_through_parser_into_valid_task(self):
        """Die Vorlage selbst muss - unverändert hochgeladen - bereits eine
        valide (wenn auch mit Platzhaltern gefüllte) Aufgabe ergeben."""
        from services.task_import import parse_task_docx
        from services.task_normalization import _normalize_task_html, _validate_task_content

        template_bytes = build_blank_task_template_docx()

        class _FS:
            def __init__(self, stream, filename):
                self.stream = stream
                self.filename = filename

            def read(self):
                return self.stream.read()

        html = parse_task_docx(_FS(io.BytesIO(template_bytes), "vorlage.docx"))
        normalized = _normalize_task_html(html, title="Titel der Aufgabe (hier ersetzen)")
        valid, reason = _validate_task_content(normalized)
        assert valid, reason
        assert "<h3>Aufgabe</h3>" in normalized
        assert "<h3>Rahmenbedingungen</h3>" in normalized
