from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer,
                        String, UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


DashboardUser = Literal[
    "finance", "registry", "library", "resource", "academic", "admin"
]
UserRole = Literal[
    "user", "student", "finance", "registry", "library", "resource", "academic", "admin"
]


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[Optional[str]] = mapped_column(String)
    role: Mapped[UserRole] = mapped_column(String, default="user", nullable=False)
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
    structure_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("structures.id", ondelete="SET NULL")
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
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
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )

    semesters: Mapped[list["StudentSemester"]] = relationship(
        back_populates="program", cascade="all, delete"
    )
    student: Mapped["Student"] = relationship(back_populates="programs")

    def __repr__(self) -> str:
        return f"<StudentProgram id={self.id!r} std_no={self.std_no!r} status={self.status!r}>"


SemesterStatus = Literal[
    "Active",
    "Outstanding",
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
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
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


ModuleType = Literal["Major", "Minor", "Core", "Delete", "Elective"]
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

GradeType = Literal[
    "A+",
    "A",
    "A-",
    "B+",
    "B",
    "B-",
    "C+",
    "C",
    "C-",
    "F",
    "PC",
    "PX",
    "AP",
    "X",
    "GNS",
    "ANN",
    "FIN",
    "FX",
    "DNC",
    "DNA",
    "PP",
    "DNS",
]


class StudentModule(Base):
    __tablename__ = "student_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semester_module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="cascade"), nullable=False
    )
    status: Mapped[ModuleStatus] = mapped_column(String, nullable=False)
    marks: Mapped[str] = mapped_column(String, nullable=False)
    grade: Mapped[GradeType] = mapped_column(String, nullable=False)
    student_semester_id: Mapped[int] = mapped_column(
        ForeignKey("student_semesters.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )

    semester: Mapped["StudentSemester"] = relationship(back_populates="modules")

    def __repr__(self) -> str:
        return (
            f"<StudentModule id={self.id!r} semester_module_id={self.semester_module_id!r} status={self.status!r} "
            f"marks={self.marks!r} grade={self.grade!r}>"
        )


class School(Base):
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )

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
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )

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
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )

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
    status: Mapped[str] = mapped_column(String, nullable=False)
    timestamp: Mapped[int] = mapped_column(Integer)

    semester_modules: Mapped[list["SemesterModule"]] = relationship(
        back_populates="module"
    )

    def __repr__(self) -> str:
        return (
            f"<Module id={self.id!r} code={self.code!r} name={self.name!r} "
            f"status={self.status!r}>"
        )


class SemesterModule(Base):
    __tablename__ = "semester_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id")
    )
    type: Mapped[ModuleType] = mapped_column(String, nullable=False)
    credits: Mapped[float] = mapped_column(Float, nullable=False)
    semester_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("structure_semesters.id", ondelete="SET NULL")
    )
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )

    semester: Mapped[Optional["StructureSemester"]] = relationship(
        back_populates="semester_modules", foreign_keys=[semester_id]
    )
    prerequisites: Mapped[list["ModulePrerequisite"]] = relationship(
        back_populates="module",
        foreign_keys="[ModulePrerequisite.semester_module_id]",
        cascade="all, delete",
    )
    is_prerequisite_for: Mapped[list["ModulePrerequisite"]] = relationship(
        back_populates="prerequisite",
        foreign_keys="[ModulePrerequisite.prerequisite_id]",
        cascade="all, delete",
    )

    def __repr__(self) -> str:
        return (
            f"<Module id={self.id!r} type={self.type!r} credits={self.credits!r}>"
        )


class ModulePrerequisite(Base):
    __tablename__ = "module_prerequisites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semester_module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="cascade"), nullable=False
    )
    prerequisite_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )

    module: Mapped["SemesterModule"] = relationship(
        "SemesterModule", foreign_keys=[semester_module_id], back_populates="prerequisites"
    )
    prerequisite: Mapped["SemesterModule"] = relationship(
        "SemesterModule", foreign_keys=[prerequisite_id], back_populates="is_prerequisite_for"
    )

    __table_args__ = (
        UniqueConstraint(
            "semester_module_id",
            "prerequisite_id",
            name="unique_module_prerequisite",
        ),
    )

    def __repr__(self) -> str:
        return f"<ModulePrerequisite id={self.id!r} semester_module_id={self.semester_module_id!r} prerequisite_id={self.prerequisite_id!r}>"


class StructureSemester(Base):
    __tablename__ = "structure_semesters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    structure_id: Mapped[int] = mapped_column(
        ForeignKey("structures.id", ondelete="cascade"), nullable=False
    )
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    total_credits: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )

    structure: Mapped["Structure"] = relationship(back_populates="semesters")
    semester_modules: Mapped[list["SemesterModule"]] = relationship(
        back_populates="semester", foreign_keys="[SemesterModule.semester_id]"
    )

    def __repr__(self) -> str:
        return (
            f"<StructureSemester id={self.id!r} structure_id={self.structure_id!r} "
            f"semester_number={self.semester_number!r} name={self.name!r} "
            f"total_credits={self.total_credits!r}>"
        )


class Term(Base):
    __tablename__ = "terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )

    def __repr__(self) -> str:
        return f"<Term id={self.id!r} name={self.name!r} is_active={self.is_active!r} semester={self.semester!r}>"


class Sponsor(Base):
    __tablename__ = "sponsors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)

    def __repr__(self) -> str:
        return f"<Sponsor id={self.id!r} name={self.name!r}>"


class SponsoredStudent(Base):
    __tablename__ = "sponsored_students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sponsor_id: Mapped[int] = mapped_column(
        ForeignKey("sponsors.id", ondelete="cascade"), nullable=False
    )
    std_no: Mapped[int] = mapped_column(
        ForeignKey("students.std_no", ondelete="cascade"), nullable=False
    )
    borrower_no: Mapped[Optional[str]] = mapped_column(String)
    term_id: Mapped[int] = mapped_column(
        ForeignKey("terms.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("std_no", "term_id", name="unique_sponsored_term"),
    )

    def __repr__(self) -> str:
        return f"<SponsoredStudent id={self.id!r} sponsor_id={self.sponsor_id!r} std_no={self.std_no!r}>"


RegistrationRequestStatus = Literal[
    "pending", "approved", "partial", "registered", "rejected"
]


class RegistrationRequest(Base):
    __tablename__ = "registration_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sponsor_id: Mapped[int] = mapped_column(
        ForeignKey("sponsors.id", ondelete="cascade"), nullable=False
    )
    std_no: Mapped[int] = mapped_column(
        ForeignKey("students.std_no", ondelete="cascade"), nullable=False
    )
    term_id: Mapped[int] = mapped_column(
        ForeignKey("terms.id", ondelete="cascade"), nullable=False
    )
    status: Mapped[RegistrationRequestStatus] = mapped_column(
        String, nullable=False, default="pending"
    )
    semester_status: Mapped[Literal["Active", "Repeat"]] = mapped_column(
        String, nullable=False
    )
    semester_number: Mapped[int] = mapped_column(Integer, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(String)
    mail_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)
    date_approved: Mapped[Optional[int]] = mapped_column(Integer)

    requested_modules: Mapped[list["RequestedModule"]] = relationship(
        back_populates="registration_request", cascade="all, delete"
    )
    clearances: Mapped[list["RegistrationClearance"]] = relationship(
        back_populates="registration_request", cascade="all, delete"
    )
    sponsor: Mapped["Sponsor"] = relationship()

    __table_args__ = (
        UniqueConstraint("std_no", "term_id", name="unique_registration_requests"),
    )

    def __repr__(self) -> str:
        return (
            f"<RegistrationRequest id={self.id!r} std_no={self.std_no!r} term_id={self.term_id!r} "
            f"status={self.status!r} semester_number={self.semester_number!r}>"
        )


RequestedModuleStatus = Literal["pending", "registered", "rejected"]


class RequestedModule(Base):
    __tablename__ = "requested_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_status: Mapped[ModuleStatus] = mapped_column(
        String, nullable=False, default="Compulsory"
    )
    registration_request_id: Mapped[int] = mapped_column(
        ForeignKey("registration_requests.id", ondelete="cascade"), nullable=False
    )
    semester_module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="cascade"), nullable=False
    )
    status: Mapped[RequestedModuleStatus] = mapped_column(
        String, nullable=False, default="pending"
    )
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )

    registration_request: Mapped["RegistrationRequest"] = relationship(
        back_populates="requested_modules"
    )
    module: Mapped["SemesterModule"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<RequestedModule id={self.id!r} module_status={self.module_status!r} "
            f"registration_request_id={self.registration_request_id!r} semester_module_id={self.semester_module_id!r} "
            f"status={self.status!r}>"
        )


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
    email_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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


class RegistrationClearanceAudit(Base):
    __tablename__ = "registration_clearance_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    registration_clearance_id: Mapped[int] = mapped_column(
        ForeignKey("registration_clearances.id", ondelete="cascade"), nullable=False
    )
    previous_status: Mapped[Optional[RegistrationRequestStatus]] = mapped_column(String)
    new_status: Mapped[RegistrationRequestStatus] = mapped_column(
        String, nullable=False
    )
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=False
    )
    date: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )
    message: Mapped[Optional[str]] = mapped_column(String)
    modules: Mapped[list[str]] = mapped_column(JSON, default=lambda: [], nullable=False)

    registration_clearance: Mapped["RegistrationClearance"] = relationship()
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])

    def __repr__(self) -> str:
        return (
            f"<RegistrationClearanceAudit id={self.id!r} "
            f"registration_clearance_id={self.registration_clearance_id!r} "
            f"previous_status={self.previous_status!r} new_status={self.new_status!r}>"
        )
