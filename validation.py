"""Pydantic-based input validation helpers for Sprint 1.2."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_KI_MODELS = {"mistral", "gemini"}
ALLOWED_OBSERVATION_AREAS = {"Soziale Kompetenzen", "Verbale Kompetenzen"}
ALLOWED_EXPORT_FORMATS = {"xlsx", "csv"}


class BaseSchema(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class LoginForm(BaseSchema):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not EMAIL_PATTERN.match(value):
            raise ValueError("Ungültige E-Mail-Adresse")
        return value.lower()


class ChangePasswordForm(BaseSchema):
    old_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)
    confirm_password: str = Field(min_length=1, max_length=256)


class AdminUserCreateForm(BaseSchema):
    email: str = Field(min_length=3, max_length=255)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    role_name: str = Field(min_length=3, max_length=40)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if not EMAIL_PATTERN.match(value):
            raise ValueError("Ungültige E-Mail-Adresse")
        return value.lower()


class AdminUserUpdateForm(BaseSchema):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    role_name: str = Field(min_length=3, max_length=40)
    new_password: Optional[str] = Field(default=None, max_length=256)


class TaskCreateForm(BaseSchema):
    observation_area: str = Field(min_length=3, max_length=80)
    participant_count: int = Field(ge=1, le=10)
    duration_minutes: int = Field(ge=5, le=120)
    target_group: Optional[str] = Field(default=None, max_length=120)
    use_example: bool = Field(default=False)

    @field_validator("observation_area")
    @classmethod
    def validate_observation_area(cls, value: str) -> str:
        if value not in ALLOWED_OBSERVATION_AREAS:
            raise ValueError("Ungültiger Beobachtungsbereich")
        return value

    @field_validator("participant_count", "duration_minutes", mode="before")
    @classmethod
    def to_int(cls, value: Any) -> Any:
        if value is None or value == "":
            return None
        if isinstance(value, int):
            return value
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Ungültige Zahl") from exc

    @field_validator("use_example", mode="before")
    @classmethod
    def to_bool(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"on", "true", "1", "yes"}
        return bool(value)


class TaskGenerateForm(BaseSchema):
    ki_model: str = Field(default="mistral", max_length=40)

    @field_validator("ki_model")
    @classmethod
    def validate_ki_model(cls, value: str) -> str:
        if value not in ALLOWED_KI_MODELS:
            raise ValueError("Ungültiges KI-Modell")
        return value


class TaskSaveVersionPayload(BaseSchema):
    content: str = Field(min_length=1, max_length=200_000)
    change_notes: str = Field(default="Manuelle Bearbeitung", max_length=200)
    title: Optional[str] = Field(default=None, max_length=200)


class TaskChatPayload(BaseSchema):
    message: str = Field(min_length=1, max_length=2000)
    current_content: Optional[str] = Field(default=None, max_length=200_000)


class ParticipantNamesForm(BaseSchema):
    participant_names: str = Field(min_length=1, max_length=4000)


class ParticipantNameForm(BaseSchema):
    participant_name: str = Field(min_length=1, max_length=120)
    redirect_url: Optional[str] = Field(default=None, max_length=500)


class SelfAssessmentPayload(BaseSchema):
    content: str = Field(min_length=1, max_length=200_000)


class ObservationsPayload(BaseSchema):
    observations: Dict[str, Any]

    @field_validator("observations", mode="before")
    @classmethod
    def ensure_dict(cls, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("Ungültiges Format für Beobachtungen")
        return value


class DataEntrySearchQuery(BaseSchema):
    query: Optional[str] = Field(default=None, max_length=120)


class ImportNamesForm(BaseSchema):
    group_name: str = Field(min_length=1, max_length=120)


class ExportDataForm(BaseSchema):
    select_all_data: bool = Field(default=False)
    export_format: str = Field(default="xlsx", max_length=10)

    @field_validator("select_all_data", mode="before")
    @classmethod
    def to_bool(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"true", "1", "yes", "on"}
        return bool(value)

    @field_validator("export_format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        if value not in ALLOWED_EXPORT_FORMATS:
            raise ValueError("Ungültiges Export-Format")
        return value


class KiPromptForm(BaseSchema):
    ki_prompt: str = Field(default="", max_length=50_000)
    ki_model: str = Field(default="mistral", max_length=40)

    @field_validator("ki_model")
    @classmethod
    def validate_ki_model(cls, value: str) -> str:
        if value not in ALLOWED_KI_MODELS:
            raise ValueError("Ungültiges KI-Modell")
        return value


class BatchAnalysisPayload(BaseSchema):
    prompt_template: str = Field(default="", max_length=50_000)
    ki_model: str = Field(default="mistral", max_length=40)
    additional_content: str = Field(default="", max_length=200_000)

    @field_validator("ki_model")
    @classmethod
    def validate_ki_model(cls, value: str) -> str:
        if value not in ALLOWED_KI_MODELS:
            raise ValueError("Ungültiges KI-Modell")
        return value


def format_validation_error(error: ValidationError) -> str:
    parts = []
    for item in error.errors():
        loc = ".".join(str(entry) for entry in item.get("loc", [])) or "Feld"
        msg = item.get("msg", "Ungültige Eingabe")
        parts.append(f"{loc}: {msg}")
    return "; ".join(parts)


def parse_form(schema: type[BaseSchema], form_data: Dict[str, Any]) -> Tuple[Optional[BaseSchema], Optional[ValidationError]]:
    try:
        return schema.model_validate(form_data), None
    except ValidationError as exc:
        return None, exc


def parse_json(schema: type[BaseSchema], payload: Any) -> Tuple[Optional[BaseSchema], Optional[ValidationError]]:
    try:
        return schema.model_validate(payload), None
    except ValidationError as exc:
        return None, exc


def parse_observations(payload: Any) -> Tuple[Optional[Dict[str, Any]], Optional[ValidationError]]:
    try:
        model = ObservationsPayload.model_validate({"observations": payload})
        return model.observations, None
    except ValidationError as exc:
        return None, exc


def parse_id_list(raw_values: Iterable[str]) -> List[int]:
    ids: List[int] = []
    for value in raw_values:
        if isinstance(value, int):
            ids.append(value)
            continue
        if not value:
            continue
        if isinstance(value, str) and value.isdigit():
            ids.append(int(value))
    return ids
