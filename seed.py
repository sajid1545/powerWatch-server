from datetime import date, timedelta, time

from dotenv import load_dotenv

load_dotenv()

from database import Base, SessionLocal, engine
from models import Area, Report, Schedule, User
from security import hash_password

Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    area_specs = [
        ("Bakalia", "Chattogram", "South", "Bakalia residential and commercial zone"),
        ("Agrabad", "Chattogram", "Central", "Commercial district"),
        ("Dhanmondi", "Dhaka", "Central", "Dhanmondi residential area"),
        ("Uttara Sector 7", "Dhaka", "North", "Uttara distribution zone"),
    ]
    areas = []
    for name, district, zone, description in area_specs:
        area = db.query(Area).filter(Area.name == name, Area.district == district).first()
        if not area:
            area = Area(name=name, district=district, zone=zone, description=description, status="active")
            db.add(area)
            db.flush()
        areas.append(area)

    admin = db.query(User).filter(User.email == "admin@powerwatch.bd").first()
    if not admin:
        admin = User(name="System Admin", email="admin@powerwatch.bd", password_hash=hash_password("Admin123!"), phone="01700000001", role="admin", area_id=areas[1].id)
        db.add(admin)
        db.flush()

    user = db.query(User).filter(User.email == "user@powerwatch.bd").first()
    if not user:
        user = User(name="Demo User", email="user@powerwatch.bd", password_hash=hash_password("User123!"), phone="01800000002", role="user", area_id=areas[0].id)
        db.add(user)
        db.flush()

    if db.query(Schedule).count() == 0:
        db.add_all([
            Schedule(title="Planned feeder maintenance", area_id=areas[0].id, outage_date=date.today(), start_time=time(10), end_time=time(12), reason="Transformer maintenance", status="scheduled", created_by=admin.id),
            Schedule(title="Grid upgrade work", area_id=areas[1].id, outage_date=date.today()+timedelta(days=2), start_time=time(14), end_time=time(16), reason="Capacity upgrade", status="scheduled", created_by=admin.id),
            Schedule(title="Emergency line repair", area_id=areas[2].id, outage_date=date.today(), start_time=time(9), end_time=time(11), reason="Damaged conductor repair", status="ongoing", created_by=admin.id),
        ])

    if db.query(Report).filter(Report.user_id == user.id).count() == 0:
        db.add_all([
            Report(user_id=user.id, area_id=areas[0].id, title="Unexpected outage on College Road", description="Power has been unavailable for over one hour.", status="pending"),
            Report(user_id=user.id, area_id=areas[0].id, title="Frequent voltage drops", description="Voltage fluctuates every evening near the market.", status="investigating", admin_response="Our field team is inspecting the feeder."),
        ])

    db.commit()
    print("Seed complete")
    print("Admin: admin@powerwatch.bd / Admin123!")
    print("User: user@powerwatch.bd / User123!")
finally:
    db.close()
