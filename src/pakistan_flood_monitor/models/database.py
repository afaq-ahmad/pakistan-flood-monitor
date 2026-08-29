from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from pakistan_flood_monitor.config import settings

# Use PostgreSQL if available, otherwise fallback to local SQLite for development/testing.
# The value is loaded through the canonical Settings object rather than the legacy
# ``app.config`` tree.
DATABASE_URL = settings.database_url

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
