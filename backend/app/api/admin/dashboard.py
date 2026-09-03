# app/api/admin/dashboard.py
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.intake import ConsultationRequest
from app.models.user import User
from app.schemas.intake import ConsultationResponse, ConsultationUpdateStatus
from app.middleware.auth import require_staff_clearance

router = APIRouter(prefix="/dashboard", tags=["Admin Dashboard"])

@router.get("/consultations", response_model=List[ConsultationResponse])
def get_all_consultation_requests(
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_staff_clearance)
):
    """
    ADMIN SIDE: Retrieves the comprehensive queue of incoming legal inquiries.
    Protected strictly: Only accessible by authenticated firm staff.
    """
    requests = db.query(ConsultationRequest).order_by(ConsultationRequest.created_at.desc()).all()
    return requests


@router.patch("/consultations/{request_id}", response_model=ConsultationResponse)
def update_consultation_status(
    request_id: UUID,
    payload: ConsultationUpdateStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff_clearance)
):
    """
    ADMIN SIDE: Updates a consultation intake record status following internal verification profiling.
    Uses bulk-query execution statements to completely clear editor type-checking limits.
    """
    # 1. Fetch the raw query execution builder template
    query = db.query(ConsultationRequest).filter(ConsultationRequest.id == request_id)
    request_record = query.first()
    
    if not request_record:
        raise HTTPException(status_code=404, detail="Consultation request file not found.")

    # 2. Extract incoming values into a clean parameter dictionary payload
    update_data = {
        ConsultationRequest.status: str(payload.status),
        ConsultationRequest.review_notes: str(payload.review_notes) if payload.review_notes else None,
        ConsultationRequest.reviewed_by_id: current_user.id
    }

    # 3. Apply changes via mass query statement instead of mutable class variables
    # This completely satisfies Pylance, clearing the "Cannot assign to attribute" warning.
    query.update(update_data, synchronize_session="fetch")

    db.commit()
    db.refresh(request_record)
    return request_record