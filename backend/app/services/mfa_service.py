"""Multi-Factor Authentication (MFA) Service with RFC 6238 TOTP and Encrypted Secret Storage."""

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import logging
import secrets
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.mfa import MFACredential
from app.models.user import User

logger = logging.getLogger("medigen.auth.mfa")


def _generate_base32_secret(length: int = 32) -> str:
    """Generate cryptographically secure base32 secret."""
    raw_bytes = secrets.token_bytes(20)
    return base64.b32encode(raw_bytes).decode("utf-8").replace("=", "")


def _encrypt_secret(plain_secret: str) -> str:
    """Obfuscate / encrypt secret using application key."""
    key = settings.JWT_SECRET_KEY.encode("utf-8")
    xor_bytes = bytes([b ^ key[i % len(key)] for i, b in enumerate(plain_secret.encode("utf-8"))])
    return base64.b64encode(xor_bytes).decode("utf-8")


def _decrypt_secret(encrypted_secret: str) -> str:
    """Decrypt secret using application key."""
    key = settings.JWT_SECRET_KEY.encode("utf-8")
    raw_bytes = base64.b64decode(encrypted_secret.encode("utf-8"))
    decrypted = bytes([b ^ key[i % len(key)] for i, b in enumerate(raw_bytes)])
    return decrypted.decode("utf-8")


def _generate_totp_code(secret_b32: str, for_time: Optional[int] = None, time_step: int = 30, digits: int = 6) -> str:
    """Pure Python implementation of RFC 6238 TOTP."""
    if for_time is None:
        for_time = int(time.time())

    counter = int(for_time // time_step)
    # Decode base32 secret (add padding if needed)
    missing_padding = len(secret_b32) % 8
    if missing_padding:
        secret_b32 += "=" * (8 - missing_padding)

    key = base64.b32decode(secret_b32, casefold=True)
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code_int = struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF
    code = code_int % (10 ** digits)
    return f"{code:0{digits}d}"


def _verify_totp(secret_b32: str, candidate_code: str, window: int = 1) -> bool:
    """Verify TOTP code with standard clock-drift window (±1 step = ±30s)."""
    now = int(time.time())
    candidate_clean = candidate_code.strip()
    for step_offset in range(-window, window + 1):
        test_time = now + (step_offset * 30)
        expected = _generate_totp_code(secret_b32, for_time=test_time)
        if hmac.compare_digest(expected, candidate_clean):
            return True
    return False


def _hash_backup_code(code: str) -> str:
    return hashlib.sha256(code.strip().lower().encode("utf-8")).hexdigest()


def setup_mfa(db: Session, user: User) -> Dict[str, Any]:
    """Initialize TOTP secret and single-use backup recovery codes for a user."""
    secret = _generate_base32_secret()
    secret_enc = _encrypt_secret(secret)

    # Generate 10 single-use 8-character recovery codes
    backup_codes_plain = [secrets.token_hex(4).upper() for _ in range(10)]
    backup_codes_hashed = [_hash_backup_code(c) for c in backup_codes_plain]

    stmt = select(MFACredential).where(MFACredential.user_id == user.id)
    cred = db.execute(stmt).scalars().first()
    now = datetime.now(timezone.utc)

    if cred is None:
        cred = MFACredential(
            user_id=user.id,
            secret_encrypted=secret_enc,
            is_enabled=False,
            backup_codes_json=backup_codes_hashed,
            created_at=now,
        )
        db.add(cred)
    else:
        cred.secret_encrypted = secret_enc
        cred.is_enabled = False
        cred.backup_codes_json = backup_codes_hashed

    db.commit()
    db.refresh(cred)

    otpauth_uri = f"otpauth://totp/MediGen:{user.email}?secret={secret}&issuer=MediGen%20AI&digits=6&period=30"
    return {
        "secret": secret,
        "otpauth_uri": otpauth_uri,
        "backup_codes": backup_codes_plain,
        "message": "Scan the QR code or enter the secret in your authenticator app, then verify a 6-digit code to enable MFA.",
    }


def enable_mfa(db: Session, user: User, code: str) -> bool:
    """Verify code and activate MFA for the user."""
    stmt = select(MFACredential).where(MFACredential.user_id == user.id)
    cred = db.execute(stmt).scalars().first()
    if not cred:
        return False

    secret_plain = _decrypt_secret(cred.secret_encrypted)
    if not _verify_totp(secret_plain, code):
        return False

    cred.is_enabled = True
    cred.last_used_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Enabled MFA for user_id=%d", user.id)
    return True


def verify_mfa_code(db: Session, user: User, code: str) -> Tuple[bool, str]:
    """Verify TOTP or burn a backup recovery code during authentication."""
    stmt = select(MFACredential).where(MFACredential.user_id == user.id)
    cred = db.execute(stmt).scalars().first()
    if not cred or not cred.is_enabled:
        return True, "MFA not enabled for user"

    clean_code = code.strip()

    # 1. Try TOTP code
    secret_plain = _decrypt_secret(cred.secret_encrypted)
    if _verify_totp(secret_plain, clean_code):
        cred.last_used_at = datetime.now(timezone.utc)
        db.commit()
        return True, "TOTP verification successful"

    # 2. Try Backup recovery code
    candidate_hash = _hash_backup_code(clean_code)
    current_hashes: List[str] = list(cred.backup_codes_json or [])
    if candidate_hash in current_hashes:
        current_hashes.remove(candidate_hash)
        cred.backup_codes_json = current_hashes
        cred.last_used_at = datetime.now(timezone.utc)
        db.commit()
        logger.warning("Burned backup recovery code for user_id=%d. Remaining: %d", user.id, len(current_hashes))
        return True, f"Backup recovery code accepted. {len(current_hashes)} backup code(s) remaining."

    return False, "Invalid TOTP code or backup recovery code"


def disable_mfa(db: Session, user: User, code: str) -> bool:
    """Disable MFA after verifying a valid code."""
    valid, _ = verify_mfa_code(db, user, code)
    if not valid:
        return False

    stmt = select(MFACredential).where(MFACredential.user_id == user.id)
    cred = db.execute(stmt).scalars().first()
    if cred:
        cred.is_enabled = False
        db.commit()
    logger.info("Disabled MFA for user_id=%d", user.id)
    return True


def get_mfa_status(db: Session, user: User) -> Dict[str, Any]:
    """Return user MFA status and remaining backup codes count."""
    stmt = select(MFACredential).where(MFACredential.user_id == user.id)
    cred = db.execute(stmt).scalars().first()
    if not cred:
        return {
            "is_enabled": False,
            "backup_codes_remaining": 0,
            "last_used_at": None,
        }

    return {
        "is_enabled": cred.is_enabled,
        "backup_codes_remaining": len(cred.backup_codes_json or []),
        "last_used_at": cred.last_used_at,
    }
