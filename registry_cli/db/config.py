import os
import sqlite3
import sys

import click
from dotenv import load_dotenv
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

load_dotenv()

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


TIMEOUT_SECONDS = 120


def _register_hrana_exit(engine: Engine) -> None:
    """Exit program when HRANA WebSocket error occurs."""

    @event.listens_for(engine, "handle_error")
    def _exit_on_hrana(exc_ctx):
        err = getattr(exc_ctx, "original_exception", None)
        if isinstance(err, sqlite3.DatabaseError) and "HRANA_WEBSOCKET_ERROR" in str(
            err
        ):
            click.secho("Fatal HRANA WebSocket error detected. Exiting...", fg="red")
            sys.exit(1)


def get_engine(use_local: bool = True) -> Engine:
    print("Using local database" if use_local else "Using production database")
    if use_local:
        engine = create_engine(
            "sqlite:///local.db",
            connect_args={"check_same_thread": False, "timeout": TIMEOUT_SECONDS},
            echo=False,
            pool_pre_ping=True,
            poolclass=NullPool,
        )
        _register_hrana_exit(engine)
        return engine
    else:
        input("⚠️ Using Production database. Press Enter to continue...")
        if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
            url = f"{TURSO_DATABASE_URL}?authToken={TURSO_AUTH_TOKEN}"
            engine = create_engine(
                f"sqlite+{url}",
                connect_args={"check_same_thread": False, "timeout": TIMEOUT_SECONDS},
                echo=False,
                pool_pre_ping=True,
                poolclass=NullPool,
            )
            _register_hrana_exit(engine)
            return engine
        else:
            raise ValueError("TURSO_AUTH_TOKEN or TURSO_DATABASE_URL missing")
