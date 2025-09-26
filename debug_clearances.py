from sqlalchemy import and_, func
from sqlalchemy.orm import sessionmaker

from registry_cli.db.config import get_engine
from registry_cli.models import Clearance, GraduationClearance, GraduationRequest

engine = get_engine(use_local=True)
Session = sessionmaker(bind=engine)
db = Session()

print(f"Total graduation requests: {db.query(GraduationRequest).count()}")
print(f"Total clearances: {db.query(Clearance).count()}")
print(f"Total graduation clearances: {db.query(GraduationClearance).count()}")
print(
    f'Approved clearances: {db.query(Clearance).filter(Clearance.status == "approved").count()}'
)

# Check distinct departments
departments = db.query(Clearance.department).distinct().all()
print(f"Departments: {[d[0] for d in departments]}")

# Check clearance statuses
statuses = db.query(Clearance.status).distinct().all()
print(f"Clearance statuses: {[s[0] for s in statuses]}")

# Check graduation clearances with approved status by department
for dept in ["finance", "registry", "library", "resource", "academic"]:
    count = (
        db.query(GraduationClearance)
        .join(Clearance, GraduationClearance.clearance_id == Clearance.id)
        .filter(and_(Clearance.department == dept, Clearance.status == "approved"))
        .count()
    )
    print(f"Approved {dept} graduation clearances: {count}")

# Now let's check the complex query from our function
required_departments = ["finance", "registry", "library", "resource", "academic"]

graduation_requests_with_full_approval = (
    db.query(GraduationRequest.id, GraduationRequest.student_program_id)
    .join(
        GraduationClearance,
        GraduationRequest.id == GraduationClearance.graduation_request_id,
    )
    .join(Clearance, GraduationClearance.clearance_id == Clearance.id)
    .filter(
        and_(
            Clearance.status == "approved",
            Clearance.department.in_(required_departments),
        )
    )
    .group_by(GraduationRequest.id, GraduationRequest.student_program_id)
    .having(
        func.count(func.distinct(Clearance.department)) == len(required_departments)
    )
    .all()
)

print(
    f"Graduation requests with full approval: {len(graduation_requests_with_full_approval)}"
)

# Let's also check how many departments each graduation request has approved
query_with_counts = (
    db.query(
        GraduationRequest.id,
        GraduationRequest.student_program_id,
        func.count(func.distinct(Clearance.department)).label("dept_count"),
    )
    .join(
        GraduationClearance,
        GraduationRequest.id == GraduationClearance.graduation_request_id,
    )
    .join(Clearance, GraduationClearance.clearance_id == Clearance.id)
    .filter(
        and_(
            Clearance.status == "approved",
            Clearance.department.in_(required_departments),
        )
    )
    .group_by(GraduationRequest.id, GraduationRequest.student_program_id)
    .all()
)

print(f"Breakdown by number of approved departments:")
from collections import Counter

dept_counts = Counter([row.dept_count for row in query_with_counts])
for count, num_requests in sorted(dept_counts.items()):
    print(f"  {count} departments approved: {num_requests} requests")

db.close()
