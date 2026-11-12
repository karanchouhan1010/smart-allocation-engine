import os
import hmac
import jwt
from datetime import datetime, timedelta, timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import text
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .database import Base, engine, SessionLocal, get_db
from .models import CandidateRecord, InternshipRecord, AllocationRecord

from pydantic import BaseModel

class CandidateIn(BaseModel):
    name: str
    qualification: str
    skills: List[str]
    preferred_sector: str
    preferred_location: str
    cgpa: float = Field(ge=0, le=10)
    experience_months: int = Field(default=0, ge=0)


class CandidateOut(CandidateIn):
    id: int
    model_config = ConfigDict(from_attributes=True)


class InternshipIn(BaseModel):
    role: str
    company: str
    required_qualification: str
    required_skills: List[str]
    sector: str
    location: str
    min_cgpa: float = Field(default=0, ge=0, le=10)
    seats: int = Field(default=1, ge=0)


class InternshipOut(InternshipIn):
    id: int
    model_config = ConfigDict(from_attributes=True)


class MatchResult(BaseModel):
    internship_id: int
    role: str
    company: str
    location: str
    eligible: bool
    score: float
    matched_skills: List[str]
    missing_skills: List[str]
    reasons: List[str]


def candidate_dict(row):
    return {
        "id": row.id,
        "name": row.name,
        "qualification": row.qualification,
        "skills": [s.strip() for s in row.skills.split(",") if s.strip()],
        "preferred_sector": row.preferred_sector,
        "preferred_location": row.preferred_location,
        "cgpa": row.cgpa,
        "experience_months": row.experience_months,
    }


def internship_dict(row):
    return {
        "id": row.id,
        "role": row.role,
        "company": row.company,
        "required_qualification": row.required_qualification,
        "required_skills": [
            s.strip() for s in row.required_skills.split(",") if s.strip()
        ],
        "sector": row.sector,
        "location": row.location,
        "min_cgpa": row.min_cgpa,
        "seats": row.seats,
    }


def seed_database(db):
    if db.query(CandidateRecord).count() == 0:
        db.add_all([
            CandidateRecord(
                name="Aarav Sharma",
                qualification="B.Tech Computer Science",
                skills="Python,SQL,Machine Learning,Pandas,HTML,CSS",
                preferred_sector="Technology",
                preferred_location="Indore",
                cgpa=8.2,
                experience_months=2,
            ),
            CandidateRecord(
                name="Meera Patel",
                qualification="B.Tech Information Technology",
                skills="Java,HTML,CSS,JavaScript,React,SQL",
                preferred_sector="Technology",
                preferred_location="Pune",
                cgpa=8.7,
                experience_months=0,
            ),
            CandidateRecord(
                name="Rohan Verma",
                qualification="B.Com",
                skills="Excel,Communication,Data Analysis,Power BI",
                preferred_sector="Finance",
                preferred_location="Indore",
                cgpa=7.8,
                experience_months=3,
            ),
        ])

    if db.query(InternshipRecord).count() == 0:
        db.add_all([
            InternshipRecord(
                role="Python Data Intern", company="TechNova",
                required_qualification="B.Tech",
                required_skills="Python,SQL,Pandas,Data Analysis",
                sector="Technology", location="Indore",
                min_cgpa=7.0, seats=2,
            ),
            InternshipRecord(
                role="Frontend Developer Intern", company="WebWorks",
                required_qualification="B.Tech",
                required_skills="HTML,CSS,JavaScript,React",
                sector="Technology", location="Pune",
                min_cgpa=7.5, seats=1,
            ),
            InternshipRecord(
                role="Business Data Intern", company="FinEdge",
                required_qualification="B.Com",
                required_skills="Excel,Data Analysis,Power BI",
                sector="Finance", location="Indore",
                min_cgpa=7.0, seats=2,
            ),
            InternshipRecord(
                role="Machine Learning Intern", company="AI Labs",
                required_qualification="B.Tech",
                required_skills="Python,Machine Learning,Statistics,SQL",
                sector="Technology", location="Bengaluru",
                min_cgpa=8.0, seats=1,
            ),
        ])

    db.commit()


def norm(value):
    return " ".join(value.lower().split())


def is_qualified(candidate, internship):
    required = norm(internship["required_qualification"])
    actual = norm(candidate["qualification"])

    if required in actual:
        return True

    if required == "b.tech":
        return (
            "computer science" in actual
            or "information technology" in actual
        )

    return False


def match_candidate(candidate, internship):
    eligible = (
        is_qualified(candidate, internship)
        and candidate["cgpa"] >= internship["min_cgpa"]
    )

    candidate_skills = {norm(s) for s in candidate["skills"]}
    required_skills = {norm(s) for s in internship["required_skills"]}

    matched = sorted(candidate_skills & required_skills)
    missing = sorted(required_skills - candidate_skills)

    text_a = " ".join(candidate["skills"])
    text_b = " ".join(internship["required_skills"])

    if text_a.strip() and text_b.strip():
        matrix = TfidfVectorizer().fit_transform([text_a, text_b])
        skill_score = float(
            cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        ) * 100
    else:
        skill_score = 0.0

    sector_score = (
        100 if norm(candidate["preferred_sector"]) == norm(internship["sector"])
        else 40
    )
    location_score = (
        100 if norm(candidate["preferred_location"]) == norm(internship["location"])
        else 50
    )
    experience_score = min(candidate["experience_months"] / 6, 1) * 100

    score = round(
        0.60 * skill_score
        + 0.15 * sector_score
        + 0.15 * location_score
        + 0.10 * experience_score,
        2,
    )

    reasons = [
        f"Skill similarity: {skill_score:.1f}/100 (60% weight).",
        "Preferred sector matches." if sector_score == 100
        else "Preferred sector differs.",
        "Preferred location matches." if location_score == 100
        else "Location differs from preference.",
        "Meets qualification and CGPA checks." if eligible
        else "Does not meet qualification or minimum CGPA requirements.",
    ]

    return MatchResult(
        internship_id=internship["id"],
        role=internship["role"],
        company=internship["company"],
        location=internship["location"],
        eligible=eligible,
        score=score,
        matched_skills=matched,
        missing_skills=missing,
        reasons=reasons,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="AI-Based Smart Allocation Engine",
    description="PostgreSQL-backed internship matching prototype",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "AI Smart Allocation Engine is running",
        "docs": "/docs",
    }


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/api/candidates", response_model=List[CandidateOut])
def get_candidates(db: Session = Depends(get_db)):
    return [
        candidate_dict(row)
        for row in db.query(CandidateRecord).order_by(CandidateRecord.id).all()
    ]


@app.post("/api/candidates", response_model=CandidateOut, status_code=201)
def create_candidate(payload: CandidateIn, db: Session = Depends(get_db)):
    row = CandidateRecord(
        name=payload.name,
        qualification=payload.qualification,
        skills=",".join(payload.skills),
        preferred_sector=payload.preferred_sector,
        preferred_location=payload.preferred_location,
        cgpa=payload.cgpa,
        experience_months=payload.experience_months,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return candidate_dict(row)


@app.put("/api/candidates/{candidate_id}", response_model=CandidateOut)
def update_candidate(
    candidate_id: int,
    payload: CandidateIn,
    db: Session = Depends(get_db),
):
    row = db.get(CandidateRecord, candidate_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    row.name = payload.name
    row.qualification = payload.qualification
    row.skills = ",".join(payload.skills)
    row.preferred_sector = payload.preferred_sector
    row.preferred_location = payload.preferred_location
    row.cgpa = payload.cgpa
    row.experience_months = payload.experience_months

    db.commit()
    db.refresh(row)
    return candidate_dict(row)


@app.get("/api/internships", response_model=List[InternshipOut])
def get_internships(db: Session = Depends(get_db)):
    return [
        internship_dict(row)
        for row in db.query(InternshipRecord).order_by(InternshipRecord.id).all()
    ]


@app.post("/api/internships", response_model=InternshipOut, status_code=201)
def create_internship(payload: InternshipIn, db: Session = Depends(get_db)):
    row = InternshipRecord(
        role=payload.role,
        company=payload.company,
        required_qualification=payload.required_qualification,
        required_skills=",".join(payload.required_skills),
        sector=payload.sector,
        location=payload.location,
        min_cgpa=payload.min_cgpa,
        seats=payload.seats,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return internship_dict(row)


@app.get("/api/candidates/{candidate_id}/matches",
         response_model=List[MatchResult])
def get_matches(
    candidate_id: int,
    eligible_only: bool = False,
    db: Session = Depends(get_db),
):
    row = db.get(CandidateRecord, candidate_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate = candidate_dict(row)
    internships = db.query(InternshipRecord).all()

    results = [
        match_candidate(candidate, internship_dict(item))
        for item in internships
    ]

    if eligible_only:
        results = [result for result in results if result.eligible]

    return sorted(
        results,
        key=lambda result: (result.eligible, result.score),
        reverse=True,
    )


@app.get("/api/admin/summary")
def admin_summary(db: Session = Depends(get_db)):
    candidates = db.query(CandidateRecord).all()
    internships = db.query(InternshipRecord).all()

    eligible_pairs = sum(
        1
        for candidate_row in candidates
        for internship_row in internships
        if match_candidate(
            candidate_dict(candidate_row),
            internship_dict(internship_row),
        ).eligible
    )

    return {
        "candidate_count": len(candidates),
        "internship_count": len(internships),
        "total_seats": sum(item.seats for item in internships),
        "eligible_pairs": eligible_pairs,
    }



@app.post("/api/allocate")
def automatic_allocation(db=Depends(get_db)):
    try:
        candidates_db = (
            db.query(CandidateRecord)
            .order_by(CandidateRecord.id)
            .all()
        )

        internships_db = (
            db.query(InternshipRecord)
            .filter(InternshipRecord.seats > 0)
            .order_by(InternshipRecord.id)
            .all()
        )

        def skill_list(value):
            if isinstance(value, list):
                return [
                    s.strip().lower()
                    for s in value
                    if s.strip()
                ]
            return [
                s.strip().lower()
                for s in (value or "").split(",")
                if s.strip()
            ]

        def compatible_qualification(candidate, internship):
            cq = (candidate.qualification or "").strip().lower()
            rq = (internship.required_qualification or "").strip().lower()
            return not rq or rq in cq or cq in rq

        options = []

        for candidate in candidates_db:
            for internship in internships_db:
                if candidate.cgpa < internship.min_cgpa:
                    continue

                if not compatible_qualification(candidate, internship):
                    continue

                candidate_skills = set(skill_list(candidate.skills))
                required_skills = set(skill_list(internship.required_skills))

                skill_score = (
                    len(candidate_skills & required_skills)
                    / len(required_skills) * 100
                    if required_skills else 0
                )

                sector_score = (
                    100
                    if (candidate.preferred_sector or "").strip().lower()
                    == (internship.sector or "").strip().lower()
                    else 0
                )

                location_score = (
                    100
                    if (candidate.preferred_location or "").strip().lower()
                    == (internship.location or "").strip().lower()
                    else 0
                )

                score = round(
                    skill_score * 0.70
                    + sector_score * 0.15
                    + location_score * 0.15,
                    2
                )

                options.append({
                    "candidate_id": candidate.id,
                    "candidate_name": candidate.name,
                    "internship_id": internship.id,
                    "role": internship.role,
                    "company": internship.company,
                    "score": score,
                    "matched_skills": sorted(
                        candidate_skills & required_skills
                    ),
                })

        # Reject low-compatibility matches before assigning seats.
        MIN_COMPATIBILITY_SCORE = 40.0
        options = [
            option for option in options
            if option["score"] >= MIN_COMPATIBILITY_SCORE
        ]

        # Best score first; one internship per candidate.
        options.sort(key=lambda item: item["score"], reverse=True)

        remaining_seats = {
            internship.id: internship.seats
            for internship in internships_db
        }

        assigned_candidates = set()
        allocations = []

        for option in options:
            candidate_id = option["candidate_id"]
            internship_id = option["internship_id"]

            if candidate_id in assigned_candidates:
                continue

            if remaining_seats.get(internship_id, 0) <= 0:
                continue

            allocations.append({
                **option,
                "status": "Allocated"
            })

            assigned_candidates.add(candidate_id)
            remaining_seats[internship_id] -= 1

        # Replace previous allocation results atomically.
        db.query(AllocationRecord).delete(
            synchronize_session=False
        )

        for item in allocations:
            db.add(AllocationRecord(
                candidate_id=item["candidate_id"],
                internship_id=item["internship_id"],
                score=item["score"],
                status=item["status"]
            ))

        db.commit()

        return {
            "total_candidates": len(candidates_db),
            "allocated_candidates": len(allocations),
            "unallocated_candidates": (
                len(candidates_db) - len(allocations)
            ),
            "allocations": allocations,
            "remaining_seats": remaining_seats,
            "minimum_compatibility_score": MIN_COMPATIBILITY_SCORE,
            "note": (
                "Allocation results saved to PostgreSQL. Matches below "
                f"{MIN_COMPATIBILITY_SCORE:.0f}% were excluded. "
                "Review recommendations before final decisions."
            )
        }

    except Exception:
        db.rollback()
        raise


@app.get("/api/allocations")
def get_allocations(db=Depends(get_db)):
    rows = (
        db.query(
            AllocationRecord.id,
            CandidateRecord.name.label("candidate_name"),
            InternshipRecord.role,
            InternshipRecord.company,
            AllocationRecord.score,
            AllocationRecord.status,
        )
        .join(
            CandidateRecord,
            CandidateRecord.id == AllocationRecord.candidate_id,
        )
        .join(
            InternshipRecord,
            InternshipRecord.id == AllocationRecord.internship_id,
        )
        .order_by(AllocationRecord.score.desc())
        .all()
    )

    return [
        {
            "id": row.id,
            "candidate_name": row.candidate_name,
            "role": row.role,
            "company": row.company,
            "score": row.score,
            "status": row.status,
        }
        for row in rows
    ]


# ==========================================
# ADMIN LOGIN AND AUTHENTICATION
# ==========================================

class AdminLogin(BaseModel):
    username: str
    password: str


security = HTTPBearer(auto_error=False)


def create_admin_token(username: str):
    secret = os.getenv("JWT_SECRET")

    if not secret:
        raise HTTPException(
            status_code=500,
            detail="JWT_SECRET is not configured"
        )

    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8)
    }

    return jwt.encode(payload, secret, algorithm="HS256")


def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Admin login required"
        )

    secret = os.getenv("JWT_SECRET")

    if not secret:
        raise HTTPException(
            status_code=500,
            detail="JWT_SECRET is not configured"
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            secret,
            algorithms=["HS256"]
        )

        username = payload.get("sub")

        if not username or username != os.getenv("ADMIN_USERNAME"):
            raise HTTPException(
                status_code=401,
                detail="Invalid admin token"
            )

        return username

    except jwt.PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )


@app.post("/api/admin/login")
def admin_login(payload: AdminLogin):

    admin_username = os.getenv("ADMIN_USERNAME")
    admin_password = os.getenv("ADMIN_PASSWORD")

    if not admin_username or not admin_password:
        raise HTTPException(
            status_code=500,
            detail="Admin credentials are not configured"
        )

    if not (
        hmac.compare_digest(payload.username, admin_username)
        and hmac.compare_digest(payload.password, admin_password)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    return {
        "access_token": create_admin_token(payload.username),
        "token_type": "bearer"
    }


# ==========================================
# ADMIN-ONLY DELETE ROUTES
# ==========================================

@app.delete("/api/candidates/{candidate_id}")
def delete_candidate(
    candidate_id: int,
    admin: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    candidate = db.get(CandidateRecord, candidate_id)

    if candidate is None:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found"
        )

    db.query(AllocationRecord).filter(
        AllocationRecord.candidate_id == candidate_id
    ).delete(synchronize_session=False)

    db.delete(candidate)
    db.commit()

    return {"message": "Candidate deleted successfully"}


@app.delete("/api/internships/{internship_id}")
def delete_internship(
    internship_id: int,
    admin: str = Depends(require_admin),
    db: Session = Depends(get_db)
):
    internship = db.get(InternshipRecord, internship_id)

    if internship is None:
        raise HTTPException(
            status_code=404,
            detail="Internship not found"
        )

    db.query(AllocationRecord).filter(
        AllocationRecord.internship_id == internship_id
    ).delete(synchronize_session=False)

    db.delete(internship)
    db.commit()

    return {"message": "Internship deleted successfully"}
