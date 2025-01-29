import click
from sqlalchemy.orm import Session

from registry_cli.commands.pull.student import student_pull
from registry_cli.models import SignUp, Student, User


def names_match(name1: str, name2: str) -> bool:
    parts1 = name1.lower().split()
    parts2 = name2.lower().split()
    for part in parts1:
        if part in parts2:
            return True
    return False


def approve_signups(db: Session) -> None:
    """Approve pending signups by pulling student data and verifying names."""

    data = db.query(SignUp).filter(SignUp.status == "pending").all()

    if not data:
        click.echo("No pending signups found.")
        return

    for signup in data:
        try:
            student_id = int(signup.std_no)
            student_pull(db, student_id)
            student = db.query(Student).filter(Student.std_no == student_id).first()

            if not student:
                click.echo(f"Failed to pull student data for {signup.std_no}")
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
                signup.message = "Name mismatch with student records"
                db.commit()
                click.echo(
                    f"Rejected signup for {signup.name} - name mismatch with student records"
                )

        except Exception as e:
            click.echo(f"Error processing signup {signup.std_no}: {str(e)}")
            continue
