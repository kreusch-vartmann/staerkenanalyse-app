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
    date = db.Column(db.Date, nullable=True)
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

