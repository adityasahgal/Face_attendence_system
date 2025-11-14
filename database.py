from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite database file
DATABASE_URL = "sqlite:///./attendance.db"

# Engine setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Session setup
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Dependency for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all tables if not exist."""
    from models import Student, Attendance
    Base.metadata.create_all(bind=engine)