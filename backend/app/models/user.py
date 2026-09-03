# app/models/user.py
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=True)
    
    # Roles: 'client', 'staff', 'partner', 'admin'
    role = Column(String(50), default="client", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    # Links a partner or staff member to the consultations they have manually reviewed
    reviewed_consultations = relationship("ConsultationRequest", back_populates="reviewer")
    
    # Links a client user to their active litigation/corporate cases
    client_cases = relationship("LegalCase", back_populates="client", foreign_keys="[LegalCase.client_id]")
    
    # Links a partner to the cases they are actively leading
    led_cases = relationship("LegalCase", back_populates="lead_partner", foreign_keys="[LegalCase.lead_partner_id]")