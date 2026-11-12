
from sqlalchemy import (
    Column, Integer, String, Float, Text, CheckConstraint
)
from .database import Base


class CandidateRecord(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    qualification = Column(String(180), nullable=False)
    skills = Column(Text, nullable=False, default="")
    preferred_sector = Column(String(100), nullable=False, default="")
    preferred_location = Column(String(100), nullable=False, default="")
    cgpa = Column(Float, nullable=False)
    experience_months = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        CheckConstraint("cgpa >= 0 AND cgpa <= 10"),
        CheckConstraint("experience_months >= 0"),
    )


class InternshipRecord(Base):
    __tablename__ = "internships"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(180), nullable=False)
    company = Column(String(180), nullable=False)
    required_qualification = Column(String(180), nullable=False)
    required_skills = Column(Text, nullable=False, default="")
    sector = Column(String(100), nullable=False, default="")
    location = Column(String(100), nullable=False, default="")
    min_cgpa = Column(Float, nullable=False, default=0)
    seats = Column(Integer, nullable=False, default=1)

    __table_args__ = (
        CheckConstraint("min_cgpa >= 0 AND min_cgpa <= 10"),
        CheckConstraint("seats >= 0"),
    )


class AllocationRecord(Base):
    __tablename__ = "allocations"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, nullable=False, index=True)
    internship_id = Column(Integer, nullable=False, index=True)
    score = Column(Float, nullable=False)
    status = Column(String(30), nullable=False, default="Allocated")
