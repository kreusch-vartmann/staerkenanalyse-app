"""
Verschlüsselung sensibler Einstellungen (z. B. API-Keys) mit Fernet.

Der Fernet-Schlüssel wird deterministisch aus dem SECRET_KEY der App
abgeleitet (PBKDF2-HMAC-SHA256). Dadurch ist kein zweites Secret nötig.

WICHTIG: Ändert sich der SECRET_KEY, sind bestehende Werte nicht mehr
entschlüsselbar und müssen in der Admin-UI neu gesetzt werden.
"""

import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Statisches Salt: notwendig, damit der abgeleitete Schlüssel über
# Prozess-Restarts hinweg identisch bleibt (deterministische Ableitung).
_SALT = b"staerkenanalyse-app-settings-v1"
_ITERATIONS = 480_000


class CryptoHelper:
    """Verschlüsselt und entschlüsselt Strings mit Fernet (AES-128-CBC + HMAC)."""

    def __init__(self, secret_key: str):
        if not secret_key:
            raise ValueError("SECRET_KEY ist erforderlich für die Verschlüsselung")

        if isinstance(secret_key, str):
            secret_key = secret_key.encode()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=_SALT,
            iterations=_ITERATIONS,
        )
        self._fernet = Fernet(base64.urlsafe_b64encode(kdf.derive(secret_key)))

    def encrypt(self, value: str) -> str:
        """Verschlüsselt einen String."""
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, encrypted_value: str) -> str:
        """Entschlüsselt einen String.

        Raises:
            InvalidToken: Wenn der Wert beschädigt ist oder der
                SECRET_KEY nicht zum Zeitpunkt der Verschlüsselung passt.
        """
        try:
            return self._fernet.decrypt(encrypted_value.encode()).decode()
        except InvalidToken as exc:
            raise InvalidToken(
                "Wert konnte nicht entschlüsselt werden (SECRET_KEY geändert?)"
            ) from exc
