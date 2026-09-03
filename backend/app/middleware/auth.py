# app/middleware/auth.py
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.user import TokenData

# Initialize the password encryption context using secure bcrypt hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Tells FastAPI where to extract the authorization bearer token in incoming request headers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/public/auth/login")


# --- PASSWORD UTILITIES ---

def hash_password(password: str) -> str:
    """Returns a secure, salted cryptographic hash of a raw string password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compares raw input text against a stored hash to confirm validation match."""
    return pwd_context.verify(plain_password, hashed_password)


# --- JWT TOKEN ENGINE ---

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a cryptographically signed JWT token for session state management."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Update token payload expiration key
    to_encode.update({"exp": expire})
    
    # Sign token with firm secret key using secure SHA-256 encryption
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


# --- AUTHORIZATION MIDDLEWARE ---

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Core dependency that decodes incoming session tokens, verifies integrity,
    and returns the active User object directly from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate identity credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode signature using firm private config values
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        # Pull raw tokens from payload dictionary array
        user_id_str = payload.get("sub")
        user_role = payload.get("role")
        
        # Explicit type validation guards to ensure parameters are genuine strings
        # This completely resolves VS Code's "Any | None is not assignable to str" type warnings
        if not isinstance(user_id_str, str) or not isinstance(user_role, str):
            raise credentials_exception
            
        token_data = TokenData(user_id=UUID(user_id_str), role=user_role)
    except (JWTError, ValueError):
        raise credentials_exception

   # Query matching account inside database to verify state integrity
    # By adding the ": Optional[User]" type annotation, VS Code immediately understands what properties are available
    user: Optional[User] = db.query(User).filter(User.id == token_data.user_id).first()
    
    # We add a clean check to ensure 'user' exists first.
    # If it does, we check bool(user.is_active) to satisfy Pylance's type checker.
    if user is None or not bool(user.is_active):
        raise credentials_exception
        
    return user


class RoleChecker:
    """
    Reusable security gatekeeper that dynamically restricts endpoint paths 
    based on custom administrative tier access requirements.
    """
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access Denied: Your account tier lacks adequate clearance parameters."
            )
        return current_user

# Global convenience shortcuts for endpoint dependency injections
require_staff_clearance = RoleChecker(["staff", "partner", "admin"])
require_partner_clearance = RoleChecker(["partner", "admin"])