"""
Unit-Tests für Utility-Funktionen (utils.py)

Testet:
- sanitize_html
- validate_upload_file
- get_file_content
- clean_json_response
"""

import io
import json
import pytest
from werkzeug.datastructures import FileStorage

from utils import (
    sanitize_html,
    validate_upload_file,
    get_file_content,
    clean_json_response,
)


@pytest.mark.unit
class TestSanitizeHtml:
    def test_sanitize_allows_basic_tags(self):
        html = "<p><strong>Hallo</strong> <em>Welt</em></p>"
        cleaned = sanitize_html(html)
        assert "<strong>" in cleaned
        assert "<em>" in cleaned

    def test_sanitize_strips_script(self):
        html = "<p>OK</p><script>alert('x')</script>"
        cleaned = sanitize_html(html)
        assert "script" not in cleaned
        assert "OK" in cleaned

    def test_sanitize_empty(self):
        assert sanitize_html("") == ""
        assert sanitize_html(None) == ""


@pytest.mark.unit
class TestValidateUploadFile:
    def _make_filestorage(self, filename: str, content: bytes):
        return FileStorage(stream=io.BytesIO(content), filename=filename)

    def test_validate_ok_pdf(self):
        file = self._make_filestorage("test.pdf", b"%PDF-1.4 sample")
        filename = validate_upload_file(file)
        assert filename == "test.pdf"

    def test_validate_rejects_empty(self):
        file = self._make_filestorage("test.pdf", b"")
        with pytest.raises(ValueError):
            validate_upload_file(file)

    def test_validate_rejects_extension(self):
        file = self._make_filestorage("test.exe", b"bad")
        with pytest.raises(ValueError):
            validate_upload_file(file)

    def test_validate_rejects_missing_file(self):
        with pytest.raises(ValueError):
            validate_upload_file(None)


@pytest.mark.unit
class TestGetFileContent:
    def _make_filestorage(self, filename: str, content: bytes):
        return FileStorage(stream=io.BytesIO(content), filename=filename)

    def test_get_file_content_txt(self):
        file = self._make_filestorage("notes.txt", b"Hallo Welt")
        content = get_file_content(file)
        assert "Hallo Welt" in content
        assert "START INHALT" in content

    def test_get_file_content_invalid_extension(self):
        file = self._make_filestorage("notes.exe", b"Hallo Welt")
        content = get_file_content(file)
        assert "FEHLER" in content

    def test_get_file_content_empty_file(self):
        file = self._make_filestorage("notes.txt", b"")
        content = get_file_content(file)
        assert "FEHLER" in content or "HINWEIS" in content


@pytest.mark.unit
class TestCleanJsonResponse:
    def test_clean_json_removes_code_block(self):
        raw = "```json\n{\"a\": 1}\n```"
        cleaned = clean_json_response(raw)
        assert cleaned == '{"a": 1}'

    def test_clean_json_removes_newlines(self):
        raw = "{\n\"a\": 1\n}"
        cleaned = clean_json_response(raw)
        assert cleaned == '{"a": 1}'

    def test_clean_json_preserves_plain(self):
        raw = '{"a": 1}'
        cleaned = clean_json_response(raw)
        assert cleaned == '{"a": 1}'
