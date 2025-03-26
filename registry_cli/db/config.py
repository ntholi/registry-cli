import os

import libsql_client
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

load_dotenv()

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


TIMEOUT_SECONDS = 120


def get_engine(use_local: bool = False) -> Engine:
    if use_local:
        return create_engine(
            "sqlite:///local.db",
            connect_args={"check_same_thread": False, "timeout": TIMEOUT_SECONDS},
            echo=False,
        )
    else:
        input("⚠️ Using Production database. Press Enter to continue...")
        if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
            url = f"{TURSO_DATABASE_URL}?authToken={TURSO_AUTH_TOKEN}"
            return create_engine(
                f"sqlite+{url}",
                connect_args={"check_same_thread": False, "timeout": TIMEOUT_SECONDS},
                echo=False,
            )
        else:
            raise ValueError("TURSO_AUTH_TOKEN or TURSO_DATABASE_URL missing")
