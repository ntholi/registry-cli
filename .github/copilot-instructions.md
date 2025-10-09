# Registry CLI - Copilot Instructions

## Critical Rules

- **NEVER generate documentation files** - Do not create or update `.md`, `.txt`, or any documentation files
- **PowerShell v7 only** - All shell commands must be PowerShell v7 compatible (Windows environment)
- **Code only** - Focus on implementing features, fixing bugs, and writing code

## Architecture

CLI tool that scrapes student data from a legacy PHP web app (`https://cmslesotho.limkokwing.net/campus/registry`) and syncs to SQLite database (local or Turso cloud).

**Flow**: Web Scraper → Database Sync → CLI Commands

## Key Patterns

### Database Sessions

- Local: `sqlite:///../registry-web/local.db`
- Production: Turso via `TURSO_DATABASE_URL` + `TURSO_AUTH_TOKEN` env vars
- Get session: `db = get_db()` (most commands) or `get_db_session(use_local)` (parallel ops)

### Web Scraping

- Singleton `Browser` class with session persistence (`session.pkl`)
- Firefox/Selenium for initial auth (manual login required)
- All scrapers inherit `BaseScraper`, implement `scrape() -> List[Dict[str, Any]]`
- Built-in retry: 60 attempts with exponential backoff

### CLI Structure

```python
@cli.group()  # Groups: pull, push, approve, enroll, create, update, export, check, send
def command_group():
    pass

@command_group.command()
@click.argument/option
def command_name(args):
    db = get_db()
    command_function(db, args)  # In registry_cli/commands/<group>/<command>.py
```

### Data Operations

- **Pull**: Web → Database (scrape first, never trust DB as source)
- **Update**: Database → Web POST (include ALL form fields to avoid corruption)
- **Parallel**: Use `ThreadPoolExecutor`, one DB session per thread, JSON progress files

## Conventions

- Student numbers: Always `int` type (e.g., `std_no: int`)
- Terms: `YYYY-MM` format (e.g., "2025-02")
- Batch ops: Support `--file` option (uses `read_student_numbers_from_file()`)
- Long-running: Add `--reset` flag for progress clearing
- Errors: Use `click.secho()` with colors (red/yellow/green)

## Running Commands

```powershell
# Development
# Use this form for all CLI invocations in development and CI: explicitly run via Poetry
poetry run registry <<command>>

```

## Key Files

- `registry_cli/main.py` - CLI routing
- `registry_cli/browser.py` - Web session singleton
- `registry_cli/db/config.py` - Database config
- `registry_cli/models/__init__.py` - All SQLAlchemy models
- `registry_cli/grade_definitions.py` - Grade logic
