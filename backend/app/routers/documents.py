import io
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi_mail import FastMail, MessageSchema, MessageType
from pydantic import BaseModel, EmailStr
from docxtpl import DocxTemplate
from sqlalchemy import text

# Import cleanly from independent config and database files
from app.database import SessionLocal
from app.email_config import conf

router = APIRouter(prefix="/documents", tags=["documents"])

# Locate template file
CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent.parent
ROOT_DIR = BACKEND_DIR.parent

POSSIBLE_PATHS = [
    ROOT_DIR / "templates" / "retainer_template.docx",
    BACKEND_DIR / "templates" / "retainer_template.docx",
    CURRENT_DIR / "templates" / "retainer_template.docx",
]

TEMPLATE_PATH = next((path for path in POSSIBLE_PATHS if path.exists()), None)

class RetainerPayload(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    service_type: str

async def send_advocate_retainer_email(payload: RetainerPayload, doc_buffer: bytes):
    """Sends the generated retainer as an email attachment to the advocates' inbox."""
    fastmail = FastMail(conf)
    
    filename = f"retainer_{payload.full_name.replace(' ', '_').lower()}.docx"
    
    email_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>New Retainer Request Generated</h2>
        <p>A new client retainer agreement has been generated via the firm portal.</p>
        <ul>
          <li><strong>Client Name:</strong> {payload.full_name}</li>
          <li><strong>Email:</strong> {payload.email}</li>
          <li><strong>Phone:</strong> {payload.phone}</li>
          <li><strong>Service Type:</strong> {payload.service_type}</li>
        </ul>
        <p>The generated Word document is attached to this email for advocate review.</p>
      </body>
    </html>
    """

    message = MessageSchema(
        subject=f"New Retainer Agreement: {payload.full_name}",
        recipients=["robertsonroberts58@gmail.com"],  # Firm/Advocate email address
        body=email_html,
        subtype=MessageType.html,
        attachments=[{
            "file": doc_buffer,
            "filename": filename,
            "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        }]
    )
    
    try:
        await fastmail.send_message(message)
    except Exception as e:
        print(f"Failed to email advocate copy: {e}")

@router.post("/generate-retainer", response_class=StreamingResponse)
async def generate_retainer(payload: RetainerPayload, background_tasks: BackgroundTasks):
    if not TEMPLATE_PATH:
        raise HTTPException(status_code=500, detail="Template file not found.")

    # 1. Render the document in memory
    doc = DocxTemplate(str(TEMPLATE_PATH))
    doc.render(payload.model_dump())

    buffer = io.BytesIO()
    doc.save(buffer)
    doc_bytes = buffer.getvalue()
    buffer.seek(0)

    # 2. Save intake record to Database (PostgreSQL)
    db = SessionLocal()
    try:
        db.execute(
            text("""
                INSERT INTO intake_requests (full_name, email, phone, service_required)
                VALUES (:full_name, :email, :phone, :service_type)
            """),
            {
                "full_name": payload.full_name,
                "email": payload.email,
                "phone": payload.phone,
                "service_type": payload.service_type,
            }
        )
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Database save error: {e}")
    finally:
        db.close()

    # 3. Queue background email task to notify Advocates' inbox
    background_tasks.add_task(send_advocate_retainer_email, payload, doc_bytes)

    # 4. Stream response to browser for immediate file download
    filename = f"retainer_{payload.full_name.replace(' ', '_').lower()}.docx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )# trigger deployment