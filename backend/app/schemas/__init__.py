# app/schemas/__init__.py
from app.schemas.case import CaseDocumentResponse, LegalCaseCreate, LegalCaseResponse
from app.schemas.intake import (
    ConsultationCreate,
    ConsultationResponse,
    ConsultationUpdateStatus,
)
from app.schemas.user import TokenData, UserCreate, UserResponse

__all__ = [
    "UserCreate",
    "UserResponse",
    "TokenData",
    "ConsultationCreate",
    "ConsultationResponse",
    "ConsultationUpdateStatus",
    "LegalCaseCreate",
    "LegalCaseResponse",
    "CaseDocumentResponse",
]
