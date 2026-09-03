# app/api/admin/conflict.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.case import LegalCase
from app.models.intake import ConsultationRequest
from app.models.user import User
from app.middleware.auth import require_staff_clearance

router = APIRouter(prefix="/conflict-screening", tags=["Admin Conflict Screening"])

@router.get("/")
def check_conflicts(query: str, db: Session = Depends(get_db), current_user: User = Depends(require_staff_clearance)):
    """
    ADMIN COMPLIANCE ENGINE: Explicit lookup utility checking against existing 
    case files and corporate entities to prevent representing opposing forces.
    """
    search_term = f"%{query}%"
    
    # 1. Search existing legal cases for identical titles or descriptions
    case_matches = db.query(LegalCase).filter(
        (LegalCase.title.ilike(search_term)) | (LegalCase.case_number.ilike(search_term))
    ).all()
    
    # 2. Search client directory for matching individuals or corporations
    client_matches = db.query(User).filter(
        (User.role == "client") & 
        ((User.first_name.ilike(search_term)) | (User.last_name.ilike(search_term)))
    ).all()

    return {
        "queried_parameter": query,
        "conflicts_detected": len(case_matches) > 0 or len(client_matches) > 0,
        "matched_historical_cases": [
            {"id": c.id, "case_number": c.case_number, "title": c.title, "status": c.status} for c in case_matches
        ],
        "matched_existing_clients": [
            {"id": u.id, "name": f"{u.first_name} {u.last_name}", "email": u.email} for u in client_matches
        ]
    }