"""
Dieses Modul definiert die SQLAlchemy-Datenbankmodelle für die Anwendung.
Jede Klasse repräsentiert eine Tabelle in der Datenbank.
"""

from datetime import datetime, timezone  # timezone für UTC
from enum import Enum

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


# =============================================================================
# Enums für Task-System
# =============================================================================
class ObservationArea(Enum):
    """Beobachtungsbereiche für Assessment-Center Aufgaben."""
    SOZIALE_KOMPETENZEN = "Soziale Kompetenzen"
    VERBALE_KOMPETENZEN = "Verbale Kompetenzen"


# =============================================================================
# User Management & Authentication Models
# =============================================================================

# Many-to-Many Association Tables

# User ↔ Group
user_groups = db.Table(
    "user_groups",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("group_id", db.Integer, db.ForeignKey("groups.id"), primary_key=True),
)

# Group ↔ Task (Aufgaben einer Gruppe)
group_tasks = db.Table(
    "group_tasks",
    db.Column("group_id", db.Integer, db.ForeignKey("groups.id"), primary_key=True),
    db.Column("task_id", db.Integer, db.ForeignKey("tasks.id"), primary_key=True),
    db.Column("assigned_at", db.DateTime, default=datetime.now(timezone.utc)),
)


class Role(db.Model):
    """Rollen für die Zugriffskontrolle (RBAC)."""

    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    # Relationship
    users = db.relationship("User", back_populates="role")

    def __repr__(self):
        return f"<Role {self.name}>"


class User(UserMixin, db.Model):
    """Benutzer mit Login-Funktionalität (implementiert UserMixin von Flask-Login)."""

    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)

    # Foreign Key to Role
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    force_password_change = db.Column(db.Boolean, default=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc)
    )
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    role = db.relationship("Role", back_populates="users")
    groups = db.relationship(
        "Group",
        secondary=user_groups,
        backref="assigned_users",
        lazy="dynamic",
    )

    def set_password(self, password: str) -> None:
        """Hasht das Passwort und speichert es."""
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password: str) -> bool:
        """Prüft ob das gegebene Passwort dem Hash entspricht."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        """Prüft ob der Benutzer Admin ist."""
        return self.role.name.lower() == "admin"

    @property
    def full_name(self) -> str:
        """Gibt den vollständigen Namen zurück."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.email

    def __repr__(self):
        return f"<User {self.email} ({self.role.name})>"


class Group(db.Model):
    __tablename__ = "groups"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date_from = db.Column(db.Date, nullable=True)
    date_to = db.Column(db.Date, nullable=True)
    location = db.Column(db.String(100), nullable=True)
    # --- GEÄNDERT ---
    leitung_fremdeinschatzung = db.Column(db.String(100), nullable=True)
    beobachter1 = db.Column(db.String(100), nullable=True)
    beobachter2 = db.Column(db.String(100), nullable=True)
    # --- NEU ---
    leitung_selbsteinschatzung = db.Column(db.String(100), nullable=True)

    # Relationships
    participants = db.relationship(
        "Participant",
        back_populates="group",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )
    
    tasks = db.relationship(
        "Task",
        secondary=group_tasks,
        lazy="dynamic",
        backref="groups"
    )


class Participant(db.Model):
    __tablename__ = "participants"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)

    # JSON-Daten als Textfelder
    general_data = db.Column(db.Text, nullable=True)
    observations = db.Column(db.Text, nullable=True)
    sk_ratings = db.Column(db.Text, nullable=True)
    vk_ratings = db.Column(db.Text, nullable=True)
    ki_texts = db.Column(db.Text, nullable=True)
    ki_raw_response = db.Column(db.Text, nullable=True)
    ki_model = db.Column(db.String(20), nullable=True)  # "mistral" oder "gemini" - welche KI den Bericht generiert hat
    footer_data = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc)
    )

    # Relationships
    group = db.relationship("Group", back_populates="participants")
    self_assessment = db.relationship(
        "SelfAssessment",
        back_populates="participant",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Prompt(db.Model):
    __tablename__ = "prompts"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc)
    )


# --- NEUE TABELLE ---
class SelfAssessment(db.Model):
    __tablename__ = "self_assessments"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False, default="")
    participant_id = db.Column(
        db.Integer, db.ForeignKey("participants.id"), nullable=False, unique=True
    )

    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc)
    )

    # Relationship zum Teilnehmer
    participant = db.relationship("Participant", back_populates="self_assessment")


class ExplanationBlock(db.Model):
    __tablename__ = "explanation_blocks"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc)
    )


# =============================================================================
# Report-System: Templates, Konfigurationen, Logos
# =============================================================================


class ReportTemplate(db.Model):
    """
    Speichert vordefinierte Report-Design-Templates.
    Ein Template definiert Farben, Schriften, Layout etc.
    """

    __tablename__ = "report_templates"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    # Design-Konfiguration als JSON
    # Enthält: primary_color, secondary_color, accent_color, font_family,
    # font_size_base, layout_style, logo_placement, page_margins, etc.
    design_config = db.Column(db.Text, nullable=False)  # JSON

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc)
    )

    # Relationships
    report_configurations = db.relationship(
        "ReportConfiguration", back_populates="template", cascade="all, delete-orphan"
    )


class CompanyLogo(db.Model):
    """
    Zentral verwaltetes Company-Logo (ein aktives Logo zur Zeit).
    Kann später durch Versionierung erweitert werden.
    """

    __tablename__ = "company_logos"
    id = db.Column(db.Integer, primary_key=True)
    logo_path = db.Column(
        db.String(255), nullable=False
    )  # z.B. "uploads/logos/company_logo.png"
    filename = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    # Relationships
    report_configurations = db.relationship(
        "ReportConfiguration",
        back_populates="company_logo",
        cascade="all, delete-orphan",
    )


class ClientLogo(db.Model):
    """
    Auftraggeber-Logos, pro Gruppe eine Datei.
    """

    __tablename__ = "client_logos"
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("groups.id"), nullable=False)
    logo_path = db.Column(
        db.String(255), nullable=False
    )  # z.B. "uploads/logos/client_xyz_123.png"
    filename = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc)
    )

    # Relationships
    group = db.relationship("Group", backref="client_logo")
    report_configuration = db.relationship(
        "ReportConfiguration",
        back_populates="client_logo",
        uselist=False,
        cascade="all, delete-orphan",
    )


class ReportConfiguration(db.Model):
    """
    Speichert Report-Konfiguration pro Gruppe:
    - Welches Template nutzen?
    - Welche Logos?
    - Welche Module sind aktiviert (Deckblatt, Selbsteinschätzung, etc.)?
    - Was sollte auf welchem Modul angezeigt werden?
    """

    __tablename__ = "report_configurations"
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(
        db.Integer, db.ForeignKey("groups.id"), nullable=False, unique=True
    )
    template_id = db.Column(
        db.Integer, db.ForeignKey("report_templates.id"), nullable=True
    )
    company_logo_id = db.Column(
        db.Integer, db.ForeignKey("company_logos.id"), nullable=True
    )
    client_logo_id = db.Column(
        db.Integer, db.ForeignKey("client_logos.id"), nullable=True
    )

    # Modul-Konfiguration als JSON
    # Struktur:
    # {
    #   "cover_page": {
    #     "enabled": true,
    #     "show_title": true,
    #     "show_participant_name": true,
    #     "show_group_name": true,
    #     "show_date": true,
    #     "show_company_logo": true,
    #     "show_client_logo": true,
    #     "title": "Stärkenanalyse",
    #     "subtitle": "Entwicklungsprofil"
    #   },
    #   "self_assessment": {"enabled": true},
    #   "external_assessment": {"enabled": true},
    #   "closing_page": {
    #     "enabled": true,
    #     "show_signature_fields": true,
    #     "signature_lines_count": 3,
    #     "additional_text": "..."
    #   },
    #   "info_page": {"enabled": true, "content": "..."},
    #   "toc_enabled": false
    # }
    modules_config = db.Column(db.Text, nullable=False)  # JSON

    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc)
    )

    # Relationships
    group = db.relationship("Group", backref="report_configuration")
    template = db.relationship("ReportTemplate", back_populates="report_configurations")
    company_logo = db.relationship(
        "CompanyLogo", back_populates="report_configurations"
    )
    client_logo = db.relationship("ClientLogo", back_populates="report_configuration")


class SignatureImage(db.Model):
    """
    Global verwaltete Unterschrift-Bilder (JPG/PNG) für Leitung FE und Leitung SE.
    Pro Rolle (leitung_fe / leitung_se) kann ein aktives Bild existieren.
    """

    __tablename__ = "signature_images"
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)  # 'leitung_fe' oder 'leitung_se'
    image_path = db.Column(
        db.String(255), nullable=False
    )  # z.B. "uploads/signatures/sig_fe.jpg"
    filename = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))


# =============================================================================
# Phase 2: Task Generator System
# =============================================================================


class Task(db.Model):
    """
    Task-Template für Assessment-Center Aufgaben.
    Versionsverwaltung erlaubt Iteration und History-Tracking.
    """

    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    
    # Metadaten
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Task-Klassifizierung
    observation_area = db.Column(
        db.String(50), nullable=False
    )  # "Soziale Kompetenzen" oder "Verbale Kompetenzen"
    participant_count = db.Column(
        db.Integer, nullable=True
    )  # 1–6, oder null für variabel
    duration_minutes = db.Column(
        db.Integer, nullable=True
    )  # 25–35 typisch, oder null
    
    # Version Control
    current_version_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "task_versions.id",
            use_alter=True,
            name="fk_tasks_current_version_id",
        ),
        nullable=True,
    )
    
    # Status & Audit
    is_active = db.Column(db.Boolean, default=True)
    is_example = db.Column(db.Boolean, default=False)  # True für vordefinierte Beispiel-Aufgaben
    ki_model = db.Column(db.String(20), nullable=True)  # "mistral" oder "gemini" - welche KI die Aufgabe generiert hat
    created_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc)
    )
    
    # Relationships
    versions = db.relationship(
        "TaskVersion",
        back_populates="task",
        cascade="all, delete-orphan",
        foreign_keys="TaskVersion.task_id",
    )
    current_version = db.relationship(
        "TaskVersion",
        foreign_keys=[current_version_id],
        uselist=False,
        lazy="joined"
    )
    created_by = db.relationship("User")
    
    def __repr__(self):
        return f"<Task {self.title} (v{len(self.versions)})>"


class TaskVersion(db.Model):
    """
    Versionierte Task-Inhalte mit Change-History.
    Jeder Save erzeugt neue Version; Revert zu Altversion möglich.
    """

    __tablename__ = "task_versions"
    id = db.Column(db.Integer, primary_key=True)
    
    # Relationship zu Task
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    
    # Versionierungsinformation
    version_number = db.Column(
        db.Float, nullable=False
    )  # 1.0, 1.1, 1.2, 2.0, etc.
    
    # Inhalt
    content = db.Column(
        db.Text, nullable=False
    )  # HTML von Quill.js Editor
    
    # Kontext-Daten (JSON)
    # Enthält Observation Area, Participant Count, Duration bei Version-Create
    context_data = db.Column(db.Text, nullable=True)  # JSON
    
    # Änderungs-Metadaten
    change_notes = db.Column(
        db.Text, nullable=True
    )  # "Präsentations-Element hinzugefügt", etc.
    created_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    # Relationships
    task = db.relationship("Task", back_populates="versions", foreign_keys=[task_id])
    created_by = db.relationship("User")
    
    def __repr__(self):
        return f"<TaskVersion {self.task.title} v{self.version_number}>"


# ============================================================================
# KI-GYM: Edit-Based Learning System
# ============================================================================

class AIRawResponse(db.Model):
    """Stores raw AI outputs before user editing for learning purposes."""
    __tablename__ = "ai_raw_responses"
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # 'task' or 'report'
    context_id = db.Column(db.Integer, nullable=False)  # task_id or participant_id
    ki_model = db.Column(db.String(100), nullable=False)  # e.g., 'mistral-large-latest'
    raw_response = db.Column(db.Text, nullable=False)  # Original AI output
    processing_status = db.Column(db.String(20), default='pending')  # 'pending', 'edited', 'analyzed'
    observation_area = db.Column(db.String(100), nullable=True)  # e.g., 'Sozialverhalten'
    context_metadata = db.Column(db.JSON, nullable=True)  # Additional context (prompt, temperature, etc.)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    edits = db.relationship("ContentEdit", back_populates="raw_response", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<AIRawResponse {self.type} #{self.context_id} ({self.ki_model})>"


class ContentEdit(db.Model):
    """Tracks differences between AI output and user's final version."""
    __tablename__ = "content_edits"
    
    id = db.Column(db.Integer, primary_key=True)
    raw_response_id = db.Column(db.Integer, db.ForeignKey("ai_raw_responses.id"), nullable=False)
    version_type = db.Column(db.String(50), nullable=False)  # 'task_version' or 'report'
    version_id = db.Column(db.Integer, nullable=False)  # ID of TaskVersion or report record
    diff_metrics = db.Column(db.JSON, nullable=False)  # {char_diff%, structure_changes, tone_shift}
    edit_reason = db.Column(db.Text, nullable=True)  # Optional: user-provided reason
    edited_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    raw_response = db.relationship("AIRawResponse", back_populates="edits")
    edited_by = db.relationship("User")
    
    def __repr__(self):
        return f"<ContentEdit for AIRawResponse {self.raw_response_id}>"


class LearnedPromptRule(db.Model):
    """Stores learned patterns and rules extracted from user edits."""
    __tablename__ = "learned_prompt_rules"
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False)  # 'task' or 'report'
    observation_area = db.Column(db.String(100), nullable=True)  # Specific area or NULL for global
    rule_type = db.Column(db.String(50), nullable=False)  # e.g., 'length', 'structure', 'tone', 'content'
    rule_content = db.Column(db.JSON, nullable=False)  # {pattern: "...", instruction: "..."}
    confidence = db.Column(db.Float, nullable=False, default=0.0)  # 0.0-1.0
    samples_analyzed = db.Column(db.Integer, nullable=False, default=0)
    trained_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    applied_in_prompt_version = db.Column(db.Integer, nullable=True)  # For tracking
    reasoning = db.Column(db.Text, nullable=True)  # AI's explanation of the rule
    is_active = db.Column(db.Boolean, default=True)  # Can be deactivated by admin
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # NULL for auto-generated
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    created_by = db.relationship("User")
    
    def __repr__(self):
        return f"<LearnedPromptRule {self.type}/{self.rule_type} (confidence: {self.confidence:.2f})>"
