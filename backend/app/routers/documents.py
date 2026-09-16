import io
import os
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from docxtpl import DocxTemplate

from app.database import SessionLocal
# Import your actual SQLAlchemy intake model (adjust name if it's Intake or IntakeRequest)
try:
    from app.models import IntakeModel as Intake
except ImportError:
    try:
        from app.models import Intake
    except ImportError:
        Intake = None

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

    db = SessionLocal()
    try:
        # Use ORM query if model is available, avoiding raw table name mismatches
        record = None
        if Intake is not None:
            record = db.query(Intake).filter(Intake.id == intake_id).first()
        
        # Fallback to raw SQL checking both common table names if ORM isn't bound
        if not record:
            from sqlalchemy import text
            for table_name in ["intake_requests", "intakes", "intake"]:
                try:
                    res = db.execute(
                        text(f"SELECT id, full_name, email, phone, service_required FROM {table_name} WHERE id = :id"),
                        {"id": intake_id}
                    ).fetchone()
                    if res:
                        record = res
                        break
                except Exception:
                    continue

        if not record:
            raise HTTPException(status_code=404, detail=f"Intake record {intake_id} not found in database.")

        # Handle both ORM object attributes and raw SQL tuples/rows safely
        if hasattr(record, "full_name"):
            intake_data = {
                "full_name": record.full_name,
                "email": record.email,
                "phone": record.phone,
                "service_type": getattr(record, "service_required", getattr(record, "service_type", "General Legal")),
                "service_required": getattr(record, "service_required", "General Legal"),
            }
        else:
            intake_data = {
                "full_name": record[1],
                "email": record[2],
                "phone": record[3],
                "service_type": record[4] if len(record) > 4 else "General Legal",
                "service_required": record[4] if len(record) > 4 else "General Legal",
            }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Database query error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal database error: {str(e)}")
    finally:
        db.close()

    try:
        doc = DocxTemplate(str(TEMPLATE_PATH))
        doc.render(intake_data)
    except Exception as e:
        print(f"Template rendering error: {e}")
        raise HTTPException(status_code=500, detail="Failed to render document template.")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    filename = f"Retainer_Agreement_{str(intake_data['full_name']).replace(' ', '_')}.docx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )