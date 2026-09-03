# app/models/intake.py
import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class PracticeArea(Base):
    __tablename__ = "practice_areas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(150), nullable=False, unique=True)
    slug = Column(String(150), nullable=False, unique=True)
    description = Column(Text, nullable=False)

    # Relationships
    consultation_requests = relationship("ConsultationRequest", back_populates="practice_area")


class ConsultationRequest(Base):
    __tablename__ = "consultation_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(200), nullable=False, index=True)
    company_name = Column(String(200), nullable=True, index=True) # Essential for business conflict checks
    email = Column(String(150), nullable=False)
    phone_number = Column(String(20), nullable=False)
    
    preferred_practice_area_id = Column(Integer, ForeignKey("practice_areas.id", ondelete="SET NULL"), nullable=True)
    brief_summary = Column(Text, nullable=False)
    
    # Statuses: 'pending', 'under_review', 'conflict_cleared', 'conflict_found', 'scheduled'
    status = Column(String(50), default="pending", nullable=False)
    
    # Internal track: Which staff/partner reviewed this intake request
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    practice_area = relationship("PracticeArea", back_populates="consultation_requests")
    reviewer = relationship("User", back_populates="reviewed_consultations")