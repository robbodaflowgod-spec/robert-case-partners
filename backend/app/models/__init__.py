# app/models/__init__.py
from app.database import Base
from app.models.case import CaseDocument, LegalCase
from app.models.intake import ConsultationRequest, PracticeArea
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "PracticeArea",
    "ConsultationRequest",
    "LegalCase",
    "CaseDocument",
]
