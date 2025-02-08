import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv()

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


def get_engine() -> Engine:
    if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
        url = f"{TURSO_DATABASE_URL}?authToken={TURSO_AUTH_TOKEN}"
        return create_engine(
            f"sqlite+{url}",
            connect_args={"check_same_thread": False, "timeout": 30},
            echo=False,
        )
    else:
        raise ValueError("TURSO_AUTH_TOKEN or TURSO_DATABASE_URL missing")


engine = get_engine()
