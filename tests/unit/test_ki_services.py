"""
Unit-Tests für KI-Services (ki_services.py)

Testet:
- generate_report_with_ai mit Mistral/Gemini (mocked)
- Fehlerfälle (fehlende Clients/ungültiges Modell)
"""

import json
import pytest
from unittest.mock import MagicMock, create_autospec, patch

from mistralai.client import MistralClient

from services.ai_client import generate_report_with_ai


@pytest.mark.unit
class TestGenerateReportWithAI:
    """Tests für generate_report_with_ai()"""

    def test_invalid_model_returns_error(self):
        """Test: Ungültiges Modell liefert Error-JSON"""
        result = generate_report_with_ai("Prompt", "invalid-model")
        parsed = json.loads(result)
        assert "error" in parsed

    @patch("services.ai_client.MISTRAL_CLIENT")
    def test_mistral_success(self, mock_client):
        """Test: Mistral-Call erfolgreich (mocked)"""
        mock_message = MagicMock()
        mock_message.content = "{\"ok\": true}"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.return_value = mock_response

        result = generate_report_with_ai("Prompt", "mistral")
        assert result == "{\"ok\": true}"
        mock_client.chat.assert_called_once()

    @patch("services.ai_client.MISTRAL_CLIENT", None)
    def test_mistral_missing_client_returns_error(self):
        """Test: Mistral ohne Client liefert Error-JSON"""
        result = generate_report_with_ai("Prompt", "mistral")
        parsed = json.loads(result)
        assert "error" in parsed

    @patch("services.ai_client.genai_client", True)
    @patch("services.ai_client.GenerativeModel")
    def test_gemini_success(self, mock_model_cls):
        """Test: Gemini-Call erfolgreich (mocked)"""
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "{\"ok\": true}"
        mock_model.generate_content.return_value = mock_response
        mock_model_cls.return_value = mock_model

        result = generate_report_with_ai("Prompt", "gemini")
        assert result == "{\"ok\": true}"
        mock_model.generate_content.assert_called_once()

    @patch("services.ai_client.GenerativeModel", None)
    def test_gemini_missing_library_returns_error(self):
        """Test: Gemini ohne Library liefert Error-JSON"""
        result = generate_report_with_ai("Prompt", "gemini")
        parsed = json.loads(result)
        assert "error" in parsed

    @patch("services.ai_client.MISTRAL_CLIENT")
    def test_mistral_exception_returns_error(self, mock_client):
        """Test: Mistral-Exception wird als Error-JSON zurückgegeben (nicht geworfen).

        generate_report_with_ai() darf laut Contract niemals eine Exception
        werfen - auch nicht bei unerwarteten Fehlern von Provider-SDKs
        (z. B. google.api_core.exceptions.ResourceExhausted bei Gemini-
        Rate-Limits). Sonst landet der Request beim generischen 500-Handler
        und der Nutzer sieht nur "Ein interner Fehler ist aufgetreten."
        """
        mock_client.chat.side_effect = Exception("Boom")
        result = generate_report_with_ai("Prompt", "mistral")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "Boom" in parsed["error"]

    @patch("services.ai_client.MISTRAL_CLIENT")
    def test_mistral_call_matches_real_sdk_signature(self, mock_client):
        """Regression-Test: `chat()` darf nur Kwargs nutzen, die die
        tatsächlich installierte mistralai-SDK-Version unterstützt.

        Vorher wurde `timeout=120` an `MistralClient.chat()` übergeben -
        ein Kwarg, das es in mistralai==0.4.2 gar nicht gibt. Das führte zu
        einem TypeError bei JEDEM Mistral-Aufruf, unabhängig vom API-Key.
        Mit `create_autospec` wird die reale Methodensignatur geprüft statt
        eines zu nachsichtigen MagicMocks, das beliebige Kwargs akzeptiert.
        """
        autospec_client = create_autospec(MistralClient, instance=True)
        mock_message = MagicMock()
        mock_message.content = "{\"ok\": true}"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        autospec_client.chat.return_value = mock_response

        with patch("services.ai_client.MISTRAL_CLIENT", autospec_client):
            result = generate_report_with_ai("Prompt", "mistral")

        parsed_or_raw = result
        assert parsed_or_raw == "{\"ok\": true}", (
            f"Erwartete erfolgreiche Antwort, bekam: {result!r} "
            "(deutet auf einen Kwarg-Mismatch mit der echten SDK-Signatur hin)"
        )
        autospec_client.chat.assert_called_once()
