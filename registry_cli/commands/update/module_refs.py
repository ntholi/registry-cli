import click
from sqlalchemy import select
from sqlalchemy.orm import Session

from registry_cli.models import Module, SemesterModule


def update_semester_module_refs(db: Session, dry_run: bool = False) -> None:
    """
    Update semester_module module_id references by finding the corresponding module
    by code and assigning the correct module_id.

    Args:
        db: Database session
        dry_run: If True, only display what would be updated without making changes
    """
    try:
        semester_modules = db.query(SemesterModule).all()

        total_modules = len(semester_modules)
        updated_count = 0
        not_found_count = 0
        already_correct_count = 0

        click.echo(f"Found {total_modules} semester modules to check.")

        for sem_module in semester_modules:
            if not hasattr(sem_module, "code") or not sem_module.code:
                click.secho(
                    f"Semester module ID {sem_module.id} has no code to search with.",
                    fg="yellow",
                )
                not_found_count += 1
                continue

            correct_module = (
                db.query(Module).filter(Module.code == sem_module.code.strip()).first()
            )

            if not correct_module:
                click.secho(
                    f"No module found with code '{sem_module.code}' for semester module ID {sem_module.id}",
                    fg="yellow",
                )
                not_found_count += 1
                continue

            if sem_module.module_id == correct_module.id:
                click.echo(
                    f"Semester module ID {sem_module.id} already has correct module_id {correct_module.id} (code: {sem_module.code})"
                )
                already_correct_count += 1
                continue

            old_module_id = sem_module.module_id
            if not dry_run:
                sem_module.module_id = correct_module.id
                click.echo(
                    f"Updated semester module ID {sem_module.id}: module_id {old_module_id} -> {correct_module.id} (code: {sem_module.code})"
                )
            else:
                click.echo(
                    f"Would update semester module ID {sem_module.id}: module_id {old_module_id} -> {correct_module.id} (code: {sem_module.code})"
                )
            updated_count += 1

        if not dry_run:
            db.commit()
            click.secho(
                f"Successfully updated module references for {updated_count} semester modules.",
                fg="green",
            )
        else:
            click.secho(
                f"Dry run: Would have updated {updated_count} semester modules.",
                fg="green",
            )

        click.echo(f"Total semester modules: {total_modules}")
        click.echo(f"Already correct: {already_correct_count}")
        click.echo(f"Updated: {updated_count}")
        click.echo(f"Not found/could not update: {not_found_count}")

    except Exception as e:
        if not dry_run:
            db.rollback()
        click.secho(f"Error updating module references: {str(e)}", fg="red")