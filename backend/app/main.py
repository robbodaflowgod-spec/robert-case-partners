import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from dotenv import load_dotenv
import bcrypt
import jwt
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import BaseModel, EmailStr, SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# --- Logging Setup for Render ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn.error")

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Robbo2004!@127.0.0.1:5432/case_advocates")
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key_change_in_production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Database engine configuration with connection pooling safeguards
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"prepare_threshold": None}
)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI(title="Robert Case & Partners API")

security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SMTP FastMail configuration
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", "robertsonroberts58@gmail.com"),
    MAIL_PASSWORD=SecretStr(os.getenv("MAIL_PASSWORD", "")),  # Must be a 16-character Gmail App Password
    MAIL_FROM=os.getenv("MAIL_FROM", "robertsonroberts58@gmail.com"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

fastmail = FastMail(conf)
RESET_TOKENS = {}


# --- Background Task Email Wrapper with Error Logging ---

async def send_email_background(message: MessageSchema):
    """Executes the mail dispatch and forces stdout logging for success/failure on Render."""
    recipients_str = ", ".join(str(r) for r in message.recipients) if message.recipients else "Unknown"
    logger.info(f"--- [EMAIL ATTEMPT] Dispatching message to: {recipients_str} ---")
    try:
        await fastmail.send_message(message)
        logger.info(f"--- [EMAIL SUCCESS] Delivered successfully to: {recipients_str} ---")
    except Exception as e:
        logger.error(
            f"--- [EMAIL ERROR] Failed to send email to {recipients_str}. Error details: {str(e)} ---", 
            exc_info=True
        )


# --- Pydantic Schemas ---

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    role: Optional[str] = "client"

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordSubmitRequest(BaseModel):
    token: str
    new_password: str

class IntakeRequest(BaseModel):
    full_name: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    service_required: Optional[str] = ""
    case_summary: Optional[str] = ""

class ReviewIntakeRequest(BaseModel):
    status: Optional[str] = "reviewed"
    meetup_date: Optional[str] = None


# --- Authentication Helpers ---

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        email = payload.get("sub")
        role = payload.get("role", "client")
        if user_id is None or email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token payload.")
        return {"user_id": str(user_id), "email": str(email), "role": str(role)}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Could not validate credentials.")

def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    role = current_user.get("role", "client")
    if role not in ["admin", "partner"]:
        raise HTTPException(status_code=403, detail="Access denied. Administrative privileges required.")
    return current_user


# --- API Routes ---

@app.post("/api/register")
async def register(request: RegisterRequest):
    db = SessionLocal()
    try:
        existing_user = db.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": request.email}
        ).fetchone()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="An account with this email already exists.")
            
        hashed_pw = bcrypt.hashpw(request.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        result = db.execute(
            text("""
                INSERT INTO users (email, password_hash, first_name, last_name, role) 
                VALUES (:email, :hash, :first_name, :last_name, :role) 
                RETURNING id
            """),
            {
                "email": request.email, 
                "hash": hashed_pw,
                "first_name": request.first_name or "",
                "last_name": request.last_name or "",
                "role": request.role or "client"
            }
        )
        
        new_user = result.fetchone()
        if not new_user:
            db.rollback()
            raise HTTPException(status_code=500, detail="User creation failed.")
            
        new_id = str(new_user[0])
        db.commit()
        access_token = create_access_token(data={"sub": request.email, "user_id": new_id, "role": request.role or "client"})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": new_id,
            "email": request.email
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database insertion error: {str(e)}")
    finally:
        db.close()

@app.post("/api/login")
async def login(credentials: LoginRequest):
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id, email, password_hash, role FROM users WHERE email = :email"),
            {"email": credentials.email}
        ).fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="Invalid email or password.")

        user_id, email, password_hash, role = user.id, user.email, user.password_hash, (user.role or "client")

        if not bcrypt.checkpw(credentials.password.encode('utf-8'), password_hash.encode('utf-8')):
            raise HTTPException(status_code=400, detail="Invalid email or password.")

        is_admin = role in ["admin", "partner"]
        access_token = create_access_token(data={"sub": email, "user_id": str(user_id), "role": role})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": role,
            "is_admin": is_admin
        }
    finally:
        db.close()

@app.post("/api/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks):
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id, email FROM users WHERE email = :email"),
            {"email": request.email}
        ).fetchone()
        
        if user:
            token = str(uuid.uuid4())
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
            RESET_TOKENS[token] = {"email": request.email, "expires_at": expires_at}
            reset_url = f"https://robert-case-partners.onrender.com/api/reset-password-verify?token={token}"
            
            html_content = f"<html><body><p>Reset password: <a href='{reset_url}'>Click here</a></p></body></html>"
            message = MessageSchema(
                subject="Password Reset - Robert Case & Partners",
                recipients=[request.email],
                body=html_content,
                subtype=MessageType.html
            )
            background_tasks.add_task(send_email_background, message)
            
        return {"message": "If the account exists, a link has been sent to your email."}
    finally:
        db.close()

@app.get("/api/reset-password-verify", response_class=HTMLResponse)
async def reset_password_page(token: str):
    token_data = RESET_TOKENS.get(token)
    if not token_data or datetime.now(timezone.utc) > token_data["expires_at"]:
        return HTMLResponse(content="<h2>Invalid or Expired Link</h2>", status_code=400)
    return HTMLResponse(content=f"<h2>Token Verified for {token_data['email']}</h2>")

@app.post("/api/reset-password-verify")
async def reset_password_submit(request: ResetPasswordSubmitRequest):
    token_data = RESET_TOKENS.get(request.token)
    if not token_data or datetime.now(timezone.utc) > token_data["expires_at"]:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    
    email = token_data["email"]
    hashed_pw = bcrypt.hashpw(request.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    db = SessionLocal()
    try:
        db.execute(text("UPDATE users SET password_hash = :hash WHERE email = :email"), {"hash": hashed_pw, "email": email})
        db.commit()
        del RESET_TOKENS[request.token]
        return {"message": "Password successfully reset."}
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error occurred.")
    finally:
        db.close()

@app.post("/api/intake", status_code=status.HTTP_201_CREATED)
async def create_intake(request: IntakeRequest):
    db = SessionLocal()
    try:
        db.execute(
            text("""
                INSERT INTO intake_requests (full_name, email, phone, service_required, case_summary)
                VALUES (:full_name, :email, :phone, :service_required, :case_summary)
            """),
            {
                "full_name": request.full_name,
                "email": request.email,
                "phone": request.phone,
                "service_required": request.service_required,
                "case_summary": request.case_summary
            }
        )
        db.commit()
        return {"status": "success", "success": True, "message": "Intake request submitted successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database execution error: {str(e)}")
    finally:
        db.close()

@app.get("/api/me")
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    return {"message": "Authenticated access granted", "user": current_user}

@app.get("/api/admin/intakes")
async def get_all_intakes(current_user: dict = Depends(get_current_admin_user)):
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT 
                    id, 
                    full_name, 
                    email, 
                    phone, 
                    service_required, 
                    case_summary, 
                    CASE 
                        WHEN EXISTS (
                            SELECT 1 FROM information_schema.columns 
                            WHERE table_name='intake_requests' AND column_name='status'
                        ) THEN COALESCE(status, 'pending')
                        ELSE 'pending'
                    END AS status,
                    created_at 
                FROM intake_requests 
                ORDER BY id DESC
            """)
        ).mappings().all()
        return [dict(row) for row in result]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")
    finally:
        db.close()

@app.patch("/api/admin/intakes/{intake_id}/review")
async def review_intake(
    intake_id: str,
    request: ReviewIntakeRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_admin_user)
):
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE intake_requests ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'pending'"))
        db.commit()

        result = db.execute(
            text("""
                UPDATE intake_requests 
                SET status = :status 
                WHERE id::text = :id 
                RETURNING id, full_name, email, service_required
            """),
            {"status": request.status or "reviewed", "id": intake_id}
        ).fetchone()

        if not result:
            db.rollback()
            raise HTTPException(status_code=404, detail="Intake request record not found.")

        db.commit()

        client_id, full_name, client_email, service_required = result.id, result.full_name, result.email, result.service_required

        if client_email:
            meetup_info = f"Proposed Physical Meetup Date/Time: <strong>{request.meetup_date}</strong>" if request.meetup_date else "We will contact you directly to finalize a physical consultation schedule."
            
            email_html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                    <h2 style="color: #0f172a;">Consultation Request Reviewed</h2>
                    <p>Dear <strong>{full_name or 'Client'}</strong>,</p>
                    <p>Your legal consultation request regarding <strong>{service_required or 'General Legal Consultation'}</strong> has been officially reviewed by our legal team at <strong>Robert Case & Partners Advocates</strong>.</p>
                    <div style="background-color: #f8fafc; padding: 15px; border-left: 4px solid #b45309; margin: 20px 0;">
                        <p style="margin: 0; font-weight: bold; color: #0f172a;">Next Steps:</p>
                        <p style="margin: 5px 0 0 0;">{meetup_info}</p>
                    </div>
                    <p>Please reply directly to this email or call our chambers to confirm or adjust your availability.</p>
                    <br>
                    <p>Kind regards,</p>
                    <p><strong>Robert Case & Partners Advocates</strong></p>
                </body>
            </html>
            """

            message = MessageSchema(
                subject="Consultation Request Reviewed - Robert Case & Partners",
                recipients=[client_email],
                body=email_html,
                subtype=MessageType.html
            )
            background_tasks.add_task(send_email_background, message)
        else:
            logger.warning(f"[REVIEW] Intake ID #{intake_id} has no email associated. Skipping notification.")

        return {
            "status": "success",
            "message": "Intake request marked as reviewed and client email queued.",
            "intake_id": str(client_id)
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update intake request: {str(e)}")
    finally:
        db.close()


# --- Static Files Mount ---

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

possible_paths = [
    os.path.join(BASE_DIR, "..", "..", "frontend"),  # Root /frontend
    os.path.join(BASE_DIR, "..", "frontend"),        # /backend/frontend
    os.path.join(BASE_DIR, "frontend"),              # /backend/app/frontend
    os.path.abspath("frontend"),                     # Current working directory /frontend
]

frontend_path = next((path for path in possible_paths if os.path.exists(path)), None)

if frontend_path:
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")