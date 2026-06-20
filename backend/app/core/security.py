"""
Säkerhetsfunktioner: JWT-tokens och symmetrisk kryptering av API-nycklar.
API-nycklar (UniFi, Graph, Acronis, Cloudfactory) krypteras med AES-128-CBC
via cryptography-biblioteket innan de lagras i databasen.
"""

import base64
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Fernet kräver en 32-byte URL-safe base64-kodad nyckel
def _fernet() -> Fernet:
    key_bytes = settings.ENCRYPTION_KEY.encode()[:32].ljust(32, b"0")
    return Fernet(base64.urlsafe_b64encode(key_bytes))


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


def hash_password(password: str) -> str:
    return pwd_context.hash(_truncate_for_bcrypt(password))


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(_truncate_for_bcrypt(plain), hashed)


def _truncate_for_bcrypt(password: str) -> str:
    """
    bcrypt hanterar max 72 bytes. Ett långt lösenord (t.ex. en lång
    passphrase i FIRST_ADMIN_PASSWORD) ska trunkeras konsekvent vid
    hashning OCH verifiering — annars kraschar appen vid uppstart
    istället för att bara klippa lösenordet.
    """
    encoded = password.encode("utf-8")
    if len(encoded) <= 72:
        return password
    return encoded[:72].decode("utf-8", errors="ignore")


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": subject, "exp": expire},
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def decode_token(token: str) -> str:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    return payload["sub"]
