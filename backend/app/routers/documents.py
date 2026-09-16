import io
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from docxtpl import DocxTemplate

from app.database import SessionLocal

router = APIRouter(prefix="/documents", tags=["documents"])

# Locate template file safely across directory structures
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent.parent
ROOT_DIR = BACKEND_DIR.parent

POSSIBLE_PATHS = [
    ROOT_DIR / "templates" / "retainer_template.docx",
    BACKEND_DIR / "templates" / "retainer_template.docx",
    CURRENT_DIR / "templates" / "retainer_template.docx",
]

TEMPLATE_PATH = next((path for path in POSSIBLE_PATHS if path.exists()), None)

@router.get("/generate/{intake_id}", response_class=StreamingResponse)
def generate_retainer_by_id(intake_id: int):
    if not TEMPLATE_PATH:
        raise HTTPException(status_code=500, detail="Template file not found on server.")

    # 1. Fetch the existing intake record from PostgreSQL by ID
    db = SessionLocal()
    try:
        # Using SQLAlchemy text query matching your sync SessionLocal setup
        query = text("SELECT id, full_name, email, phone, service_required FROM intake_requests WHERE id = :id")
        result = db.execute(query, {"id": intake_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Intake record not found in database.")
        
        # Map database row fields to template context tags
        intake_data = {
            "full_name": result[1],           # full_name
            "email": result[2],               # email
            "phone": result[3],               # phone
            "service_type": result[4],        # service_required
            "service_required": result[4],    # support both template key variants
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Database query error: {e}")
        raise HTTPException(status_code=500, detail="Internal database error fetching record.")
    finally:
        db.close()

    # 2. Render the Word document template in memory
    try:
        doc = DocxTemplate(str(TEMPLATE_PATH))
        doc.render(intake_data)
    except Exception as e:
        print(f"Template rendering error: {e}")
        raise HTTPException(status_code=500, detail="Failed to render document template.")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    # 3. Stream the generated .docx file back to the browser for immediate download
    filename = f"Retainer_Agreement_{str(intake_data['full_name']).replace(' ', '_')}.docx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )