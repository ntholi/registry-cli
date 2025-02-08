import datetime

date_format = "%Y-%m-%d"


def register_program_payload(std_no: str, program_code: str) -> dict:
    program = get_program(program_code)
    settings = Settings()
    if not settings.intake_date_str():
        raise ValueError("Intake date is not set")
    if not settings.term:
        raise ValueError("Term is not set")

    return {
        "a_add": "A",
        "x_StudentID": std_no,
        "x_StdProgRegDate": today(),
        "x_ProgramID": program.program_id,
        "x_ProgramIntakeDate": settings.intake_date_str(),
        "x_TermCode": settings.term,
        "x_StructureID": program.version,
        "x_ProgStreamCode": "Normal",
        "x_ProgramStatus": "Active",
        "btnAction": "Add",
    }


def add_semester_payload(
    std_program_id: int,
    school_id: int,
    program_id: int,
    structure_id: int,
    term: str,
    semester_id: str,
) -> dict:
    return {
        "x_StdProgramID": std_program_id,
        "x_SchoolID": school_id,
        "x_ProgramID": program_id,
        "x_TermCode": term,
        "x_StructureID": structure_id,
        "x_SemesterID": semester_id,
        "x_CampusCode": "Lesotho",
        "x_StdSemCAFDate": today(),
        "x_SemesterStatus": "Active",
        "btnAction": "Add",
    }


def add_update_payload(std_no: str) -> dict:
    return {
        "a_add": "A",
        "x_StudentID": std_no,
        "x_SuppObjectCode": "REG_SEMESTER",
        "btnAction": "Add",
    }


def today() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")
