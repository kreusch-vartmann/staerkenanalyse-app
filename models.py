"""
Dieses Modul definiert die SQLAlchemy-Datenbankmodelle für die Anwendung.
Jede Klasse repräsentiert eine Tabelle in der Datenbank.
"""
from datetime import datetime, UTC  # UTC hier importiert
from extensions import db

class Group(db.Model):
    __tablename__ = 'groups'
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

    # Relationship zu den Teilnehmern
    participants = db.relationship('Participant', back_populates='group', lazy='dynamic', cascade="all, delete-orphan")

class Participant(db.Model):
    __tablename__ = 'participants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    
    # JSON-Daten als Textfelder
    general_data = db.Column(db.Text, nullable=True)
    observations = db.Column(db.Text, nullable=True)
    sk_ratings = db.Column(db.Text, nullable=True)
    vk_ratings = db.Column(db.Text, nullable=True)
    ki_texts = db.Column(db.Text, nullable=True)
    ki_raw_response = db.Column(db.Text, nullable=True)
    footer_data = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    # Relationships
    group = db.relationship('Group', back_populates='participants')
    self_assessment = db.relationship('SelfAssessment', back_populates='participant', uselist=False, cascade="all, delete-orphan")

class Prompt(db.Model):
    __tablename__ = 'prompts'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

# --- NEUE TABELLE ---
class SelfAssessment(db.Model):
    __tablename__ = 'self_assessments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False, default='')
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False, unique=True)
    
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))

    # Relationship zum Teilnehmer
    participant = db.relationship('Participant', back_populates='self_assessment')

class ExplanationBlock(db.Model):
    __tablename__ = 'explanation_blocks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))


# =============================================================================
# Report-System: Templates, Konfigurationen, Logos
# =============================================================================

class ReportTemplate(db.Model):
    """
    Speichert vordefinierte Report-Design-Templates.
    Ein Template definiert Farben, Schriften, Layout etc.
    """
    __tablename__ = 'report_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    
    # Design-Konfiguration als JSON
    # Enthält: primary_color, secondary_color, accent_color, font_family,
    # font_size_base, layout_style, logo_placement, page_margins, etc.
    design_config = db.Column(db.Text, nullable=False)  # JSON
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    # Relationships
    report_configurations = db.relationship('ReportConfiguration', back_populates='template', cascade="all, delete-orphan")


class CompanyLogo(db.Model):
    """
    Zentral verwaltetes Company-Logo (ein aktives Logo zur Zeit).
    Kann später durch Versionierung erweitert werden.
    """
    __tablename__ = 'company_logos'
    id = db.Column(db.Integer, primary_key=True)
    logo_path = db.Column(db.String(255), nullable=False)  # z.B. "uploads/logos/company_logo.png"
    filename = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.now(UTC))
    
    # Relationships
    report_configurations = db.relationship('ReportConfiguration', back_populates='company_logo', cascade="all, delete-orphan")


class ClientLogo(db.Model):
    """
    Auftraggeber-Logos, pro Gruppe eine Datei.
    """
    __tablename__ = 'client_logos'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    logo_path = db.Column(db.String(255), nullable=False)  # z.B. "uploads/logos/client_xyz_123.png"
    filename = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    # Relationships
    group = db.relationship('Group', backref='client_logo')
    report_configuration = db.relationship('ReportConfiguration', back_populates='client_logo', uselist=False, cascade="all, delete-orphan")


class ReportConfiguration(db.Model):
    """
    Speichert Report-Konfiguration pro Gruppe:
    - Welches Template nutzen?
    - Welche Logos?
    - Welche Module sind aktiviert (Deckblatt, Selbsteinschätzung, etc.)?
    - Was sollte auf welchem Modul angezeigt werden?
    """
    __tablename__ = 'report_configurations'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False, unique=True)
    template_id = db.Column(db.Integer, db.ForeignKey('report_templates.id'), nullable=True)
    company_logo_id = db.Column(db.Integer, db.ForeignKey('company_logos.id'), nullable=True)
    client_logo_id = db.Column(db.Integer, db.ForeignKey('client_logos.id'), nullable=True)
    
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
    
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=datetime.now(UTC), onupdate=datetime.now(UTC))
    
    # Relationships
    group = db.relationship('Group', backref='report_configuration')
    template = db.relationship('ReportTemplate', back_populates='report_configurations')
    company_logo = db.relationship('CompanyLogo', back_populates='report_configurations')
    client_logo = db.relationship('ClientLogo', back_populates='report_configuration')

