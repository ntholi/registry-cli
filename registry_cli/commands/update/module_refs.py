import click
from sqlalchemy import select
from sqlalchemy.orm import Session

from registry_cli.models import Module, SemesterModule


def update_semester_module_refs(db: Session, dry_run: bool = False) -> None:
    """
    Verify semester_module module_id references point to valid modules.
    Since SemesterModule no longer has a code field (removing duplication with Module.code),
    this function now mainly checks for valid module references.

    Args:
        db: Database session
        dry_run: If True, only display what would be updated without making changes
    """
    try:
        semester_modules = db.query(SemesterModule).all()

        total_modules = len(semester_modules)
        no_module_count = 0
        valid_module_count = 0

        click.echo(f"Found {total_modules} semester modules to check.")

        for sem_module in semester_modules:
            # Check if module_id points to a valid module
            module = db.query(Module).filter(Module.id == sem_module.module_id).first()

            if not module:
                click.secho(
                    f"Semester module ID {sem_module.id} has invalid module_id {sem_module.module_id}",
                    fg="yellow",
                )
                no_module_count += 1
            else:
                click.echo(
                    f"Semester module ID {sem_module.id} correctly points to module ID {module.id} (code: {module.code})"
                )
                valid_module_count += 1

        if not dry_run:
            db.commit()
            click.secho(
                f"Successfully verified {valid_module_count} semester modules.",
                fg="green",
            )
        else:
            click.secho(
                f"Dry run: Verified {valid_module_count} semester modules.",
                fg="green",
            )

        click.echo(f"Total semester modules: {total_modules}")
        click.echo(f"Valid module references: {valid_module_count}")
        click.echo(f"Invalid module references: {no_module_count}")

    except Exception as e:
        if not dry_run:
            db.rollback()
        click.secho(f"Error verifying module references: {str(e)}", fg="red")
