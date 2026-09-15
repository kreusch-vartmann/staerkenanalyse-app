"""
Service für App-Einstellungen (z. B. API-Keys).

Werte werden verschlüsselt in der Tabelle `app_settings` gespeichert.
Lesereihenfolge: Datenbank -> Umgebungsvariable -> Default.
So bleibt der bisherige ENV-Betrieb (z. B. Container mit Secrets)
vollständig kompatibel, während Admins Keys auch über die UI pflegen können.
"""

import os
from datetime import datetime, timezone
from typing import Optional

import structlog
from flask import current_app

import models
from extensions import db
from services.crypto import CryptoHelper

logger = structlog.get_logger(__name__)

# Keys, die über die Admin-UI verwaltet werden
MANAGED_KEYS = ("MISTRAL_API_KEY", "GOOGLE_API_KEY")


def _crypto() -> CryptoHelper:
    """Erzeugt den Crypto-Helper aus dem SECRET_KEY der App."""
    return CryptoHelper(current_app.config["SECRET_KEY"])


def _load_row(key: str) -> Optional[models.AppSetting]:
    """Liest den DB-Datensatz für einen Key (None bei Fehler/nicht vorhanden)."""
    try:
        return db.session.scalars(
            db.select(models.AppSetting).filter_by(key=key)
        ).first()
    except Exception as exc:  # z. B. Tabelle fehlt (alte Migrationen)
        logger.warning("app_settings nicht lesbar", key=key, error=str(exc))
        db.session.rollback()
        return None


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Holt eine Einstellung: DB (entschlüsselt) -> ENV -> Default."""
    row = _load_row(key)
    if row and row.value_encrypted:
        try:
            return _crypto().decrypt(row.value_encrypted)
        except Exception as exc:
            # Falscher SECRET_KEY oder beschädigter Wert -> ENV-Fallback nutzen
            logger.error(
                "Einstellung konnte nicht entschlüsselt werden",
                key=key,
                error=str(exc),
            )

    return os.getenv(key) or default


def get_setting_source(key: str) -> Optional[str]:
    """Gibt zurück, woher der Wert kommt: 'db', 'env' oder None."""
    row = _load_row(key)
    if row and row.value_encrypted:
        return "db"
    if os.getenv(key):
        return "env"
    return None


def set_setting(key: str, value: str, user_id: Optional[int] = None) -> None:
    """Speichert eine Einstellung verschlüsselt in der Datenbank."""
    encrypted = _crypto().encrypt(value)
    row = _load_row(key)

    if row:
        row.value_encrypted = encrypted
        row.updated_at = datetime.now(timezone.utc)
        row.updated_by = user_id
    else:
        row = models.AppSetting(
            key=key,
            value_encrypted=encrypted,
            updated_at=datetime.now(timezone.utc),
            updated_by=user_id,
        )
        db.session.add(row)

    db.session.commit()
    logger.info("Einstellung gespeichert", key=key, user_id=user_id)


def delete_setting(key: str) -> bool:
    """Löscht eine Einstellung aus der Datenbank (ENV-Fallback greift danach)."""
    row = _load_row(key)
    if not row:
        return False

    db.session.delete(row)
    db.session.commit()
    logger.info("Einstellung gelöscht", key=key)
    return True


def mask_secret(value: Optional[str]) -> str:
    """Maskiert ein Secret für die Anzeige (nur letzte 4 Zeichen sichtbar)."""
    if not value:
        return ""
    if len(value) <= 4:
        return "•" * len(value)
    return "•" * 8 + value[-4:]
