"""
auth/security.py
================
Password hashing and verification using Argon2id.

Argon2id is the winner of the Password Hashing Competition (PHC) and is the
primary recommendation of OWASP and IETF RFC 9106 for credential protection.
It provides hybrid resistance against both side-channel attacks and GPU/ASIC
cracking.
"""

import logging

logger = logging.getLogger(__name__)

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    # OWASP recommended parameters for Argon2id:
    # time_cost: 2 iterations
    # memory_cost: 65536 KiB (64 MB)
    # parallelism: 1 thread
    # hash_len: 32 bytes
    _hasher = PasswordHasher(
        time_cost=2,
        memory_cost=65536,
        parallelism=1,
        hash_len=32,
    )
    _USING_NATIVE_ARGON2 = True

    def hash_password(plain_password: str) -> str:
        """Hash a plain text password using native Argon2id."""
        return _hasher.hash(plain_password)

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against an Argon2id hash."""
        try:
            return _hasher.verify(hashed_password, plain_password)
        except VerifyMismatchError:
            return False
        except Exception as exc:
            logger.warning(f"Password verification error: {exc}")
            return False

except ImportError:
    # Fallback to standard library PBKDF2 with SHA-256 (600,000 iterations)
    # if argon2-cffi has not yet been installed by pip.
    import hashlib
    import hmac
    import secrets

    _USING_NATIVE_ARGON2 = False
    logger.info("argon2-cffi not installed; using standard library fallback. Install argon2-cffi for native Argon2id.")

    def hash_password(plain_password: str) -> str:
        """Generate a secure salted hash (OWASP PBKDF2-SHA256 standard fallback)."""
        salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 600000
        )
        return f"$argon2id-fallback$v=19${salt}${key.hex()}"

    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against fallback hash."""
        if not hashed_password or not hashed_password.startswith("$argon2id-fallback$"):
            return False
        try:
            parts = hashed_password.split("$")
            salt = parts[3]
            expected_key = parts[4]
            key = hashlib.pbkdf2_hmac(
                "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 600000
            )
            return hmac.compare_digest(key.hex(), expected_key)
        except Exception:
            return False


def is_argon2_native() -> bool:
    """Return True if native argon2-cffi library is active."""
    return _USING_NATIVE_ARGON2
