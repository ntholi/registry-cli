import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")

if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
    raise ValueError("TURSO_DATABASE_URL and TURSO_AUTH_TOKEN must be set in .env file")

# Create SQLAlchemy engine with proper Turso configuration
url = f"{TURSO_DATABASE_URL}?authToken={TURSO_AUTH_TOKEN}"
engine = create_engine(
    f"sqlite+{url}", connect_args={"check_same_thread": False}, echo=True
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()
