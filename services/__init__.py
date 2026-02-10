"""
Services Modul - Geschäftslogik für die Anwendung.
"""

from .report_generator import ReportGenerator
from .task_knowledge_base import get_knowledge_for_prompt, get_target_group_options

__all__ = ["ReportGenerator", "get_knowledge_for_prompt", "get_target_group_options"]
