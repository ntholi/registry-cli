import click
from sqlalchemy.orm import Session

from registry_cli.commands.pull.student import student_pull
from registry_cli.models import SignUp, Student, User


def names_match(name1: str, name2: str) -> bool:
    """
    Returns True if at least two words are common between the names.
    """
    if name1.lower() == name2.lower():
        return True
    return len(set(name1.lower().split()) & set(name2.lower().split())) >= 2


def approve_signups(db: Session) -> None:
    """Approve pending signups by pulling student data and verifying names."""

    data = db.query(SignUp).filter(SignUp.status == "pending").all()

    if not data:
        click.secho("No pending signups found.", fg="red")
        return

    for i, signup in enumerate(data):
        print()
        print("-" * 30)
        print(f"{i+1}/{len(data)}] {signup.name} ({signup.std_no})")
        try:
            student_id = int(signup.std_no)

            existing_student = (
                db.query(Student)
                .filter(
                    Student.std_no == student_id,
                    Student.user_id != None,
                    Student.user_id != signup.user_id,
                )
                .first()
            )

            if existing_student and existing_student.user:
                signup.status = "rejected"
                signup.message = f"Student number already linked to user: {existing_student.user.email}"
                db.commit()
                click.secho(
                    f"Rejected signup for {signup.name} - student number already linked to user: {existing_student.user.email}",
                    fg="red",
                )
                continue

            student = db.query(Student).filter(Student.std_no == student_id).first()
            if not student:
                passed = student_pull(db, student_id)
                if not passed:
                    click.secho(
                        f"Failed to pull student data for {signup.std_no}", fg="red"
                    )
                    signup.status = "rejected"
                    signup.message = (
                        "Error while syncing student data, resubmit your request later"
                    )
                    db.commit()
                    continue
                student = db.query(Student).filter(Student.std_no == student_id).first()
                if not student:
                    click.secho(
                        f"Student data pulled but not found in database for {signup.std_no}",
                        fg="red",
                    )
                    continue

            if names_match(student.name, signup.name):
                user = db.query(User).filter(User.id == signup.user_id).first()
                if user:
                    user.role = "student"
                    student.user_id = user.id
                    signup.status = "approved"
                    signup.message = "Signup approved"
                    db.commit()
                    click.echo(f"Approved signup for {student.name} ({student.std_no})")
            else:
                signup.status = "rejected"
                signup.message = "Student number does not match provided name"
                db.commit()
                click.secho(
                    f"Rejected signup for {signup.name} - name mismatch with student records",
                    fg="red",
                )

        except Exception as e:
            click.secho(f"Error processing signup {signup.std_no}: {str(e)}", fg="red")
            try:
                student_id = int(signup.std_no)
                student = db.query(Student).filter(Student.std_no == student_id).first()
                if student:
                    click.secho(
                        f"Deleting student record for {student.name} ({student.std_no})",
                        fg="yellow",
                    )
                    db.delete(student)
                    db.commit()
                    click.secho(f"Student record deleted successfully", fg="green")
            except Exception as delete_error:
                click.secho(f"Failed to delete student: {str(delete_error)}", fg="red")
                db.rollback()
            continue
