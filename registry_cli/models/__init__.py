from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4

from nanoid import generate
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


DashboardUser = Literal[
    "finance", "registry", "library", "resource", "academic", "admin"
]
UserRole = Literal[
    "user", "student", "finance", "registry", "library", "resource", "academic", "admin"
]
UserPosition = Literal[
    "manager",
    "program_leader",
    "principal_lecturer",
    "year_leader",
    "lecturer",
    "admin",
]


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate()
    )
    name: Mapped[Optional[str]] = mapped_column(String)
    role: Mapped[UserRole] = mapped_column(String, default="user", nullable=False)
    position: Mapped[Optional[UserPosition]] = mapped_column(String)
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
    date_of_birth: Mapped[Optional[int]] = mapped_column(Integer)
    phone1: Mapped[Optional[str]] = mapped_column(String)
    phone2: Mapped[Optional[str]] = mapped_column(String)
    gender: Mapped[Optional[Gender]] = mapped_column(String)
    marital_status: Mapped[Optional[MaritalStatus]] = mapped_column(String)
    religion: Mapped[Optional[str]] = mapped_column(String)
    user_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

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
    intake_date: Mapped[Optional[str]] = mapped_column(String)
    reg_date: Mapped[Optional[str]] = mapped_column(String)
    start_term: Mapped[Optional[str]] = mapped_column(String)
    structure_id: Mapped[int] = mapped_column(
        ForeignKey("structures.id", ondelete="cascade"), nullable=False
    )
    stream: Mapped[Optional[str]] = mapped_column(String)
    graduation_date: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[ProgramStatus] = mapped_column(String, nullable=False)
    assist_provider: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    semesters: Mapped[list["StudentSemester"]] = relationship(
        back_populates="program", cascade="all, delete"
    )
    student: Mapped["Student"] = relationship(back_populates="programs")
    structure: Mapped["Structure"] = relationship(back_populates="student_programs")

    def __repr__(self) -> str:
        return f"<StudentProgram id={self.id!r} std_no={self.std_no!r} status={self.status!r}>"


SemesterStatus = Literal[
    "Active",
    "Outstanding",
    "Deferred",
    "Deleted",
    "DNR",
    "DroppedOut",
    "Withdrawn",
    "Enrolled",
    "Exempted",
    "Inactive",
    "Repeat",
]


class StudentSemester(Base):
    __tablename__ = "student_semesters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term: Mapped[str] = mapped_column(String, nullable=False)
    semester_number: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[SemesterStatus] = mapped_column(String, nullable=False)
    student_program_id: Mapped[int] = mapped_column(
        ForeignKey("student_programs.id", ondelete="cascade"), nullable=False
    )
    caf_date: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

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
    "Def",
    "DEF",
    "GNS",
    "ANN",
    "FIN",
    "FX",
    "DNC",
    "DNA",
    "PP",
    "DNS",
    "EXP",
    "NM",
]


class StudentModule(Base):
    __tablename__ = "student_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semester_module_id: Mapped[int] = mapped_column(
        ForeignKey("semester_modules.id", ondelete="cascade"), nullable=False
    )
    status: Mapped[ModuleStatus] = mapped_column(String, nullable=False)
    marks: Mapped[str] = mapped_column(String, nullable=False)
    grade: Mapped[GradeType] = mapped_column(String, nullable=False)
    student_semester_id: Mapped[int] = mapped_column(
        ForeignKey("student_semesters.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

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
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    programs: Mapped[list["Program"]] = relationship(back_populates="school")
    user_schools: Mapped[list["UserSchool"]] = relationship(back_populates="school")

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
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

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
    desc: Mapped[Optional[str]] = mapped_column(String)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )

    program: Mapped["Program"] = relationship(back_populates="structures")
    student_programs: Mapped[list["StudentProgram"]] = relationship(
        back_populates="structure"
    )
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
    status: Mapped[str] = mapped_column(String, nullable=False, default="Active")
    timestamp: Mapped[Optional[str]] = mapped_column(String)

    semester_modules: Mapped[list["SemesterModule"]] = relationship(
        back_populates="module"
    )
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="module")
    module_grades: Mapped[list["ModuleGrade"]] = relationship(back_populates="module")

    def __repr__(self) -> str:
        return (
            f"<Module id={self.id!r} code={self.code!r} name={self.name!r} "
            f"status={self.status!r}>"
        )


class SemesterModule(Base):
    __tablename__ = "semester_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    module_id: Mapped[Optional[int]] = mapped_column(ForeignKey("modules.id"))
    type: Mapped[ModuleType] = mapped_column(String, nullable=False)
    credits: Mapped[float] = mapped_column(Float, nullable=False)
    semester_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("structure_semesters.id", ondelete="SET NULL")
    )
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    semester: Mapped[Optional["StructureSemester"]] = relationship(
        back_populates="semester_modules", foreign_keys=[semester_id]
    )
    module: Mapped[Optional["Module"]] = relationship(back_populates="semester_modules")
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
    assigned_modules: Mapped[list["AssignedModule"]] = relationship(
        back_populates="semester_module"
    )

    def __repr__(self) -> str:
        return f"<SemesterModule id={self.id!r} type={self.type!r} credits={self.credits!r}>"


class ModulePrerequisite(Base):
    __tablename__ = "module_prerequisites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semester_module_id: Mapped[int] = mapped_column(
        ForeignKey("semester_modules.id", ondelete="cascade"), nullable=False
    )
    prerequisite_id: Mapped[int] = mapped_column(
        ForeignKey("semester_modules.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    module: Mapped["SemesterModule"] = relationship(
        "SemesterModule",
        foreign_keys=[semester_module_id],
        back_populates="prerequisites",
    )
    prerequisite: Mapped["SemesterModule"] = relationship(
        "SemesterModule",
        foreign_keys=[prerequisite_id],
        back_populates="is_prerequisite_for",
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
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

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
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    assessments: Mapped[list["Assessment"]] = relationship(back_populates="term")

    def __repr__(self) -> str:
        return f"<Term id={self.id!r} name={self.name!r} is_active={self.is_active!r} semester={self.semester!r}>"


class Sponsor(Base):
    __tablename__ = "sponsors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
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
    bank_name: Mapped[Optional[str]] = mapped_column(String)
    account_number: Mapped[Optional[str]] = mapped_column(String)
    confirmed: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("sponsor_id", "std_no", name="unique_sponsored_student"),
    )

    def __repr__(self) -> str:
        return f"<SponsoredStudent id={self.id!r} sponsor_id={self.sponsor_id!r} std_no={self.std_no!r}>"


class SponsoredTerm(Base):
    __tablename__ = "sponsored_terms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sponsored_student_id: Mapped[int] = mapped_column(
        ForeignKey("sponsored_students.id", ondelete="cascade"), nullable=False
    )
    term_id: Mapped[int] = mapped_column(
        ForeignKey("terms.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint(
            "sponsored_student_id", "term_id", name="unique_sponsored_term"
        ),
    )

    def __repr__(self) -> str:
        return f"<SponsoredTerm id={self.id!r} sponsored_student_id={self.sponsored_student_id!r} term_id={self.term_id!r}>"


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
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)
    date_approved: Mapped[Optional[int]] = mapped_column(Integer)

    requested_modules: Mapped[list["RequestedModule"]] = relationship(
        back_populates="registration_request", cascade="all, delete"
    )
    registration_clearances: Mapped[list["RegistrationClearance"]] = relationship(
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
        ForeignKey("semester_modules.id", ondelete="cascade"), nullable=False
    )
    status: Mapped[RequestedModuleStatus] = mapped_column(
        String, nullable=False, default="pending"
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    registration_request: Mapped["RegistrationRequest"] = relationship(
        back_populates="requested_modules"
    )
    semester_module: Mapped["SemesterModule"] = relationship()

    def __repr__(self) -> str:
        return (
            f"<RequestedModule id={self.id!r} module_status={self.module_status!r} "
            f"registration_request_id={self.registration_request_id!r} semester_module_id={self.semester_module_id!r} "
            f"status={self.status!r}>"
        )


ClearanceStatus = Literal["pending", "approved", "rejected"]


class Clearance(Base):
    __tablename__ = "clearance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    department: Mapped[DashboardUser] = mapped_column(String, nullable=False)
    status: Mapped[ClearanceStatus] = mapped_column(
        String, nullable=False, default="pending"
    )
    message: Mapped[Optional[str]] = mapped_column(String)
    email_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    responded_by: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="cascade")
    )
    response_date: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    responder: Mapped[Optional["User"]] = relationship()
    registration_clearances: Mapped[list["RegistrationClearance"]] = relationship(
        back_populates="clearance", cascade="all, delete"
    )
    audits: Mapped[list["ClearanceAudit"]] = relationship(
        back_populates="clearance", cascade="all, delete"
    )

    def __repr__(self) -> str:
        return f"<Clearance id={self.id!r} department={self.department!r} status={self.status!r}>"


class RegistrationClearance(Base):
    __tablename__ = "registration_clearance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    registration_request_id: Mapped[int] = mapped_column(
        ForeignKey("registration_requests.id", ondelete="cascade"), nullable=False
    )
    clearance_id: Mapped[int] = mapped_column(
        ForeignKey("clearance.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    registration_request: Mapped["RegistrationRequest"] = relationship(
        back_populates="registration_clearances"
    )
    clearance: Mapped["Clearance"] = relationship(
        back_populates="registration_clearances"
    )

    __table_args__ = (
        UniqueConstraint(
            "registration_request_id",
            "clearance_id",
            name="registration_clearance_unique",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<RegistrationClearance id={self.id!r} registration_request_id={self.registration_request_id!r} "
            f"clearance_id={self.clearance_id!r}>"
        )


class ClearanceAudit(Base):
    __tablename__ = "clearance_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clearance_id: Mapped[int] = mapped_column(
        ForeignKey("clearance.id", ondelete="cascade"), nullable=False
    )
    previous_status: Mapped[Optional[ClearanceStatus]] = mapped_column(String)
    new_status: Mapped[ClearanceStatus] = mapped_column(String, nullable=False)
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=False
    )
    date: Mapped[int] = mapped_column(
        Integer, nullable=False, default=lambda: int(datetime.now().timestamp())
    )
    message: Mapped[Optional[str]] = mapped_column(String)
    modules: Mapped[list[str]] = mapped_column(JSON, default=lambda: [], nullable=False)

    clearance: Mapped["Clearance"] = relationship(back_populates="audits")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])

    def __repr__(self) -> str:
        return (
            f"<ClearanceAudit id={self.id!r} "
            f"clearance_id={self.clearance_id!r} "
            f"previous_status={self.previous_status!r} new_status={self.new_status!r}>"
        )


class AssignedModule(Base):
    __tablename__ = "assigned_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    term_id: Mapped[int] = mapped_column(
        ForeignKey("terms.id", ondelete="cascade"), nullable=False
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="cascade"), nullable=False
    )
    semester_module_id: Mapped[int] = mapped_column(
        ForeignKey("semester_modules.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    user: Mapped["User"] = relationship()
    semester_module: Mapped["SemesterModule"] = relationship(
        back_populates="assigned_modules"
    )

    def __repr__(self) -> str:
        return f"<AssignedModule id={self.id!r} user_id={self.user_id!r} semester_module_id={self.semester_module_id!r}>"


class UserSchool(Base):
    __tablename__ = "user_schools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="cascade"), nullable=False
    )
    school_id: Mapped[int] = mapped_column(
        ForeignKey("schools.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    user: Mapped["User"] = relationship()
    school: Mapped["School"] = relationship(back_populates="user_schools")

    __table_args__ = (
        UniqueConstraint("user_id", "school_id", name="unique_user_school"),
    )

    def __repr__(self) -> str:
        return f"<UserSchool id={self.id!r} user_id={self.user_id!r} school_id={self.school_id!r}>"


AssessmentNumber = Literal[
    "CW1",
    "CW2",
    "CW3",
    "CW4",
    "CW5",
    "CW6",
    "CW7",
    "CW8",
    "CW9",
    "CW10",
    "CW11",
    "CW12",
    "CW13",
    "CW14",
    "CW15",
]


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="cascade"), nullable=False
    )
    term_id: Mapped[int] = mapped_column(
        ForeignKey("terms.id", ondelete="cascade"), nullable=False
    )
    assessment_number: Mapped[AssessmentNumber] = mapped_column(String, nullable=False)
    assessment_type: Mapped[str] = mapped_column(String, nullable=False)
    total_marks: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    module: Mapped["Module"] = relationship(back_populates="assessments")
    term: Mapped["Term"] = relationship(back_populates="assessments")
    assessment_marks: Mapped[list["AssessmentMark"]] = relationship(
        back_populates="assessment"
    )

    __table_args__ = (
        UniqueConstraint(
            "module_id", "assessment_number", "term_id", name="unique_assessment_module"
        ),
    )

    def __repr__(self) -> str:
        return f"<Assessment id={self.id!r} module_id={self.module_id!r} assessment_number={self.assessment_number!r}>"


class AssessmentMark(Base):
    __tablename__ = "assessment_marks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="cascade"), nullable=False
    )
    std_no: Mapped[int] = mapped_column(
        ForeignKey("students.std_no", ondelete="cascade"), nullable=False
    )
    marks: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    assessment: Mapped["Assessment"] = relationship(back_populates="assessment_marks")
    student: Mapped["Student"] = relationship()

    def __repr__(self) -> str:
        return f"<AssessmentMark id={self.id!r} assessment_id={self.assessment_id!r} std_no={self.std_no!r} marks={self.marks!r}>"


class ModuleGrade(Base):
    __tablename__ = "module_grades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="cascade"), nullable=False
    )
    std_no: Mapped[int] = mapped_column(
        ForeignKey("students.std_no", ondelete="cascade"), nullable=False
    )
    grade: Mapped[GradeType] = mapped_column(String, nullable=False)
    weighted_total: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

    module: Mapped["Module"] = relationship(back_populates="module_grades")
    student: Mapped["Student"] = relationship()

    __table_args__ = (
        UniqueConstraint("module_id", "std_no", name="unique_module_student"),
    )

    def __repr__(self) -> str:
        return f"<ModuleGrade id={self.id!r} module_id={self.module_id!r} std_no={self.std_no!r} grade={self.grade!r}>"


class GraduationRequest(Base):
    __tablename__ = "graduation_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_program_id: Mapped[int] = mapped_column(
        ForeignKey("student_programs.id", ondelete="cascade"),
        nullable=False,
        unique=True,
    )
    information_confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    message: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[Optional[int]] = mapped_column(Integer)

    student_program: Mapped["StudentProgram"] = relationship()

    def __repr__(self) -> str:
        return f"<GraduationRequest id={self.id!r} student_program_id={self.student_program_id!r}>"


class GraduationClearance(Base):
    __tablename__ = "graduation_clearance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    graduation_request_id: Mapped[int] = mapped_column(
        ForeignKey("graduation_requests.id", ondelete="cascade"), nullable=False
    )
    clearance_id: Mapped[int] = mapped_column(
        ForeignKey("clearance.id", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("clearance_id", name="unique_graduation_clearance"),
    )

    def __repr__(self) -> str:
        return f"<GraduationClearance id={self.id!r} graduation_request_id={self.graduation_request_id!r}>"


PaymentType = Literal["graduation_gown", "graduation_fee"]


class PaymentReceipt(Base):
    __tablename__ = "payment_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    graduation_request_id: Mapped[int] = mapped_column(
        ForeignKey("graduation_requests.id", ondelete="cascade"), nullable=False
    )
    payment_type: Mapped[PaymentType] = mapped_column(String, nullable=False)
    receipt_no: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<PaymentReceipt id={self.id!r} graduation_request_id={self.graduation_request_id!r} payment_type={self.payment_type!r}>"


class StatementOfResultsPrint(Base):
    __tablename__ = "statement_of_results_prints"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate()
    )
    std_no: Mapped[int] = mapped_column(
        ForeignKey("students.std_no", ondelete="cascade"), nullable=False
    )
    printed_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=False
    )
    student_name: Mapped[str] = mapped_column(String, nullable=False)
    program_name: Mapped[str] = mapped_column(String, nullable=False)
    total_credits: Mapped[int] = mapped_column(Integer, nullable=False)
    total_modules: Mapped[int] = mapped_column(Integer, nullable=False)
    cgpa: Mapped[Optional[float]] = mapped_column(Float)
    classification: Mapped[Optional[str]] = mapped_column(String)
    academic_status: Mapped[Optional[str]] = mapped_column(String)
    graduation_date: Mapped[Optional[str]] = mapped_column(String)
    printed_at: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<StatementOfResultsPrint id={self.id!r} std_no={self.std_no!r}>"


BlockedStatus = Literal["blocked", "unblocked"]


class BlockedStudent(Base):
    __tablename__ = "blocked_students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[BlockedStatus] = mapped_column(
        String, nullable=False, default="blocked"
    )
    reason: Mapped[str] = mapped_column(String, nullable=False)
    by_department: Mapped[DashboardUser] = mapped_column(String, nullable=False)
    std_no: Mapped[int] = mapped_column(
        ForeignKey("students.std_no", ondelete="cascade"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (Index("blocked_students_std_no_idx", "std_no"),)

    def __repr__(self) -> str:
        return f"<BlockedStudent id={self.id!r} std_no={self.std_no!r} status={self.status!r}>"


class StudentCardPrint(Base):
    __tablename__ = "student_card_prints"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: generate()
    )
    reference: Mapped[str] = mapped_column(
        String, nullable=False, unique=True, default="Initial Print"
    )
    std_no: Mapped[int] = mapped_column(
        ForeignKey("students.std_no", ondelete="cascade"), nullable=False
    )
    printed_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=False
    )
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<StudentCardPrint id={self.id!r} std_no={self.std_no!r}>"


AssessmentMarksAuditAction = Literal["create", "update", "delete"]


class AssessmentMarksAudit(Base):
    __tablename__ = "assessment_marks_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_mark_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("assessment_marks.id", ondelete="set null")
    )
    action: Mapped[AssessmentMarksAuditAction] = mapped_column(String, nullable=False)
    previous_marks: Mapped[Optional[float]] = mapped_column(Float)
    new_marks: Mapped[Optional[float]] = mapped_column(Float)
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=False
    )
    date: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<AssessmentMarksAudit id={self.id!r} action={self.action!r}>"


AssessmentsAuditAction = Literal["create", "update", "delete"]


class AssessmentsAudit(Base):
    __tablename__ = "assessments_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    assessment_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("assessments.id", ondelete="set null")
    )
    action: Mapped[AssessmentsAuditAction] = mapped_column(String, nullable=False)
    previous_assessment_number: Mapped[Optional[AssessmentNumber]] = mapped_column(
        String
    )
    new_assessment_number: Mapped[Optional[AssessmentNumber]] = mapped_column(String)
    previous_assessment_type: Mapped[Optional[str]] = mapped_column(String)
    new_assessment_type: Mapped[Optional[str]] = mapped_column(String)
    previous_total_marks: Mapped[Optional[float]] = mapped_column(Float)
    new_total_marks: Mapped[Optional[float]] = mapped_column(Float)
    previous_weight: Mapped[Optional[float]] = mapped_column(Float)
    new_weight: Mapped[Optional[float]] = mapped_column(Float)
    created_by: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="set null"), nullable=False
    )
    date: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<AssessmentsAudit id={self.id!r} action={self.action!r}>"
