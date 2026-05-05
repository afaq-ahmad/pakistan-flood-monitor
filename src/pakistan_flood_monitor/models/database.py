import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use PostgreSQL if available, otherwise fallback to local SQLite for development testing
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./storage/pakistan_flood_monitor.db")

# For SQLite, we need connect_args to avoid thread issues. For Postgres, we don't.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
