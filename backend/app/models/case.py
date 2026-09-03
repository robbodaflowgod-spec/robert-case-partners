# app/models/case.py
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class LegalCase(Base):
    __tablename__ = "legal_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number = Column(String(50), nullable=False, unique=True, index=True) # e.g., LSK/RC/2026/001
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    client_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lead_partner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Statuses: 'active', 'closed', 'archived'
    status = Column(String(50), default="active", nullable=False)
    
    opened_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    client = relationship("User", back_populates="client_cases", foreign_keys=[client_id])
    lead_partner = relationship("User", back_populates="led_cases", foreign_keys=[lead_partner_id])
    documents = relationship("CaseDocument", back_populates="legal_case", cascade="all, delete-orphan")


class CaseDocument(Base):
    __tablename__ = "case_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("legal_cases.id", ondelete="CASCADE"), nullable=False)
    uploaded_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    file_name = Column(String(255), nullable=False)
    file_url = Column(String(512), nullable=False) # Points to encrypted storage bucket
    file_size_bytes = Column(Integer, nullable=False)
    
    # Strict role security flag: if true, standard clients cannot see this in their dashboard portal
    is_internal_only = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    legal_case = relationship("LegalCase", back_populates="documents")