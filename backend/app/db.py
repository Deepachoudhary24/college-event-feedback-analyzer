import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "analyzer.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initialize the full multi-module SQLite schema and seed defaults if empty."""
    from app.auth import hash_password

    with get_connection() as conn:
        # 1. Users Table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'viewer')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 2. Analyses Table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_name TEXT NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_responses INTEGER NOT NULL,
                analysis_json TEXT NOT NULL,
                created_by INTEGER REFERENCES users(id)
            );
            """
        )

        # Check if created_by column exists on existing analyses table (non-destructive migration)
        cursor = conn.execute("PRAGMA table_info(analyses);")
        columns = [row["name"] for row in cursor.fetchall()]
        if "created_by" not in columns:
            conn.execute("ALTER TABLE analyses ADD COLUMN created_by INTEGER REFERENCES users(id);")

        # 3. Project Singleton Table (ID=1)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS project (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                name TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Planning', 'Active', 'Completed', 'On Hold')),
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 4. Tasks Table (IT PM Kanban)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL DEFAULT 1 REFERENCES project(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo', 'in-progress', 'done')),
                due_date TEXT,
                assigned_to TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 5. Milestones Table (IT PM Schedule)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL DEFAULT 1 REFERENCES project(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                target_date TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0, 1)),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 6. Risks Table (IT PM Risk Register)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS risks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL DEFAULT 1 REFERENCES project(id) ON DELETE CASCADE,
                description TEXT NOT NULL,
                likelihood TEXT NOT NULL CHECK(likelihood IN ('Low', 'Medium', 'High')),
                impact TEXT NOT NULL CHECK(impact IN ('Low', 'Medium', 'High')),
                mitigation TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open', 'Mitigated', 'Closed')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 7. Stakeholders Table (IT PM Stakeholder Directory)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stakeholders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL DEFAULT 1 REFERENCES project(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                contact TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 8. Categories Table (Enterprise Lookup)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
            """
        )

        # 9. Issues Table (Enterprise Negative Feedback Ticketing)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id INTEGER REFERENCES analyses(id) ON DELETE CASCADE,
                source_feedback_text TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'General',
                priority TEXT NOT NULL DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High', 'Critical')),
                status TEXT NOT NULL DEFAULT 'new' CHECK(status IN ('new', 'in-progress', 'resolved')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # 10. Transaction Logs Table (Live DB Audit Stream)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transaction_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL CHECK(action IN ('INSERT', 'UPDATE', 'DELETE', 'SELECT', 'PRAGMA', 'TRANSACTION', 'MIGRATION')),
                table_name TEXT NOT NULL,
                summary TEXT NOT NULL,
                details TEXT,
                status TEXT NOT NULL DEFAULT 'COMMITTED',
                duration_ms REAL DEFAULT 0.0,
                client_ip TEXT DEFAULT '127.0.0.1'
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_trans_logs_id ON transaction_logs(id DESC);")

        # ------------------------------------------------------------------
        # Seed Initial Data (Only if tables are empty)
        # ------------------------------------------------------------------

        # Users Seed
        user_count = conn.execute("SELECT COUNT(*) FROM users;").fetchone()[0]
        if user_count == 0:
            admin_pwd = os.environ.get("ADMIN_PASSWORD", "Admin@Event123")
            admin_hash = hash_password(admin_pwd)
            viewer_hash = hash_password("Viewer@Event123")
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?);",
                ("admin", admin_hash, "admin"),
            )
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?);",
                ("viewer", viewer_hash, "viewer"),
            )
            print(f"[Event Insight] Seeded default users: 'admin' (password: '{admin_pwd}') & 'viewer' (password: 'Viewer@Event123')")

        # Project Seed
        proj_count = conn.execute("SELECT COUNT(*) FROM project;").fetchone()[0]
        if proj_count == 0:
            conn.execute(
                """
                INSERT INTO project (id, name, start_date, end_date, status, description)
                VALUES (1, ?, ?, ?, ?, ?);
                """,
                (
                    "Campus Tech Symposium 2026 Feedback Drive",
                    "2026-09-01",
                    "2026-10-15",
                    "Active",
                    "Integrated feedback collection, sentiment evaluation, and institutional service improvement initiative.",
                ),
            )

        # Categories Seed
        cat_count = conn.execute("SELECT COUNT(*) FROM categories;").fetchone()[0]
        if cat_count == 0:
            default_categories = [
                "Audio/Visual & Tech",
                "Catering & Hospitality",
                "Facility & Logistics",
                "Scheduling & Content",
                "General",
            ]
            for cat in default_categories:
                conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?);", (cat,))

        # Tasks Seed
        task_count = conn.execute("SELECT COUNT(*) FROM tasks;").fetchone()[0]
        if task_count == 0:
            starter_tasks = [
                (1, "Finalize feedback survey questionnaire & rating scales", "done", "2026-09-05", "Event Committee"),
                (1, "Distribute QR code and digital survey to attendees", "done", "2026-09-15", "Student Volunteers"),
                (1, "Run automated NLP sentiment and topic modeling", "in-progress", "2026-09-25", "Lead Data Analyst"),
                (1, "Triage negative sentiment feedback into enterprise issues", "in-progress", "2026-09-28", "Quality Assurance Lead"),
                (1, "Compile executive institutional audit PDF report", "todo", "2026-10-05", "Project Manager"),
                (1, "Hold post-event corrective action stakeholder review", "todo", "2026-10-12", "Steering Committee"),
            ]
            conn.executemany(
                "INSERT INTO tasks (project_id, title, status, due_date, assigned_to) VALUES (?, ?, ?, ?, ?);",
                starter_tasks,
            )

        # Milestones Seed
        ms_count = conn.execute("SELECT COUNT(*) FROM milestones;").fetchone()[0]
        if ms_count == 0:
            starter_milestones = [
                (1, "Feedback Ingestion Portal Launch", "2026-09-15", 1),
                (1, "Survey Data Ingestion & Sentiment Baseline", "2026-09-24", 1),
                (1, "Negative Feedback Issue Triage & Routing", "2026-09-30", 0),
                (1, "Departmental Corrective Action Review", "2026-10-08", 0),
                (1, "Executive Sign-Off & Project Closure", "2026-10-15", 0),
            ]
            conn.executemany(
                "INSERT INTO milestones (project_id, title, target_date, completed) VALUES (?, ?, ?, ?);",
                starter_milestones,
            )

        # Risks Seed
        risk_count = conn.execute("SELECT COUNT(*) FROM risks;").fetchone()[0]
        if risk_count == 0:
            starter_risks = [
                (
                    1,
                    "Low survey response rate leading to skewed sentiment analysis sample",
                    "Medium",
                    "High",
                    "Broadcast reminders, offer certificate vouchers, and deploy physical QR stands at exit gates",
                    "Mitigated",
                ),
                (
                    1,
                    "Audio reverberation and microphone feedback in main auditorium during keynotes",
                    "High",
                    "Medium",
                    "Conduct AV sound checks 2 hours prior and stage backup wireless handheld mics",
                    "Open",
                ),
                (
                    1,
                    "Delayed resolution of attendee comfort complaints (hall temperature and seating)",
                    "Low",
                    "Medium",
                    "Route facility issues directly into Campus Facilities dispatch with 24h SLA",
                    "Open",
                ),
            ]
            conn.executemany(
                "INSERT INTO risks (project_id, description, likelihood, impact, mitigation, status) VALUES (?, ?, ?, ?, ?, ?);",
                starter_risks,
            )

        # Stakeholders Seed
        sh_count = conn.execute("SELECT COUNT(*) FROM stakeholders;").fetchone()[0]
        if sh_count == 0:
            starter_stakeholders = [
                (1, "Dr. Sarah Jenkins", "Dean of Student Affairs", "s.jenkins@college.edu"),
                (1, "Prof. Rajesh Nair", "Head of IT & AV Infrastructure", "r.nair@college.edu"),
                (1, "Ananya Verma", "Student Council President", "studentcouncil@college.edu"),
                (1, "Marcus Chen", "Campus Facilities & Logistics Manager", "m.chen@college.edu"),
            ]
            conn.executemany(
                "INSERT INTO stakeholders (project_id, name, role, contact) VALUES (?, ?, ?, ?);",
                starter_stakeholders,
            )

        # 10. Transaction Logs Seed
        tl_count = conn.execute("SELECT COUNT(*) FROM transaction_logs;").fetchone()[0]
        if tl_count == 0:
            starter_logs = [
                ("MIGRATION", "schema", "Initialized SQLite relational schema & WAL journal mode", None, "COMMITTED", 3.2),
                ("INSERT", "users", "Provisioned default Administrator & Viewer credentials", json.dumps({"users": ["admin", "viewer"]}), "COMMITTED", 1.8),
                ("INSERT", "project", "Established single-row IT PM project governance baseline", json.dumps({"project_id": 1}), "COMMITTED", 0.9),
                ("INSERT", "tasks", "Populated initial WBS Kanban sprint backlog tasks", json.dumps({"count": 6}), "COMMITTED", 2.1),
                ("INSERT", "milestones", "Scheduled symposium delivery milestone deadlines", json.dumps({"count": 5}), "COMMITTED", 1.4),
                ("INSERT", "risks", "Recorded institutional PMBOK threats into Risk Register", json.dumps({"count": 3}), "COMMITTED", 1.1),
                ("INSERT", "stakeholders", "Synchronized governance directory stakeholder records", json.dumps({"count": 4}), "COMMITTED", 1.5),
                ("TRANSACTION", "categories", "Configured enterprise department lookup taxonomy", json.dumps({"count": 5}), "COMMITTED", 0.8),
            ]
            conn.executemany(
                "INSERT INTO transaction_logs (action, table_name, summary, details, status, duration_ms) VALUES (?, ?, ?, ?, ?, ?);",
                starter_logs,
            )

        conn.commit()


# ==============================================================================
# Users Management
# ==============================================================================

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT id, username, role, created_at FROM users WHERE id = ?;", (user_id,)).fetchone()
        return dict(row) if row else None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, role, created_at FROM users WHERE username = ?;",
            (username.strip(),),
        ).fetchone()
        return dict(row) if row else None


def create_user(username: str, password_hash: str, role: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?);",
            (username.strip(), password_hash, role.strip()),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_users() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT id, username, role, created_at FROM users ORDER BY id ASC;").fetchall()
        return [dict(row) for row in rows]


# ==============================================================================
# Analyses Management
# ==============================================================================

def save_analysis(
    event_name: str,
    total_responses: int,
    analysis_data: Dict[str, Any],
    created_by: Optional[int] = None,
) -> int:
    """Save an analysis result blob and return the new row ID."""
    clean_event_name = (event_name or "Untitled Event").strip() or "Untitled Event"
    json_str = json.dumps(analysis_data, ensure_ascii=False)
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO analyses (event_name, total_responses, analysis_json, created_by)
            VALUES (?, ?, ?, ?);
            """,
            (clean_event_name, total_responses, json_str, created_by),
        )
        conn.commit()
        return int(cursor.lastrowid)


def get_all_analyses() -> List[Dict[str, Any]]:
    """Return summary metadata for all saved analyses, newest first."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT a.id, a.event_name, a.uploaded_at, a.total_responses, a.created_by, u.username as creator_name
            FROM analyses a
            LEFT JOIN users u ON a.created_by = u.id
            ORDER BY a.id DESC;
            """
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "event_name": row["event_name"],
                "uploaded_at": str(row["uploaded_at"]),
                "total_responses": row["total_responses"],
                "created_by": row["created_by"],
                "creator_name": row["creator_name"] or "System / Anonymous",
            }
            for row in rows
        ]


def get_analysis_by_id(analysis_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve full analysis JSON blob by ID and return deserialized dict."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT a.id, a.event_name, a.uploaded_at, a.total_responses, a.analysis_json, a.created_by, u.username as creator_name
            FROM analyses a
            LEFT JOIN users u ON a.created_by = u.id
            WHERE a.id = ?;
            """,
            (analysis_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None

        data = json.loads(row["analysis_json"])
        data["id"] = row["id"]
        data["event_name"] = row["event_name"]
        data["uploaded_at"] = str(row["uploaded_at"])
        data["created_by"] = row["created_by"]
        data["creator_name"] = row["creator_name"] or "System / Anonymous"
        return data


def delete_analysis_by_id(analysis_id: int) -> bool:
    """Delete an analysis row by ID. Cascades to associated issues."""
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM analyses WHERE id = ?;", (analysis_id,))
        conn.commit()
        return cursor.rowcount > 0


# ==============================================================================
# IT Project Management Module
# ==============================================================================

def get_project() -> Dict[str, Any]:
    """Retrieve the single project entity alongside computed summary KPIs."""
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM project WHERE id = 1;").fetchone()
        if not row:
            # Fallback if somehow missing
            conn.execute(
                "INSERT OR IGNORE INTO project (id, name, start_date, end_date, status, description) VALUES (1, 'College Feedback Project', '2026-09-01', '2026-10-15', 'Active', 'Event Feedback Collection');"
            )
            conn.commit()
            row = conn.execute("SELECT * FROM project WHERE id = 1;").fetchone()

        project_data = dict(row)

        # Calculate progress KPIs
        tasks = conn.execute("SELECT status, count(*) as cnt FROM tasks WHERE project_id = 1 GROUP BY status;").fetchall()
        task_stats = {r["status"]: r["cnt"] for r in tasks}
        total_tasks = sum(task_stats.values())
        completed_tasks = task_stats.get("done", 0)

        milestones = conn.execute("SELECT completed, count(*) as cnt FROM milestones WHERE project_id = 1 GROUP BY completed;").fetchall()
        ms_stats = {r["completed"]: r["cnt"] for r in milestones}
        total_milestones = sum(ms_stats.values())
        completed_milestones = ms_stats.get(1, 0)

        open_risks = conn.execute("SELECT count(*) FROM risks WHERE project_id = 1 AND status != 'Closed';").fetchone()[0]
        total_stakeholders = conn.execute("SELECT count(*) FROM stakeholders WHERE project_id = 1;").fetchone()[0]

        project_data["stats"] = {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "task_completion_pct": round((completed_tasks / max(total_tasks, 1)) * 100, 1),
            "total_milestones": total_milestones,
            "completed_milestones": completed_milestones,
            "milestone_completion_pct": round((completed_milestones / max(total_milestones, 1)) * 100, 1),
            "open_risks": open_risks,
            "total_stakeholders": total_stakeholders,
        }
        return project_data


def update_project(name: str, start_date: str, end_date: str, status: str, description: Optional[str] = None) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE project
            SET name = ?, start_date = ?, end_date = ?, status = ?, description = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1;
            """,
            (name.strip(), start_date.strip(), end_date.strip(), status.strip(), (description or "").strip()),
        )
        conn.commit()
        return cursor.rowcount > 0


# --- Tasks ---
def get_tasks() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM tasks WHERE project_id = 1 ORDER BY id ASC;").fetchall()
        return [dict(r) for r in rows]


def create_task(title: str, status: str = "todo", due_date: Optional[str] = None, assigned_to: Optional[str] = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tasks (project_id, title, status, due_date, assigned_to)
            VALUES (1, ?, ?, ?, ?);
            """,
            (title.strip(), status.strip().lower(), (due_date or "").strip() or None, (assigned_to or "").strip() or None),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_task(task_id: int, updates: Dict[str, Any]) -> bool:
    fields = []
    values = []
    for k in ("title", "status", "due_date", "assigned_to"):
        if k in updates:
            fields.append(f"{k} = ?")
            values.append(updates[k])
    if not fields:
        return False
    values.append(task_id)
    with get_connection() as conn:
        cursor = conn.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?;", tuple(values))
        conn.commit()
        return cursor.rowcount > 0


def delete_task(task_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?;", (task_id,))
        conn.commit()
        return cursor.rowcount > 0


# --- Milestones ---
def get_milestones() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM milestones WHERE project_id = 1 ORDER BY target_date ASC, id ASC;").fetchall()
        return [dict(r) for r in rows]


def create_milestone(title: str, target_date: str, completed: int = 0) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO milestones (project_id, title, target_date, completed) VALUES (1, ?, ?, ?);",
            (title.strip(), target_date.strip(), 1 if completed else 0),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_milestone(milestone_id: int, updates: Dict[str, Any]) -> bool:
    fields = []
    values = []
    for k in ("title", "target_date", "completed"):
        if k in updates:
            fields.append(f"{k} = ?")
            val = int(updates[k]) if k == "completed" else updates[k]
            values.append(val)
    if not fields:
        return False
    values.append(milestone_id)
    with get_connection() as conn:
        cursor = conn.execute(f"UPDATE milestones SET {', '.join(fields)} WHERE id = ?;", tuple(values))
        conn.commit()
        return cursor.rowcount > 0


def delete_milestone(milestone_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM milestones WHERE id = ?;", (milestone_id,))
        conn.commit()
        return cursor.rowcount > 0


# --- Risks ---
def get_risks() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM risks WHERE project_id = 1 ORDER BY id ASC;").fetchall()
        return [dict(r) for r in rows]


def create_risk(description: str, likelihood: str, impact: str, mitigation: str, status: str = "Open") -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO risks (project_id, description, likelihood, impact, mitigation, status)
            VALUES (1, ?, ?, ?, ?, ?);
            """,
            (description.strip(), likelihood.strip(), impact.strip(), mitigation.strip(), status.strip()),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_risk(risk_id: int, updates: Dict[str, Any]) -> bool:
    fields = []
    values = []
    for k in ("description", "likelihood", "impact", "mitigation", "status"):
        if k in updates:
            fields.append(f"{k} = ?")
            values.append(updates[k])
    if not fields:
        return False
    values.append(risk_id)
    with get_connection() as conn:
        cursor = conn.execute(f"UPDATE risks SET {', '.join(fields)} WHERE id = ?;", tuple(values))
        conn.commit()
        return cursor.rowcount > 0


def delete_risk(risk_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM risks WHERE id = ?;", (risk_id,))
        conn.commit()
        return cursor.rowcount > 0


# --- Stakeholders ---
def get_stakeholders() -> List[Dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM stakeholders WHERE project_id = 1 ORDER BY id ASC;").fetchall()
        return [dict(r) for r in rows]


def create_stakeholder(name: str, role: str, contact: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO stakeholders (project_id, name, role, contact) VALUES (1, ?, ?, ?);",
            (name.strip(), role.strip(), contact.strip()),
        )
        conn.commit()
        return int(cursor.lastrowid)


def delete_stakeholder(stakeholder_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM stakeholders WHERE id = ?;", (stakeholder_id,))
        conn.commit()
        return cursor.rowcount > 0


# ==============================================================================
# Enterprise System Module (Categories & Negative Feedback Issues)
# ==============================================================================

def get_categories() -> List[str]:
    with get_connection() as conn:
        rows = conn.execute("SELECT name FROM categories ORDER BY name ASC;").fetchall()
        return [r["name"] for r in rows]


def create_category(name: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?);", (name.strip(),))
        conn.commit()
        return int(cursor.lastrowid)


def get_issues(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    analysis_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    query = """
        SELECT i.id, i.analysis_id, i.source_feedback_text, i.category, i.priority, i.status, i.created_at,
               a.event_name
        FROM issues i
        LEFT JOIN analyses a ON i.analysis_id = a.id
        WHERE 1=1
    """
    params = []
    if status:
        query += " AND i.status = ?"
        params.append(status.strip())
    if priority:
        query += " AND i.priority = ?"
        params.append(priority.strip())
    if category:
        query += " AND i.category = ?"
        params.append(category.strip())
    if analysis_id:
        query += " AND i.analysis_id = ?"
        params.append(analysis_id)

    query += " ORDER BY i.id DESC;"

    with get_connection() as conn:
        rows = conn.execute(query, tuple(params)).fetchall()
        return [
            {
                "id": r["id"],
                "analysis_id": r["analysis_id"],
                "event_name": r["event_name"] or "Standalone Issue",
                "source_feedback_text": r["source_feedback_text"],
                "category": r["category"],
                "priority": r["priority"],
                "status": r["status"],
                "created_at": str(r["created_at"]),
            }
            for r in rows
        ]


def get_issue_stats(analysis_id: Optional[int] = None) -> Dict[str, int]:
    with get_connection() as conn:
        query = "SELECT status, count(*) as cnt FROM issues WHERE 1=1"
        params = []
        if analysis_id is not None:
            query += " AND analysis_id = ?"
            params.append(analysis_id)
        query += " GROUP BY status;"
        rows = conn.execute(query, tuple(params)).fetchall()
        counts = {r["status"]: r["cnt"] for r in rows}
        total = sum(counts.values())
        return {
            "total": total,
            "new": counts.get("new", 0),
            "in_progress": counts.get("in-progress", 0),
            "resolved": counts.get("resolved", 0),
        }


def create_issue(
    analysis_id: Optional[int],
    source_feedback_text: str,
    category: str = "General",
    priority: str = "Medium",
    status: str = "new",
) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO issues (analysis_id, source_feedback_text, category, priority, status)
            VALUES (?, ?, ?, ?, ?);
            """,
            (analysis_id, source_feedback_text.strip(), category.strip(), priority.strip(), status.strip()),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_issue(issue_id: int, updates: Dict[str, Any]) -> bool:
    fields = []
    values = []
    for k in ("category", "priority", "status"):
        if k in updates:
            fields.append(f"{k} = ?")
            values.append(updates[k])
    if not fields:
        return False
    values.append(issue_id)
    with get_connection() as conn:
        cursor = conn.execute(f"UPDATE issues SET {', '.join(fields)} WHERE id = ?;", tuple(values))
        conn.commit()
        return cursor.rowcount > 0


def delete_issue(issue_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM issues WHERE id = ?;", (issue_id,))
        conn.commit()
        return cursor.rowcount > 0


def _classify_category(text: str) -> str:
    """Heuristically assign negative student feedback to an operational category."""
    lower = text.lower()
    if any(k in lower for k in ("sound", "mic", "microphone", "audio", "hear", "speaker", "projector", "screen", "slide", "wifi", "internet")):
        return "Audio/Visual & Tech"
    if any(k in lower for k in ("food", "lunch", "snack", "refreshment", "tea", "coffee", "water", "meal", "catering", "drinks")):
        return "Catering & Hospitality"
    if any(k in lower for k in ("ac", "air condition", "hot", "cold", "hall", "room", "seat", "chair", "space", "crowd", "dirty", "restroom", "washroom", "ventilation")):
        return "Facility & Logistics"
    if any(k in lower for k in ("delay", "late", "time", "timing", "schedule", "long", "agenda", "rushed", "duration", "speaker went over")):
        return "Scheduling & Content"
    return "General"


def _determine_priority(compound_score: float) -> str:
    """Map VADER negative polarity intensity to enterprise priority levels."""
    if compound_score <= -0.65:
        return "Critical"
    elif compound_score <= -0.45:
        return "High"
    elif compound_score <= -0.30:
        return "Medium"
    return "Low"


def create_issues_from_analysis(analysis_id: int, threshold: float = -0.30) -> Dict[str, Any]:
    """
    Mine negative sentiment responses (compound score <= threshold) from a completed analysis
    and convert them into enterprise issue tracking tickets.
    """
    analysis = get_analysis_by_id(analysis_id)
    if not analysis:
        raise ValueError(f"Analysis #{analysis_id} not found.")

    sentiment = analysis.get("sentiment", {})
    per_response = sentiment.get("per_response", [])

    created_issues = []
    skipped_count = 0

    with get_connection() as conn:
        # Check existing issues for this analysis to avoid duplicate ticket generation
        existing_rows = conn.execute(
            "SELECT source_feedback_text FROM issues WHERE analysis_id = ?;",
            (analysis_id,),
        ).fetchall()
        existing_texts = {r["source_feedback_text"].strip().lower() for r in existing_rows}

        for item in per_response:
            compound = item.get("compound", 0.0)
            text = (item.get("text") or "").strip()
            if not text:
                continue

            if compound <= threshold:
                norm_text = text.lower()
                if norm_text in existing_texts:
                    skipped_count += 1
                    continue

                category = _classify_category(text)
                priority = _determine_priority(compound)

                cursor = conn.execute(
                    """
                    INSERT INTO issues (analysis_id, source_feedback_text, category, priority, status)
                    VALUES (?, ?, ?, ?, 'new');
                    """,
                    (analysis_id, text, category, priority),
                )
                existing_texts.add(norm_text)
                created_issues.append({
                    "id": int(cursor.lastrowid),
                    "analysis_id": analysis_id,
                    "source_feedback_text": text,
                    "category": category,
                    "priority": priority,
                    "status": "new",
                    "compound_score": compound,
                })

        conn.commit()

    return {
        "analysis_id": analysis_id,
        "event_name": analysis.get("event_name"),
        "threshold": threshold,
        "created_count": len(created_issues),
        "skipped_duplicates": skipped_count,
        "issues": created_issues,
    }


# ==============================================================================
# Transaction Logging & Live Database Introspection Engine
# ==============================================================================

def log_transaction(
    action: str,
    table_name: str,
    summary: str,
    details: Optional[Any] = None,
    status: str = "COMMITTED",
    duration_ms: float = 0.0,
    client_ip: str = "127.0.0.1",
) -> Optional[int]:
    """Persist an audit log entry for database transactions."""
    try:
        details_str = json.dumps(details) if isinstance(details, (dict, list)) else (str(details) if details else None)
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO transaction_logs (action, table_name, summary, details, status, duration_ms, client_ip)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (action.upper(), table_name, summary, details_str, status, round(duration_ms, 2), client_ip),
            )
            conn.commit()
            return int(cursor.lastrowid)
    except Exception as e:
        print(f"[Warning] Failed to write transaction log: {e}")
        return None


def get_database_overview() -> Dict[str, Any]:
    """Inspect analyzer.db schema, statistics, table counts, and storage metrics."""
    with get_connection() as conn:
        # SQLite metadata
        sqlite_version = conn.execute("SELECT sqlite_version();").fetchone()[0]
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0].upper()
        page_count = conn.execute("PRAGMA page_count;").fetchone()[0]
        page_size = conn.execute("PRAGMA page_size;").fetchone()[0]
        encoding = conn.execute("PRAGMA encoding;").fetchone()[0]
        foreign_keys = conn.execute("PRAGMA foreign_keys;").fetchone()[0]

        # File stats
        db_size_bytes = os.path.getsize(DB_PATH) if DB_PATH.exists() else 0
        if db_size_bytes >= 1024 * 1024:
            size_fmt = f"{db_size_bytes / (1024 * 1024):.2f} MB"
        else:
            size_fmt = f"{db_size_bytes / 1024:.2f} KB"

        # Tables introspection
        table_rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name ASC;"
        ).fetchall()
        table_names = [r["name"] for r in table_rows]

        tables_data = []
        total_rows = 0

        for tname in table_names:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {tname};").fetchone()[0]
            total_rows += cnt

            cols_info = conn.execute(f"PRAGMA table_info({tname});").fetchall()
            columns = [
                {
                    "cid": c["cid"],
                    "name": c["name"],
                    "type": c["type"] or "TEXT",
                    "notnull": bool(c["notnull"]),
                    "dflt_value": c["dflt_value"],
                    "pk": bool(c["pk"]),
                }
                for c in cols_info
            ]

            fks_info = conn.execute(f"PRAGMA foreign_key_list({tname});").fetchall()
            foreign_keys_list = [
                {
                    "id": fk["id"],
                    "seq": fk["seq"],
                    "table": fk["table"],
                    "from": fk["from"],
                    "to": fk["to"],
                }
                for fk in fks_info
            ]

            tables_data.append({
                "name": tname,
                "row_count": cnt,
                "column_count": len(columns),
                "columns": columns,
                "foreign_keys": foreign_keys_list,
            })

        total_transactions = conn.execute("SELECT COUNT(*) FROM transaction_logs;").fetchone()[0] if "transaction_logs" in table_names else 0

        return {
            "database_name": "analyzer.db",
            "file_path": str(DB_PATH),
            "file_size_bytes": db_size_bytes,
            "file_size_formatted": size_fmt,
            "sqlite_version": sqlite_version,
            "journal_mode": journal_mode,
            "page_count": page_count,
            "page_size": page_size,
            "encoding": encoding,
            "foreign_keys_enabled": bool(foreign_keys),
            "total_tables": len(table_names),
            "total_rows": total_rows,
            "total_transactions": total_transactions,
            "tables": tables_data,
        }


def get_table_rows(
    table_name: str,
    page: int = 1,
    page_size: int = 50,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve paginated rows and column definitions for a given table safely."""
    ALLOWED_TABLES = {
        "analyses",
        "categories",
        "issues",
        "milestones",
        "project",
        "risks",
        "stakeholders",
        "tasks",
        "transaction_logs",
        "users",
    }
    if table_name not in ALLOWED_TABLES:
        raise ValueError(f"Invalid or unauthorized table name: '{table_name}'.")

    page = max(1, page)
    page_size = max(5, min(page_size, 200))
    offset = (page - 1) * page_size

    with get_connection() as conn:
        cols_info = conn.execute(f"PRAGMA table_info({table_name});").fetchall()
        columns = [
            {
                "name": c["name"],
                "type": c["type"] or "TEXT",
                "pk": bool(c["pk"]),
                "notnull": bool(c["notnull"]),
            }
            for c in cols_info
        ]
        col_names = [c["name"] for c in columns]

        where_clause = ""
        params: List[Any] = []
        if search and search.strip():
            term = f"%{search.strip()}%"
            # Search across all columns
            clauses = [f"CAST({c} AS TEXT) LIKE ?" for c in col_names]
            where_clause = " WHERE " + " OR ".join(clauses)
            params = [term] * len(col_names)

        count_sql = f"SELECT COUNT(*) FROM {table_name}{where_clause};"
        total_rows = conn.execute(count_sql, tuple(params)).fetchone()[0]

        pk_cols = [c["name"] for c in columns if c["pk"]]
        order_col = pk_cols[0] if pk_cols else col_names[0]
        order_clause = f" ORDER BY {order_col} DESC"

        query_sql = f"SELECT * FROM {table_name}{where_clause}{order_clause} LIMIT ? OFFSET ?;"
        exec_params = tuple(params + [page_size, offset])
        rows = conn.execute(query_sql, exec_params).fetchall()

        serialized_rows = []
        for r in rows:
            row_dict = {}
            for col in col_names:
                val = r[col]
                if table_name == "users" and col == "password_hash":
                    row_dict[col] = "••••••••••••••••••••••••••••••••••••"
                elif isinstance(val, (dict, list)):
                    row_dict[col] = json.dumps(val)
                else:
                    row_dict[col] = val
            serialized_rows.append(row_dict)

        total_pages = max(1, (total_rows + page_size - 1) // page_size)

        return {
            "table_name": table_name,
            "columns": columns,
            "rows": serialized_rows,
            "total_rows": total_rows,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }


def get_transaction_logs(
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    table_name: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict[str, Any]:
    """Query live transaction logs with filters."""
    limit = max(1, min(limit, 200))
    offset = max(0, offset)

    clauses = []
    params: List[Any] = []

    if action and action.strip().upper() != "ALL":
        clauses.append("action = ?")
        params.append(action.strip().upper())

    if table_name and table_name.strip().upper() != "ALL":
        clauses.append("table_name = ?")
        params.append(table_name.strip())

    if search and search.strip():
        term = f"%{search.strip()}%"
        clauses.append("(summary LIKE ? OR details LIKE ? OR action LIKE ? OR table_name LIKE ?)")
        params.extend([term, term, term, term])

    where_str = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    with get_connection() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM transaction_logs{where_str};", tuple(params)).fetchone()[0]
        sql = f"SELECT * FROM transaction_logs{where_str} ORDER BY id DESC LIMIT ? OFFSET ?;"
        rows = conn.execute(sql, tuple(params + [limit, offset])).fetchall()

        logs = [dict(r) for r in rows]
        return {
            "logs": logs,
            "total": total,
            "limit": limit,
            "offset": offset,
        }


def simulate_database_transaction(action_type: Optional[str] = None) -> Dict[str, Any]:
    """Simulate a live transaction on the database to demonstrate real-time audit logging."""
    import random
    import time

    templates = [
        ("INSERT", "tasks", "Scheduled AV Soundcheck for Main Stage", {"priority": "High", "assignee": "A/V Team"}),
        ("UPDATE", "issues", "Escalated Wi-Fi connectivity ticket #412 to Critical", {"status": "in-progress", "sla": "2h"}),
        ("SELECT", "analyses", "Read extractive summary vector embeddings", {"event": "Annual Symposium", "limit": 25}),
        ("UPDATE", "milestones", "Verified milestone 'Survey Portal Ingestion Closed'", {"completed": 1}),
        ("INSERT", "risks", "Mitigated air conditioning overload risk via auxiliary fans", {"likelihood": "Low", "status": "Mitigated"}),
        ("TRANSACTION", "issues", "Batched resolution of 14 catering temperature feedback remarks", {"resolved_count": 14}),
        ("INSERT", "stakeholders", "Added Dr. Lisa Vance (Logistics Coordinator)", {"contact": "l.vance@college.edu"}),
        ("SELECT", "users", "Authenticated session token for admin supervisor", {"role": "admin"}),
    ]

    selected = random.choice(templates)
    act = action_type.upper() if action_type and action_type.upper() in ("INSERT", "UPDATE", "DELETE", "SELECT", "TRANSACTION") else selected[0]
    tbl = selected[1]
    summary = selected[2]
    details = selected[3]

    duration = round(random.uniform(0.4, 4.8), 2)
    log_id = log_transaction(
        action=act,
        table_name=tbl,
        summary=summary,
        details=details,
        status="COMMITTED",
        duration_ms=duration,
        client_ip="127.0.0.1",
    )

    return {
        "id": log_id,
        "action": act,
        "table_name": tbl,
        "summary": summary,
        "details": details,
        "status": "COMMITTED",
        "duration_ms": duration,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def clear_transaction_logs() -> bool:
    """Clear transaction logs and add a reset audit entry."""
    with get_connection() as conn:
        conn.execute("DELETE FROM transaction_logs;")
        conn.commit()
    log_transaction("MIGRATION", "transaction_logs", "Transaction log stream reset by supervisor", status="COMMITTED", duration_ms=0.5)
    return True

