from datetime import datetime
from typing import Any, Dict, List

import click
from sqlalchemy.orm import Session

from registry_cli.models import Module
from registry_cli.scrapers.module import ModuleScraper


def module_pull(db: Session) -> None:
    """Pull all modules from the registry system and save them to the database."""
    try:
        # Scrape modules page by page
        scraper = ModuleScraper()
        total_modules = 0
        total_pages = 0

        # Process each page of modules as they are scraped
        for page_modules in scraper.scrape():
            total_pages += 1
            total_modules += len(page_modules)

            # Save modules from this page to database
            save_modules(db, page_modules)

            click.echo(f"Saved page {total_pages} with {len(page_modules)} modules")

        click.secho(
            f"Successfully pulled {total_modules} modules from {total_pages} pages.",
            fg="green",
        )
    except Exception as e:
        db.rollback()
        click.secho(f"Error pulling modules: {str(e)}", fg="red", err=True)


def save_modules(db: Session, modules: List[Dict[str, Any]]) -> None:
    """Save or update modules in the database.

    Args:
        db: Database session
        modules: List of module dictionaries with module data
    """
    total_created = 0
    total_updated = 0

    for module_data in modules:
        # Check if module already exists by ID
        module = db.query(Module).filter(Module.id == module_data["id"]).first()

        # Convert date string to timestamp
        try:
            date_obj = datetime.strptime(module_data["date_stamp"], "%Y-%m-%d")
            timestamp = int(date_obj.timestamp())
        except:
            # If date parsing fails, use current timestamp
            timestamp = int(datetime.now().timestamp())

        if module:
            # Update existing module
            module.code = module_data["code"]
            module.name = module_data["name"]
            module.status = module_data["status"]
            module.timestamp = timestamp
            total_updated += 1
        else:
            # Create new module
            module = Module(
                id=module_data["id"],
                code=module_data["code"],
                name=module_data["name"],
                status=module_data["status"],
                timestamp=timestamp,
            )
            db.add(module)
            total_created += 1

        # Commit in batches to avoid memory issues
        if (total_created + total_updated) % 50 == 0:
            try:
                db.commit()
                click.echo(
                    f"Progress: {total_created + total_updated} modules processed"
                )
            except Exception as e:
                db.rollback()
                click.secho(f"Error committing batch: {str(e)}", fg="red", err=True)

    # Final commit for remaining modules
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        click.secho(f"Error committing final batch: {str(e)}", fg="red", err=True)

    click.secho(
        f"Created {total_created} new modules and updated {total_updated} existing modules",
        fg="green",
    )
