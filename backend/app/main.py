import os
import uuid
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
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:Robbo2004!@127.0.0.1:5432/case_advocates")
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key_change_in_production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI()
security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME", "robertsonroberts58@gmail.com"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD", ""),  # type: ignore
    MAIL_FROM=os.getenv("MAIL_FROM", "robertsonroberts58@gmail.com"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

fastmail = FastMail(conf)
RESET_TOKENS = {}

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
        if user_id is None or email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token payload.")
        return {"user_id": str(user_id), "email": str(email)}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Could not validate credentials.")

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
        first_name_val = request.first_name if request.first_name is not None else ""
        last_name_val = request.last_name if request.last_name is not None else ""
        role_val = request.role if request.role else "client"

        result = db.execute(
            text("""
                INSERT INTO users (email, password_hash, first_name, last_name, role) 
                VALUES (:email, :hash, :first_name, :last_name, :role) 
                RETURNING id
            """),
            {
                "email": request.email, 
                "hash": hashed_pw,
                "first_name": first_name_val,
                "last_name": last_name_val,
                "role": role_val
            }
        )
        
        new_user = result.fetchone()
        if not new_user:
            db.rollback()
            raise HTTPException(status_code=500, detail="User creation failed.")
            
        new_id = str(new_user[0])
        db.commit()
        access_token = create_access_token(data={"sub": request.email, "user_id": new_id})
        
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
async def login(request: LoginRequest):
    db = SessionLocal()
    try:
        user = db.execute(
            text("SELECT id, email, password_hash FROM users WHERE email = :email"),
            {"email": request.email}
        ).fetchone()

        if not user or not bcrypt.checkpw(request.password.encode('utf-8'), user.password_hash.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        access_token = create_access_token(data={"sub": user.email, "user_id": str(user.id)})
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": str(user.id),
            "email": user.email
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
            reset_url = f"http://127.0.0.1:8000/api/reset-password-verify?token={token}"
            
            html_content = f"<html><body><p>Reset password: <a href='{reset_url}'>Click here</a></p></body></html>"
            message = MessageSchema(
                subject="Password Reset - Robert Case & Partners",
                recipients=[request.email], # type: ignore
                body=html_content,
                subtype=MessageType.html
            )
            background_tasks.add_task(fastmail.send_message, message)
            
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

app.mount("/", StaticFiles(directory="../frontend", html=True), name="static")