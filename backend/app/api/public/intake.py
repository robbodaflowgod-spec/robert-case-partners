# app/api/public/intake.py
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.intake import ConsultationRequest
from app.schemas.intake import ConsultationCreate, ConsultationResponse

router = APIRouter(prefix="/intake", tags=["Public Intake"])

@router.post("/", response_model=ConsultationResponse, status_code=status.HTTP_201_CREATED)
def submit_consultation(payload: ConsultationCreate, db: Session = Depends(get_db)):
    """
    CLIENT SIDE: Public endpoint allowing potential clients to submit a case inquiry.
    Saves the data into the consultation queue for an internal conflict-of-interest check.
    """
    new_request = ConsultationRequest(
        full_name=payload.full_name,
        company_name=payload.company_name,
        email=payload.email,
        phone_number=payload.phone_number,
        preferred_practice_area_id=payload.preferred_practice_area_id,
        brief_summary=payload.brief_summary,
        status="pending"
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request