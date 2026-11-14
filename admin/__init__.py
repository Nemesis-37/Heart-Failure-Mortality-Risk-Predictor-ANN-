"""
admin/
======
Hospital Administrator Doctor Credential Verification.
"""

from admin.security import create_admin_token, verify_admin_token, get_current_admin

try:
    from admin.router import router as admin_router
except ImportError:
    admin_router = None

__all__ = ["create_admin_token", "verify_admin_token", "get_current_admin", "admin_router"]
