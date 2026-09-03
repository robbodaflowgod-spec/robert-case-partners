# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from uuid import UUID
from typing import Optional

# Base properties shared across schemas
class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    phone_number: Optional[str] = Field(None, max_length=20)

# Input contract used during user registration/creation
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Raw password input")
    role: Optional[str] = Field("client", description="Roles: client, staff, partner, admin")

# Output contract returned via API responses (Safe data sharing)
class UserResponse(UserBase):
    id: UUID
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Configures Pydantic to read raw attributes from SQLAlchemy ORM records automatically
    model_config = {"from_attributes": True}

# Context contract for handling OAuth2 token validation payloads
class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    role: Optional[str] = None