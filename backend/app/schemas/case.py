# app/schemas/case.py
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional

# --- Case Document Schemas ---
class CaseDocumentBase(BaseModel):
    file_name: str = Field(..., max_length=255)
    is_internal_only: Optional[bool] = True

class CaseDocumentCreate(CaseDocumentBase):
    case_id: UUID
    file_url: str = Field(..., max_length=512)
    file_size_bytes: int

class CaseDocumentResponse(CaseDocumentBase):
    id: UUID
    file_url: str
    file_size_bytes: int
    uploaded_by_id: Optional[UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Legal Case Schemas ---
class LegalCaseBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    status: Optional[str] = "active" # active, closed, archived

class LegalCaseCreate(LegalCaseBase):
    case_number: str = Field(..., max_length=50)
    client_id: UUID
    lead_partner_id: Optional[UUID] = None

class LegalCaseUpdate(LegalCaseBase):
    lead_partner_id: Optional[UUID] = None
    closed_at: Optional[datetime] = None

class LegalCaseResponse(LegalCaseBase):
    id: UUID
    case_number: str
    client_id: UUID
    lead_partner_id: Optional[UUID] = None
    opened_at: datetime
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}