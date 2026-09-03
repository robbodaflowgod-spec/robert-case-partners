# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# 1. Create the SQLAlchemy Engine
# Fixed: Changed 'create_backend' to the correct 'create_engine' function
engine = create_engine(
    settings.DATABASE_URL,
    # pool_pre_ping checks if the connection is still alive before executing queries.
    pool_pre_ping=True 
)

# 2. Create a Session Local Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Establish the Declarative Base
Base = declarative_base()

# 4. Dependency Injection Provider
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
