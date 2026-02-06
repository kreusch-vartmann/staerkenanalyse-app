# config.py - Zentrale Konfigurations-Klassen
"""Konfigurations-Klassen für verschiedene Environments (Development, Production)."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Basis-Konfiguration (gemeinsame Settings)."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
    
    # SQLAlchemy
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,  # Prüft Verbindungen vor Nutzung
        'pool_recycle': 3600,   # Recyclet Connections nach 1h
    }
    
    # API Keys
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')
    
    # Upload-Ordner
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    
    # Session
    SESSION_COOKIE_SECURE = False  # In Production auf True setzen
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 Stunde


class DevelopmentConfig(Config):
    """Entwicklungs-Konfiguration."""
    
    DEBUG = True
    TESTING = False
    
    # Development-spezifische Settings
    SQLALCHEMY_ECHO = True  # SQL-Queries in Console loggen
    
    # Weniger strikte Security für Development
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Production-Konfiguration."""
    
    DEBUG = False
    TESTING = False
    
    # Production-spezifische Settings
    SQLALCHEMY_ECHO = False
    
    # Strikte Security für Production
    SESSION_COOKIE_SECURE = True
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')


class TestingConfig(Config):
    """Test-Konfiguration."""
    
    TESTING = True
    DEBUG = True
    
    # SQLite für Tests (schneller)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # CSRF-Protection deaktivieren für Tests
    WTF_CSRF_ENABLED = False


# Config-Dictionary für einfachen Zugriff
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Gibt die passende Config-Klasse basierend auf FLASK_ENV zurück."""
    env = os.getenv('FLASK_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)
