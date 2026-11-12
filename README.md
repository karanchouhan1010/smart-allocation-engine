# AI-Based Smart Allocation Engine for PM Internship Scheme

A beginner-friendly web MVP with:
- Candidate and internship sample data
- Eligibility filtering
- AI-style skill matching using TF-IDF + cosine similarity
- Weighted compatibility score and ranked recommendations
- FastAPI backend and HTML/CSS/JavaScript frontend

## Requirements
- Python 3.10+
- VS Code recommended

## Run the backend
Open a terminal in this folder:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r backend/requirements.txt
uvicorn backend.main:app --reload
```

Backend: http://127.0.0.1:8000  
API docs: http://127.0.0.1:8000/docs

## Run the frontend
Open `frontend/index.html` in a browser. If browser restrictions interfere, use the VS Code Live Server extension.

The frontend calls the API at `http://127.0.0.1:8000`.

## Current MVP limitations
- Uses in-memory sample data (resets when server restarts).
- No login, database, or official PM Internship Scheme integration yet.
- Matching scores are decision-support estimates, not official selection decisions.
- Do not enter real personal data into this prototype.

## Suggested next milestones
1. Verify this MVP runs locally.
2. Add create/edit forms for candidates and internships.
3. Add PostgreSQL persistence.
4. Add admin authentication and allocation constraints.
5. Add testing, audit logs, and deployment.
