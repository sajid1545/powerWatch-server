import enum
from datetime import datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, Enum, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

def now(): return datetime.now(timezone.utc)
class Role(str, enum.Enum): admin="admin"; user="user"
class AreaStatus(str, enum.Enum): active="active"; inactive="inactive"
class ScheduleStatus(str, enum.Enum): scheduled="scheduled"; ongoing="ongoing"; completed="completed"; cancelled="cancelled"
class ReportStatus(str, enum.Enum): pending="pending"; investigating="investigating"; resolved="resolved"; rejected="rejected"

class User(Base):
    __tablename__="users"
    id=Column(Integer,primary_key=True,index=True); name=Column(String(120),nullable=False); email=Column(String(255),unique=True,index=True,nullable=False); password_hash=Column(String,nullable=False); phone=Column(String(30)); role=Column(Enum(Role),default=Role.user,nullable=False,index=True); area_id=Column(Integer,ForeignKey("areas.id",ondelete="SET NULL"),index=True); created_at=Column(DateTime(timezone=True),default=now); updated_at=Column(DateTime(timezone=True),default=now,onupdate=now)
    area=relationship("Area",back_populates="users"); reports=relationship("Report",back_populates="user",cascade="all, delete-orphan")
class Area(Base):
    __tablename__="areas"; __table_args__=(UniqueConstraint("name","district",name="uq_area_name_district"),)
    id=Column(Integer,primary_key=True,index=True); name=Column(String(120),nullable=False,index=True); district=Column(String(120),nullable=False,index=True); zone=Column(String(120),nullable=False); description=Column(Text); status=Column(Enum(AreaStatus),default=AreaStatus.active,nullable=False,index=True); created_at=Column(DateTime(timezone=True),default=now); updated_at=Column(DateTime(timezone=True),default=now,onupdate=now)
    users=relationship("User",back_populates="area"); schedules=relationship("Schedule",back_populates="area"); reports=relationship("Report",back_populates="area")
class Schedule(Base):
    __tablename__="schedules"; __table_args__=(CheckConstraint("end_time > start_time",name="end_after_start"),)
    id=Column(Integer,primary_key=True,index=True); title=Column(String(200),nullable=False,index=True); area_id=Column(Integer,ForeignKey("areas.id",ondelete="RESTRICT"),nullable=False,index=True); outage_date=Column(Date,nullable=False,index=True); start_time=Column(Time,nullable=False); end_time=Column(Time,nullable=False); reason=Column(Text,nullable=False); status=Column(Enum(ScheduleStatus),default=ScheduleStatus.scheduled,nullable=False,index=True); created_by=Column(Integer,ForeignKey("users.id",ondelete="RESTRICT"),nullable=False); created_at=Column(DateTime(timezone=True),default=now); updated_at=Column(DateTime(timezone=True),default=now,onupdate=now)
    area=relationship("Area",back_populates="schedules"); creator=relationship("User",foreign_keys=[created_by])
class Report(Base):
    __tablename__="reports"
    id=Column(Integer,primary_key=True,index=True); user_id=Column(Integer,ForeignKey("users.id",ondelete="CASCADE"),nullable=False,index=True); area_id=Column(Integer,ForeignKey("areas.id",ondelete="RESTRICT"),nullable=False,index=True); title=Column(String(200),nullable=False,index=True); description=Column(Text,nullable=False); reported_at=Column(DateTime(timezone=True),default=now); status=Column(Enum(ReportStatus),default=ReportStatus.pending,nullable=False,index=True); admin_response=Column(Text); resolved_at=Column(DateTime(timezone=True)); created_at=Column(DateTime(timezone=True),default=now); updated_at=Column(DateTime(timezone=True),default=now,onupdate=now)
    user=relationship("User",back_populates="reports"); area=relationship("Area",back_populates="reports")
class RefreshToken(Base):
    __tablename__="refresh_tokens"; id=Column(Integer,primary_key=True); user_id=Column(Integer,ForeignKey("users.id",ondelete="CASCADE"),nullable=False,index=True); token_hash=Column(String(64),unique=True,nullable=False); expires_at=Column(DateTime(timezone=True),nullable=False,index=True); revoked=Column(Boolean,default=False)
class PasswordReset(Base):
    __tablename__="password_resets"; id=Column(Integer,primary_key=True); user_id=Column(Integer,ForeignKey("users.id",ondelete="CASCADE"),nullable=False,index=True); token_hash=Column(String(64),unique=True,nullable=False); expires_at=Column(DateTime(timezone=True),nullable=False,index=True); used=Column(Boolean,default=False)
