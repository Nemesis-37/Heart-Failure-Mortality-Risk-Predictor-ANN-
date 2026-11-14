"""
auth/validation.py
==================
Input validations for Doctor registration.
"""

import re
from fastapi import HTTPException, status


def validate_doctor_fields(
    full_name: str,
    email: str,
    mobile: str,
    medical_degree: str,
    registration_number: str,
    registration_council: str,
    password: str,
    confirm_password: str,
) -> str:
    """
    Validate all required registration fields and password complexity.
    Returns cleaned, normalized email address upon success.
    """
    if not full_name or len(full_name.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name must be at least 3 characters long.",
        )

    clean_email = email.strip().lower()
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", clean_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format. Please provide a valid professional email.",
        )

    if not mobile or len(mobile.strip()) < 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid contact number (minimum 7 digits).",
        )

    if not medical_degree or len(medical_degree.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please specify your medical qualification/degree.",
        )

    if not registration_number or len(registration_number.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid medical council registration number.",
        )

    if not registration_council or len(registration_council.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please specify the issuing medical council or licensing authority.",
        )

    if password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match. Please verify your password entry.",
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter (A-Z).",
        )
    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter (a-z).",
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one digit (0-9).",
        )

    return clean_email
