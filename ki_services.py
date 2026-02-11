"""
Compatibility layer for AI services.
Delegates to modular implementations in services/.
"""

from services.ai_client import (
    GenerativeModel,
    NotFound,
    MISTRAL_CLIENT,
    MISTRAL_MODEL,
    genai_client,
    _call_gemini,
    save_ai_raw_response,
    compute_content_diff,
    generate_report_with_ai,
    generate_text_report_with_ai,
)
from services.task_generator import generate_task
from services.task_refinement import refine_task_content
from services.task_normalization import (
    _clean_html_output,
    _has_empty_sections,
    _normalize_task_html,
    _ensure_all_sections_filled,
    _validate_task_content,
)

__all__ = [
    "GenerativeModel",
    "NotFound",
    "MISTRAL_CLIENT",
    "MISTRAL_MODEL",
    "genai_client",
    "_call_gemini",
    "save_ai_raw_response",
    "compute_content_diff",
    "generate_report_with_ai",
    "generate_text_report_with_ai",
    "generate_task",
    "refine_task_content",
    "_clean_html_output",
    "_has_empty_sections",
    "_normalize_task_html",
    "_ensure_all_sections_filled",
    "_validate_task_content",
]
