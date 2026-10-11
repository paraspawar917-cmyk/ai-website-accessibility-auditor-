from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

import os
import sys

# Ensure both current directory and parent directory are on sys.path
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.abspath(os.path.join(_current_dir, ".."))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from backend.database import (
        get_db,
        init_db,
        User,
        Website,
        Scan,
        AccessibilityIssue,
        ScanHistory,
    )
    from backend.scanner import audit_website, normalize_target_url
except (ModuleNotFoundError, ImportError):
    from database import (
        get_db,
        init_db,
        User,
        Website,
        Scan,
        AccessibilityIssue,
        ScanHistory,
    )
    from scanner import audit_website, normalize_target_url


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables and default seed user on startup
    try:
        init_db()
    except Exception as exc:
        print(f"Database initialization error: {exc}")
    yield


app = FastAPI(
    title="AccessAI Accessibility Auditor API",
    description="Backend API for AI Website Accessibility Auditing and WCAG conformance evaluation.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend Vite development server and standard origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuditRequest(BaseModel):
    url: str


class IssueDTO(BaseModel):
    id: int
    rule_code: Optional[str] = None
    title: str
    description: Optional[str] = None
    severity: str
    wcag: Optional[str] = None
    element: Optional[str] = None
    element_html: Optional[str] = None
    recommendation: Optional[str] = None
    page_url: Optional[str] = None


class SummaryDTO(BaseModel):
    score: Optional[int] = None
    total: int
    critical: int
    serious: int
    moderate: int
    minor: int
    passed: int


class AuditResponse(BaseModel):
    scan_id: int
    url: str
    summary: SummaryDTO
    issues: List[IssueDTO]


@app.get("/")
def home():
    return {
        "name": "AccessAI Accessibility Auditor Backend",
        "status": "online",
        "version": "1.0.0",
    }


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        user_count = db.query(User).count()
        return {
            "status": "healthy",
            "database": "connected",
            "users_count": user_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "database": f"error: {str(exc)}",
            "timestamp": datetime.utcnow().isoformat(),
        }


@app.post("/api/audit", response_model=AuditResponse)
def run_audit(payload: AuditRequest, db: Session = Depends(get_db)):
    raw_url = payload.url.strip()
    if not raw_url:
        raise HTTPException(status_code=400, detail="URL cannot be empty")

    start_time = datetime.utcnow()

    # 1. Execute live accessibility scan
    try:
        scan_result = audit_website(raw_url)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Audit failed for website: {str(exc)}"
        )

    final_url = scan_result["url"]
    summary = scan_result["summary"]
    issues = scan_result["issues"]
    end_time = datetime.utcnow()

    # 2. Store results into MySQL / Database
    try:
        # Get or create default user
        user = db.query(User).first()
        if not user:
            user = User(
                full_name="Default Auditor",
                email="admin@accessai.local",
                password_hash="demo_hash",
            )
            db.add(user)
            db.flush()

        # Find or create website
        website = db.query(Website).filter(Website.website_url == final_url).first()
        if not website:
            from urllib.parse import urlparse
            hostname = urlparse(final_url).hostname or final_url
            website = Website(
                user_id=user.user_id,
                website_name=hostname,
                website_url=final_url,
            )
            db.add(website)
            db.flush()

        # Create scan record
        scan = Scan(
            website_id=website.website_id,
            scan_status="completed",
            accessibility_score=summary["score"],
            total_issues=summary["total"],
            critical_issues=summary["critical"],
            serious_issues=summary["serious"],
            moderate_issues=summary["moderate"],
            minor_issues=summary["minor"],
            started_at=start_time,
            completed_at=end_time,
        )
        db.add(scan)
        db.flush()

        # Create issue records
        db_issues = []
        for issue in issues:
            raw_sev = issue.get("raw_severity", issue["severity"].lower())
            db_issue = AccessibilityIssue(
                scan_id=scan.scan_id,
                rule_code=issue.get("rule_code"),
                issue_title=issue["title"],
                description=issue.get("description"),
                severity=raw_sev,
                element_selector=issue.get("element"),
                element_html=issue.get("element_html"),
                page_url=final_url,
                recommendation=issue.get("recommendation"),
                wcag_reference=issue.get("wcag"),
            )
            db_issues.append(db_issue)

        db.add_all(db_issues)

        # Create scan history record
        history = ScanHistory(
            website_id=website.website_id,
            scan_id=scan.scan_id,
            accessibility_score=summary["score"],
            total_issues=summary["total"],
            scanned_at=end_time,
        )
        db.add(history)

        db.commit()

        # Attach real database scan_id
        return {
            "scan_id": scan.scan_id,
            "url": final_url,
            "summary": summary,
            "issues": issues,
        }

    except Exception as exc:
        db.rollback()
        # Even if DB storage encounters an issue, return the valid audit to the user
        print(f"Database write error: {exc}")
        return {
            "scan_id": 0,
            "url": final_url,
            "summary": summary,
            "issues": issues,
        }


@app.get("/api/scans")
def list_scans(limit: int = 10, db: Session = Depends(get_db)):
    """Fetch past scans from the database."""
    try:
        scans = (
            db.query(Scan)
            .join(Website)
            .order_by(desc(Scan.created_at))
            .limit(limit)
            .all()
        )
        results = []
        for s in scans:
            results.append({
                "scan_id": s.scan_id,
                "website_url": s.website.website_url if s.website else "",
                "website_name": s.website.website_name if s.website else "",
                "accessibility_score": float(s.accessibility_score) if s.accessibility_score else None,
                "total_issues": s.total_issues,
                "critical_issues": s.critical_issues,
                "serious_issues": s.serious_issues,
                "moderate_issues": s.moderate_issues,
                "minor_issues": s.minor_issues,
                "scan_status": s.scan_status,
                "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S") if s.created_at else "",
            })
        return results
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/scans/{scan_id}")
def get_scan_details(scan_id: int, db: Session = Depends(get_db)):
    """Fetch specific scan and its associated accessibility issues."""
    scan = db.query(Scan).filter(Scan.scan_id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    issues_list = []
    for idx, iss in enumerate(scan.issues, start=1):
        issues_list.append({
            "id": iss.issue_id,
            "rule_code": iss.rule_code,
            "title": iss.issue_title,
            "description": iss.description,
            "severity": iss.severity.capitalize() if iss.severity else "Moderate",
            "wcag": iss.wcag_reference,
            "element": iss.element_selector,
            "element_html": iss.element_html,
            "recommendation": iss.recommendation,
            "page_url": iss.page_url,
        })

    summary = {
        "score": int(scan.accessibility_score) if scan.accessibility_score else 0,
        "total": scan.total_issues or len(issues_list),
        "critical": scan.critical_issues or 0,
        "serious": scan.serious_issues or 0,
        "moderate": scan.moderate_issues or 0,
        "minor": scan.minor_issues or 0,
        "passed": max(12, 35 - (scan.total_issues or 0)),
    }

    return {
        "scan_id": scan.scan_id,
        "url": scan.website.website_url if scan.website else "",
        "summary": summary,
        "issues": issues_list,
        "created_at": scan.created_at.isoformat() if scan.created_at else "",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
