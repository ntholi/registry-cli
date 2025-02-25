from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


UserRole = Literal["admin", "student"]


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[Optional[str]] = mapped_column(String)
    role: Mapped[UserRole] = mapped_column(String, default="student", nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True)
    email_verified: Mapped[Optional[datetime]] = mapped_column(DateTime)
    image: Mapped[Optional[str]] = mapped_column(String)

    accounts: Mapped[list["Account"]] = relationship(
        back_populates="user", cascade="all, delete"
    )
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete"
    )
    authenticators: Mapped[list["Authenticator"]] = relationship(
        back_populates="user", cascade="all, delete"
    )
    student: Mapped[Optional["Student"]] = relationship(back_populates="user")

    def __repr__(self) -> str:
        return f"<User id={self.id!r} name={self.name!r} role={self.role!r} email={self.email!r}>"


class Account(Base):
    __tablename__ = "accounts"

    provider: Mapped[str] = mapped_column(String, primary_key=True)
    provider_account_id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="cascade"), nullable=False
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    refresh_token: Mapped[Optional[str]] = mapped_column(String)
    access_token: Mapped[Optional[str]] = mapped_column(String)
    expires_at: Mapped[Optional[int]] = mapped_column(Integer)
    token_type: Mapped[Optional[str]] = mapped_column(String)
    scope: Mapped[Optional[str]] = mapped_column(String)
    id_token: Mapped[Optional[str]] = mapped_column(String)
    session_state: Mapped[Optional[str]] = mapped_column(String)

    user: Mapped["User"] = relationship(back_populates="accounts")

    def __repr__(self) -> str:
        return (
            f"<Account provider={self.provider!r} provider_account_id={self.provider_account_id!r} "
            f"type={self.type!r} user_id={self.user_id!r}>"
        )


class Session(Base):
    __tablename__ = "sessions"

    session_token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="cascade"), nullable=False
    )
    expires: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship(back_populates="sessions")

    def __repr__(self) -> str:
        return (
            f"<Session session_token={self.session_token!r} user_id={self.user_id!r} "
            f"expires={self.expires!r}>"
        )


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    identifier: Mapped[str] = mapped_column(String, primary_key=True)
    token: Mapped[str] = mapped_column(String, primary_key=True)
    expires: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<VerificationToken identifier={self.identifier!r} token={self.token!r}>"
        )


class Authenticator(Base):
    __tablename__ = "authenticators"

    credential_id: Mapped[str] = mapped_column(String, unique=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="cascade"), primary_key=True
    )
    provider_account_id: Mapped[str] = mapped_column(String, nullable=False)
    credential_public_key: Mapped[str] = mapped_column(String, nullable=False)
    counter: Mapped[int] = mapped_column(Integer, nullable=False)
    credential_device_type: Mapped[str] = mapped_column(String, nullable=False)
    credential_backed_up: Mapped[bool] = mapped_column(Boolean, nullable=False)
    transports: Mapped[Optional[str]] = mapped_column(String)

    user: Mapped["User"] = relationship(back_populates="authenticators")
    __table_args__ = (
        UniqueConstraint("user_id", "credential_id", name="authenticators_pk"),
    )

    def __repr__(self) -> str:
        return (
            f"<Authenticator user_id={self.user_id!r} credential_id={self.credential_id!r} "
            f"provider_account_id={self.provider_account_id!r}>"
        )


SignUpStatus = Literal["pending", "approved", "rejected"]


class SignUp(Base):
    __tablename__ = "signups"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="cascade"), primary_key=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    std_no: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[SignUpStatus] = mapped_column(
        String, nullable=False, default="pending"
    )
    message: Mapped[Optional[str]] = mapped_column(String, default="Pending approval")
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<SignUp user_id={self.user_id!r} name={self.name!r} std_no={self.std_no!r} "
            f"status={self.status!r}>"
        )


Gender = Literal["Male", "Female", "Other"]
MaritalStatus = Literal["Single", "Married", "Divorced", "Windowed"]


class Student(Base):
    __tablename__ = "students"

    std_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    national_id: Mapped[str] = mapped_column(String, nullable=False)
    sem: Mapped[int] = mapped_column(Integer, nullable=False)
    date_of_birth: Mapped[datetime] = mapped_column(DateTime)
    phone1: Mapped[Optional[str]] = mapped_column(String)
    phone2: Mapped[Optional[str]] = mapped_column(String)
    gender: Mapped[Gender] = mapped_column(String)
    marital_status: Mapped[MaritalStatus] = mapped_column(String)
    religion: Mapped[Optional[str]] = mapped_column(String)
    structure_id: Mapped[Optional[int]] = mapped_column(ForeignKey("structures.id"))
    user_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    structure: Mapped[Optional["Structure"]] = relationship(back_populates="students")
    user: Mapped[Optional["User"]] = relationship(back_populates="student")
    programs: Mapped[list["StudentProgram"]] = relationship(
        back_populates="student", cascade="all, delete"
    )

    def __repr__(self) -> str:
        return f"<Student std_no={self.std_no!r} name={self.name!r} national_id={self.national_id!r}>"


ProgramStatus = Literal["Active", "Changed", "Completed", "Deleted", "Inactive"]


class StudentProgram(Base):
    __tablename__ = "student_programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    std_no: Mapped[int] = mapped_column(
        ForeignKey("students.std_no", ondelete="cascade"), nullable=False
    )
    start_term: Mapped[Optional[str]] = mapped_column(String)
    structure_id: Mapped[int] = mapped_column(
        ForeignKey("structures.id", ondelete="cascade"), nullable=False
    )
    stream: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[ProgramStatus] = mapped_column(String, nullable=False)
    assist_provider: Mapped[Optional[str]] = mapped_column(String)

    semesters: Mapped[list["StudentSemester"]] = relationship(
        back_populates="program", cascade="all, delete"
    )
    student: Mapped["Student"] = relationship(back_populates="programs")

    def __repr__(self) -> str:
        return f"<StudentProgram id={self.id!r} std_no={self.std_no!r} status={self.status!r}>"


SemesterStatus = Literal[
    "Active",
    "Deferred",
    "Deleted",
    "DNR",
    "DroppedOut",
    "Enrolled",
    "Exempted",
    "Inactive",
    "Repeat",
]


class StudentSemester(Base):
    __tablename__ = "student_semesters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[SemesterStatus] = mapped_column(String, nullable=False)
    semester_number: Mapped[int] = mapped_column(Integer)
    student_program_id: Mapped[int] = mapped_column(
        ForeignKey("student_programs.id", ondelete="cascade"), nullable=False
    )

    program: Mapped["StudentProgram"] = relationship(back_populates="semesters")
    modules: Mapped[list["StudentModule"]] = relationship(
        back_populates="semester", cascade="all, delete"
    )

    def __repr__(self) -> str:
        return (
            f"<StudentSemester id={self.id!r} term={self.term!r} status={self.status!r} "
            f"semester_number={self.semester_number!r}>"
        )


ModuleType = Literal["Major", "Minor", "Core"]
ModuleStatus = Literal[
    "Add",
    "Compulsory",
    "Delete",
    "Drop",
    "Exempted",
    "Ineligible",
    "Repeat1",
    "Repeat2",
    "Repeat3",
    "Repeat4",
    "Repeat5",
    "Repeat6",
    "Repeat7",
    "Resit1",
    "Resit2",
    "Resit3",
    "Resit4",
    "Supplementary",
]


class StudentModule(Base):
    __tablename__ = "student_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="cascade"), nullable=False
    )
    status: Mapped[ModuleStatus] = mapped_column(String, nullable=False)
    marks: Mapped[str] = mapped_column(String, nullable=False)
    grade: Mapped[str] = mapped_column(String, nullable=False)
    student_semester_id: Mapped[int] = mapped_column(
        ForeignKey("student_semesters.id", ondelete="cascade"), nullable=False
    )

    semester: Mapped["StudentSemester"] = relationship(back_populates="modules")

    def __repr__(self) -> str:
        return (
            f"<StudentModule id={self.id!r} module_id={self.module_id!r} status={self.status!r} "
            f"marks={self.marks!r} grade={self.grade!r}>"
        )


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    programs: Mapped[list["Program"]] = relationship(back_populates="school")

    def __repr__(self) -> str:
        return f"<School id={self.id!r} code={self.code!r} name={self.name!r}>"


ProgramLevel = Literal["certificate", "diploma", "degree"]


class Program(Base):
    __tablename__ = "programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    level: Mapped[ProgramLevel] = mapped_column(String, nullable=False)

    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    school: Mapped["School"] = relationship(back_populates="programs")

    structures: Mapped[list["Structure"]] = relationship(back_populates="program")

    def __repr__(self) -> str:
        return (
            f"<Program id={self.id!r} code={self.code!r} name={self.name!r} "
            f"level={self.level!r}>"
        )


class Structure(Base):
    __tablename__ = "structures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("programs.id"), nullable=False)
    program: Mapped["Program"] = relationship(back_populates="structures")
    students: Mapped[list["Student"]] = relationship(back_populates="structure")
    semesters: Mapped[list["StructureSemester"]] = relationship(
        back_populates="structure"
    )

    def __repr__(self) -> str:
        return f"<Structure id={self.id!r} code={self.code!r} program_id={self.program_id!r}>"


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[ModuleType] = mapped_column(String, nullable=False)
    credits: Mapped[float] = mapped_column(Float, nullable=False)
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("structure_semesters.id"), nullable=False
    )
    semester: Mapped["StructureSemester"] = relationship(
        back_populates="semester_modules", foreign_keys=[semester_id]
    )
    prerequisites: Mapped[list["ModulePrerequisite"]] = relationship(
        back_populates="module",
        foreign_keys="[ModulePrerequisite.module_id]",
        cascade="all, delete",
    )
    is_prerequisite_for: Mapped[list["ModulePrerequisite"]] = relationship(
        back_populates="prerequisite",
        foreign_keys="[ModulePrerequisite.prerequisite_id]",
        cascade="all, delete",
    )

    def __repr__(self) -> str:
        return (
            f"<Module id={self.id!r} code={self.code!r} name={self.name!r} "
            f"type={self.type!r} credits={self.credits!r}>"
        )


class ModulePrerequisite(Base):
    __tablename__ = "module_prerequisites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="cascade"), nullable=False
    )
    prerequisite_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="cascade"), nullable=False
    )

    module: Mapped["Module"] = relationship(
        "Module", foreign_keys=[module_id], back_populates="prerequisites"
    )
    prerequisite: Mapped["Module"] = relationship(
        "Module", foreign_keys=[prerequisite_id], back_populates="is_prerequisite_for"
    )

    __table_args__ = (
        UniqueConstraint(
            "module_id",
            "prerequisite_id",
            name="unique_module_prerequisite",
        ),
    )

    def __repr__(self) -> str:
        return f"<ModulePrerequisite id={self.id!r} module_id={self.module_id!r} prerequisite_id={self.prerequisite_id!r}>"


class StructureSemester(Base):
    __tablename__ = "structure_semesters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    structure_id: Mapped[int] = mapped_column(
        ForeignKey("structures.id"), nullable=False
    )
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    total_credits: Mapped[float] = mapped_column(Float, nullable=False)

    structure: Mapped["Structure"] = relationship(back_populates="semesters")
    semester_modules: Mapped[list["Module"]] = relationship(
        back_populates="semester", foreign_keys="[Module.semester_id]"
    )

    def __repr__(self) -> str:
        return (
            f"<StructureSemester id={self.id!r} structure_id={self.structure_id!r} "
            f"semester_number={self.semester_number!r} name={self.name!r} "
            f"total_credits={self.total_credits!r}>"
        )


class Term(Base):
    __tablename__ = "terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return f"<Term id={self.id!r} name={self.name!r} is_active={self.is_active!r}>"


RegistrationRequestStatus = Literal["pending", "approved", "registered", "rejected"]


class RegistrationRequest(Base):
    __tablename__ = "registration_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    std_no: Mapped[int] = mapped_column(
        ForeignKey("students.std_no", ondelete="cascade"), nullable=False
    )
    term_id: Mapped[int] = mapped_column(
        ForeignKey("terms.id", ondelete="cascade"), nullable=False
    )
    status: Mapped[RegistrationRequestStatus] = mapped_column(
        String, nullable=False, default="pending"
    )
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)
    date_approved: Mapped[Optional[int]] = mapped_column(Integer)

    requested_modules: Mapped[list["RequestedModule"]] = relationship(
        back_populates="registration_request", cascade="all, delete"
    )
    clearances: Mapped[list["RegistrationClearance"]] = relationship(
        back_populates="registration_request", cascade="all, delete"
    )

    __table_args__ = (
        UniqueConstraint("std_no", "term_id", name="unique_registration_requests"),
    )

    def __repr__(self) -> str:
        return (
            f"<RegistrationRequest id={self.id!r} std_no={self.std_no!r} term_id={self.term_id!r} "
            f"status={self.status!r} semester_number={self.semester_number!r}>"
        )


class RequestedModule(Base):
    __tablename__ = "requested_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_status: Mapped[ModuleStatus] = mapped_column(
        String, nullable=False, default="Compulsory"
    )
    registration_request_id: Mapped[int] = mapped_column(
        ForeignKey("registration_requests.id", ondelete="cascade"), nullable=False
    )
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    registration_request: Mapped["RegistrationRequest"] = relationship(
        back_populates="requested_modules"
    )
    module: Mapped["Module"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<RequestedModule id={self.id!r} module_status={self.module_status!r} "
            f"registration_request_id={self.registration_request_id!r} module_id={self.module_id!r}>"
        )


DashboardUser = Literal["admin", "finance", "academic", "library"]


class RegistrationClearance(Base):
    __tablename__ = "registration_clearances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    registration_request_id: Mapped[int] = mapped_column(
        ForeignKey("registration_requests.id", ondelete="cascade"), nullable=False
    )
    department: Mapped[DashboardUser] = mapped_column(String, nullable=False)
    status: Mapped[RegistrationRequestStatus] = mapped_column(
        String, nullable=False, default="pending"
    )
    message: Mapped[Optional[str]] = mapped_column(String)
    responded_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="cascade")
    )
    response_date: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    registration_request: Mapped["RegistrationRequest"] = relationship(
        back_populates="clearances"
    )
    responder: Mapped[Optional["User"]] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "registration_request_id",
            "department",
            name="unique_registration_clearance",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<RegistrationClearance id={self.id!r} registration_request_id={self.registration_request_id!r} "
            f"department={self.department!r} status={self.status!r}>"
        )
