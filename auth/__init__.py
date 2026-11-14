"""
auth/
=====
Physician authentication, registration, and security.
"""

from auth.security import hash_password, verify_password, is_argon2_native

try:
    from auth.router import router as auth_router
except ImportError:
    auth_router = None

__all__ = ["hash_password", "verify_password", "is_argon2_native", "auth_router"]
