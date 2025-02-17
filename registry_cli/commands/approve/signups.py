import click
from sqlalchemy.orm import Session

from registry_cli.commands.pull.student import student_pull
from registry_cli.models import SignUp, Student, User


def names_match(name1: str, name2: str) -> bool:
    """
    Returns True if at least two words are common between the names.
    """
    return len(set(name1.lower().split()) & set(name2.lower().split())) >= 2


def approve_signups(db: Session) -> None:
    """Approve pending signups by pulling student data and verifying names."""

    data = db.query(SignUp).filter(SignUp.status == "pending").all()

    if not data:
        click.echo("No pending signups found.")
        return

    for i, signup in enumerate(data):
        print()
        print("-" * 30)
        print(f"{i}/{len(data)}] {signup.name} ({signup.std_no})")
        try:
            student_id = int(signup.std_no)

            student = db.query(Student).filter(Student.std_no == student_id).first()
            if not student:
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
                signup.message = "Student Number does not match provided name"
                db.commit()
                click.echo(
                    f"Rejected signup for {signup.name} - name mismatch with student records"
                )

        except Exception as e:
            click.echo(f"Error processing signup {signup.std_no}: {str(e)}")
            continue
