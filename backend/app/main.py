import io
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path for direct execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.analysis import run_full_analysis
from app.auth import (
    create_access_token,
    get_current_user,
    get_optional_user,
    hash_password,
    require_admin,
    verify_password,
)
from app.db import (
    clear_transaction_logs,
    create_category,
    create_issue,
    create_issues_from_analysis,
    create_milestone,
    create_risk,
    create_stakeholder,
    create_task,
    create_user,
    delete_analysis_by_id,
    delete_issue,
    delete_milestone,
    delete_risk,
    delete_stakeholder,
    delete_task,
    get_all_analyses,
    get_analysis_by_id,
    get_categories,
    get_database_overview,
    get_issue_stats,
    get_issues,
    get_milestones,
    get_project,
    get_risks,
    get_stakeholders,
    get_table_rows,
    get_tasks,
    get_transaction_logs,
    get_user_by_username,
    init_db,
    list_users,
    log_transaction,
    save_analysis,
    simulate_database_transaction,
    update_issue,
    update_milestone,
    update_project,
    update_risk,
    update_task,
)
from app.report import build_pdf_report

app = FastAPI(
    title="College Event Feedback Analyzer (Event Insight)",
    description="Integrated Academic Mini-Project covering Text Media Analysis, IT Project Management, and Enterprise Systems.",
    version="2.0.0",
)

# Startup Hook
@app.on_event("startup")
def on_startup():
    init_db()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _read_csv(file_bytes: bytes) -> pd.DataFrame:
    try:
        return pd.read_csv(io.BytesIO(file_bytes))
    except Exception:
        try:
            return pd.read_csv(io.BytesIO(file_bytes), encoding="latin-1")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")


# ==============================================================================
# Pydantic Request Schemas
# ==============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = Field("viewer", pattern="^(admin|viewer)$")


class ProjectUpdateRequest(BaseModel):
    name: str
    start_date: str
    end_date: str
    status: str = Field("Active", pattern="^(Planning|Active|Completed|On Hold)$")
    description: Optional[str] = ""


class TaskCreateRequest(BaseModel):
    title: str
    status: str = Field("todo", pattern="^(todo|in-progress|done)$")
    due_date: Optional[str] = None
    assigned_to: Optional[str] = None


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(todo|in-progress|done)$")
    due_date: Optional[str] = None
    assigned_to: Optional[str] = None


class MilestoneCreateRequest(BaseModel):
    title: str
    target_date: str
    completed: bool = False


class MilestoneUpdateRequest(BaseModel):
    title: Optional[str] = None
    target_date: Optional[str] = None
    completed: Optional[bool] = None


class RiskCreateRequest(BaseModel):
    description: str
    likelihood: str = Field(..., pattern="^(Low|Medium|High)$")
    impact: str = Field(..., pattern="^(Low|Medium|High)$")
    mitigation: str
    status: str = Field("Open", pattern="^(Open|Mitigated|Closed)$")


class RiskUpdateRequest(BaseModel):
    description: Optional[str] = None
    likelihood: Optional[str] = Field(None, pattern="^(Low|Medium|High)$")
    impact: Optional[str] = Field(None, pattern="^(Low|Medium|High)$")
    mitigation: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(Open|Mitigated|Closed)$")


class StakeholderCreateRequest(BaseModel):
    name: str
    role: str
    contact: str


class CategoryCreateRequest(BaseModel):
    name: str


class IssueCreateRequest(BaseModel):
    analysis_id: Optional[int] = None
    source_feedback_text: str
    category: str = "General"
    priority: str = Field("Medium", pattern="^(Low|Medium|High|Critical)$")
    status: str = Field("new", pattern="^(new|in-progress|resolved)$")


class IssueUpdateRequest(BaseModel):
    category: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(Low|Medium|High|Critical)$")
    status: Optional[str] = Field(None, pattern="^(new|in-progress|resolved)$")


# ==============================================================================
# Health & General Routes
# ==============================================================================

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Event Insight", "version": "2.0.0"}


# ==============================================================================
# Authentication & User Management Routes (Enterprise Subject)
# ==============================================================================

@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    token = create_access_token(data={"sub": str(user["id"]), "username": user["username"], "role": user["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
        },
    }


@app.get("/api/auth/me")
def get_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "username": current_user["username"],
        "role": current_user["role"],
    }


@app.get("/api/auth/users")
def get_users(admin: Dict[str, Any] = Depends(require_admin)):
    return list_users()


@app.post("/api/auth/users", status_code=status.HTTP_201_CREATED)
def create_new_user(req: CreateUserRequest, admin: Dict[str, Any] = Depends(require_admin)):
    existing = get_user_by_username(req.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username is already registered.")

    hashed = hash_password(req.password)
    new_id = create_user(req.username, hashed, req.role)
    return {"id": new_id, "username": req.username, "role": req.role}


# ==============================================================================
# Text Media Analysis Routes (Existing Core NLP Subject)
# ==============================================================================

@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    event_name: str = Form("Untitled Event"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_user),
):
    contents = await file.read()
    df = _read_csv(contents)
    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file has no rows.")

    result = run_full_analysis(df)
    clean_event_name = (event_name or "Untitled Event").strip() or "Untitled Event"
    user_id = current_user["id"] if current_user else None

    row_id = save_analysis(
        event_name=clean_event_name,
        total_responses=result.get("total_responses", int(len(df))),
        analysis_data=result,
        created_by=user_id,
    )
    result["id"] = row_id
    result["event_name"] = clean_event_name
    return result


@app.get("/api/history")
@app.get("/api/analyses")
def history():
    return get_all_analyses()


@app.get("/api/history/{analysis_id}")
@app.get("/api/analyses/{analysis_id}")
def history_item(analysis_id: int):
    item = get_analysis_by_id(analysis_id)
    if not item:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return item


@app.delete("/api/history/{analysis_id}")
@app.delete("/api/analyses/{analysis_id}")
def delete_history(analysis_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    success = delete_analysis_by_id(analysis_id)
    if not success:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return {"status": "ok", "message": f"Analysis {analysis_id} deleted."}


@app.post("/api/report")
async def report(file: UploadFile = File(...), event_name: str = Form("College Event")):
    contents = await file.read()
    df = _read_csv(contents)
    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file has no rows.")
    analysis = run_full_analysis(df)
    pdf_bytes = build_pdf_report(analysis, event_name=event_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{event_name.replace(" ", "_")}_feedback_report.pdf"'},
    )


@app.get("/api/analyses/{analysis_id}/report")
def get_analysis_pdf_report(analysis_id: int):
    row = get_analysis_by_id(analysis_id)
    if not row:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    event_name = row.get("event_name", "College Event")
    pdf_bytes = build_pdf_report(row, event_name=event_name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{event_name.replace(" ", "_")}_feedback_report.pdf"'},
    )


# ==============================================================================
# IT Project Management Routes (IT PM Subject)
# ==============================================================================

@app.get("/api/project")
def get_project_details():
    return get_project()


@app.put("/api/project")
def update_project_details(req: ProjectUpdateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    success = update_project(
        name=req.name,
        start_date=req.start_date,
        end_date=req.end_date,
        status=req.status,
        description=req.description,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update project details.")
    return get_project()


# --- Tasks ---
@app.get("/api/tasks")
def list_tasks():
    return get_tasks()


@app.post("/api/tasks", status_code=status.HTTP_201_CREATED)
def add_task(req: TaskCreateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    task_id = create_task(
        title=req.title,
        status=req.status,
        due_date=req.due_date,
        assigned_to=req.assigned_to,
    )
    return {"id": task_id, "message": "Task created successfully"}


@app.patch("/api/tasks/{task_id}")
def edit_task(task_id: int, req: TaskUpdateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    updates = req.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")
    success = update_task(task_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"status": "ok", "message": f"Task {task_id} updated."}


@app.delete("/api/tasks/{task_id}")
def remove_task(task_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    success = delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"status": "ok", "message": f"Task {task_id} deleted."}


# --- Milestones ---
@app.get("/api/milestones")
def list_milestones():
    return get_milestones()


@app.post("/api/milestones", status_code=status.HTTP_201_CREATED)
def add_milestone(req: MilestoneCreateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    ms_id = create_milestone(
        title=req.title,
        target_date=req.target_date,
        completed=1 if req.completed else 0,
    )
    return {"id": ms_id, "message": "Milestone created successfully"}


@app.patch("/api/milestones/{milestone_id}")
def edit_milestone(milestone_id: int, req: MilestoneUpdateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    updates = req.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")
    success = update_milestone(milestone_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Milestone not found.")
    return {"status": "ok", "message": f"Milestone {milestone_id} updated."}


@app.delete("/api/milestones/{milestone_id}")
def remove_milestone(milestone_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    success = delete_milestone(milestone_id)
    if not success:
        raise HTTPException(status_code=404, detail="Milestone not found.")
    return {"status": "ok", "message": f"Milestone {milestone_id} deleted."}


# --- Risks ---
@app.get("/api/risks")
def list_risks():
    return get_risks()


@app.post("/api/risks", status_code=status.HTTP_201_CREATED)
def add_risk(req: RiskCreateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    risk_id = create_risk(
        description=req.description,
        likelihood=req.likelihood,
        impact=req.impact,
        mitigation=req.mitigation,
        status=req.status,
    )
    return {"id": risk_id, "message": "Risk created successfully"}


@app.patch("/api/risks/{risk_id}")
def edit_risk(risk_id: int, req: RiskUpdateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    updates = req.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")
    success = update_risk(risk_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Risk not found.")
    return {"status": "ok", "message": f"Risk {risk_id} updated."}


@app.delete("/api/risks/{risk_id}")
def remove_risk(risk_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    success = delete_risk(risk_id)
    if not success:
        raise HTTPException(status_code=404, detail="Risk not found.")
    return {"status": "ok", "message": f"Risk {risk_id} deleted."}


# --- Stakeholders ---
@app.get("/api/stakeholders")
def list_stakeholders():
    return get_stakeholders()


@app.post("/api/stakeholders", status_code=status.HTTP_201_CREATED)
def add_stakeholder(req: StakeholderCreateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    sh_id = create_stakeholder(name=req.name, role=req.role, contact=req.contact)
    return {"id": sh_id, "message": "Stakeholder created successfully"}


@app.delete("/api/stakeholders/{stakeholder_id}")
def remove_stakeholder(stakeholder_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    success = delete_stakeholder(stakeholder_id)
    if not success:
        raise HTTPException(status_code=404, detail="Stakeholder not found.")
    return {"status": "ok", "message": f"Stakeholder {stakeholder_id} deleted."}


# ==============================================================================
# Enterprise System Module (Negative Sentiment Issues & Categories)
# ==============================================================================

@app.get("/api/categories")
def list_categories():
    return get_categories()


@app.post("/api/categories", status_code=status.HTTP_201_CREATED)
def add_category(req: CategoryCreateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    cat_id = create_category(req.name)
    return {"id": cat_id, "name": req.name}


@app.get("/api/issues/stats")
def issue_statistics(analysis_id: Optional[int] = Query(None)):
    return get_issue_stats(analysis_id=analysis_id)


@app.get("/api/issues")
def list_issues(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    analysis_id: Optional[int] = Query(None),
):
    return get_issues(status=status, priority=priority, category=category, analysis_id=analysis_id)


@app.post("/api/analyses/{analysis_id}/create-issues")
def generate_issues_from_analysis(
    analysis_id: int,
    threshold: float = Query(-0.30, description="Compound score cutoff for negative sentiment"),
    admin: Dict[str, Any] = Depends(require_admin),
):
    try:
        result = create_issues_from_analysis(analysis_id, threshold=threshold)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate issues: {e}")


@app.post("/api/issues", status_code=status.HTTP_201_CREATED)
def add_issue(req: IssueCreateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    issue_id = create_issue(
        analysis_id=req.analysis_id,
        source_feedback_text=req.source_feedback_text,
        category=req.category,
        priority=req.priority,
        status=req.status,
    )
    return {"id": issue_id, "message": "Issue created successfully"}


@app.patch("/api/issues/{issue_id}")
def edit_issue(issue_id: int, req: IssueUpdateRequest, admin: Dict[str, Any] = Depends(require_admin)):
    updates = req.dict(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided to update.")
    success = update_issue(issue_id, updates)
    if not success:
        raise HTTPException(status_code=404, detail="Issue not found.")
    return {"status": "ok", "message": f"Issue {issue_id} updated."}


@app.delete("/api/issues/{issue_id}")
def remove_issue(issue_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    success = delete_issue(issue_id)
    if not success:
        raise HTTPException(status_code=404, detail="Issue not found.")
    return {"status": "ok", "message": f"Issue {issue_id} deleted."}


# ==============================================================================
# Database Introspection & Live Transaction Logs API
# ==============================================================================

@app.get("/api/database/overview")
def api_database_overview():
    """Retrieve database schema, storage footprint, and table stats."""
    try:
        return get_database_overview()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database inspection failed: {e}")


@app.get("/api/database/tables/{table_name}")
def api_database_table_rows(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    search: Optional[str] = Query(None),
):
    """Retrieve paginated live records from any table."""
    try:
        return get_table_rows(table_name=table_name, page=page, page_size=page_size, search=search)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch table records: {e}")


@app.get("/api/database/transactions")
def api_database_transactions(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
    table_name: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """Retrieve real-time transaction logs and audit journal entries."""
    try:
        return get_transaction_logs(limit=limit, offset=offset, action=action, table_name=table_name, search=search)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch transaction logs: {e}")


@app.post("/api/database/transactions/simulate")
def api_database_simulate_transaction(action_type: Optional[str] = Query(None)):
    """Simulate a live transaction to demonstrate real-time audit streaming."""
    try:
        return simulate_database_transaction(action_type=action_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to simulate transaction: {e}")


@app.delete("/api/database/transactions")
def api_database_clear_transactions():
    """Clear transaction logs (resets to initial audit state)."""
    try:
        clear_transaction_logs()
        return {"status": "ok", "message": "Transaction logs reset successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset transaction logs: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8800, reload=True)


