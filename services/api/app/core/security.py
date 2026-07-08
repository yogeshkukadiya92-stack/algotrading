from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class CredentialCipher:
    def __init__(self, key: str | None = None) -> None:
        raw_key = key or get_settings().broker_credential_encryption_key
        try:
            self._fernet = Fernet(raw_key.encode())
        except ValueError as exc:
            raise ValueError("BROKER_CREDENTIAL_ENCRYPTION_KEY must be a valid Fernet key") from exc

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Unable to decrypt broker credential") from exc

