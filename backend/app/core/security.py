"""
Säkerhetsfunktioner: JWT-tokens och symmetrisk kryptering av API-nycklar.
API-nycklar (UniFi, Graph, Acronis, Cloudfactory) krypteras med Fernet AES-128
via cryptography-biblioteket innan de lagras i databasen.
"""

from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from fastapi import HTTPException, status
from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_BCRYPT_MAX_BYTES = 72


def _fernet() -> Fernet:
    """
    Läser ENCRYPTION_KEY rakt av — den måste vara en giltig Fernet-nyckel
    (base64url, 32 bytes). Generera med:
      python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """
    if not settings.ENCRYPTION_KEY:
        raise RuntimeError("ENCRYPTION_KEY saknas i miljövariablerna")
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet().decrypt(ciphertext.encode()).decode()


def _validate_password_length(password: str) -> None:
    if len(password.encode("utf-8")) > _BCRYPT_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Lösenordet är för långt — max {_BCRYPT_MAX_BYTES} bytes (UTF-8).",
        )


def hash_password(password: str) -> str:
    _validate_password_length(password)
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    _validate_password_length(plain)
    return pwd_context.verify(plain, hashed)


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
