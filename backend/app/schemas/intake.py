# app/schemas/intake.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID
from typing import Optional

# --- Practice Area Schemas ---
class PracticeAreaBase(BaseModel):
    title: str = Field(..., max_length=150)
    slug: str = Field(..., max_length=150)
    description: str

class PracticeAreaResponse(PracticeAreaBase):
    id: int

    model_config = {"from_attributes": True}


# --- Consultation Request Schemas ---
# Client Side: Public intake entry contract
class ConsultationCreate(BaseModel):
    full_name: str = Field(..., max_length=200)
    company_name: Optional[str] = Field(None, max_length=200, description="Corporate entity for conflict checks")
    email: EmailStr
    phone_number: str = Field(..., max_length=20)
    preferred_practice_area_id: Optional[int] = None
    brief_summary: str = Field(..., min_length=10, description="Brief non-confidential factual overview")

# Admin Side: Updating request status during intake review
class ConsultationUpdateStatus(BaseModel):
    status: str = Field(..., description="pending, under_review, conflict_cleared, conflict_found, scheduled")
    review_notes: Optional[str] = None

# Comprehensive response payload displayed in internal admin list view
class ConsultationResponse(ConsultationCreate):
    id: UUID
    status: str
    reviewed_by_id: Optional[UUID] = None
    review_notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}