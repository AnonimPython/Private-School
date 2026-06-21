
#/ =====================================================================================
#/  Activity logger — logging user actions in MongoDB
#/  Records: who, what, when, and with what details
#/  Used in all routers for auditing
#/ =====================================================================================

#/ ─── Imports / Импорты ───
import config
from datetime import datetime, timezone
from typing import Optional
from pymongo import MongoClient
from app.database import get_mongo


#* ─── Action types ───
#? List of all logged actions. Add new ones as functionality expands
LOGIN = "login"
LOGOUT = "logout"
CREATE_USER = "create_user"
UPDATE_USER = "update_user"
DELETE_USER = "delete_user"
CREATE_GRADE = "create_grade"
UPDATE_GRADE = "update_grade"
DELETE_GRADE = "delete_grade"
CREATE_HOMEWORK = "create_homework"
UPDATE_HOMEWORK = "update_homework"
DELETE_HOMEWORK = "delete_homework"
CREATE_NEWS = "create_news"
UPDATE_NEWS = "update_news"
DELETE_NEWS = "delete_news"
CREATE_CLASS = "create_class"
CREATE_SUBJECT = "create_subject"
ASSIGN_TEACHER = "assign_teacher"
GENERATE_YEARLY_GRADES = "generate_yearly_grades"
VIEW_LOGS = "view_logs"
UPDATE_SCHEDULE = "update_schedule"
DELETE_SCHEDULE = "delete_schedule"
CLEANUP_LOGS = "cleanup_logs"


#* ─── Logger ───

def log_action(
    user_id: str,
    action: str,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Write a user action to MongoDB.

    Args:
        user_id: UUID of the user (string)
        action: action type from constants above
        details: arbitrary data (e.g., {"grade_value": 5, "subject": "Математика"})
        ip_address: IP address of the user
        user_agent: User-Agent of the browser
    """
    mongo = get_mongo()
    if mongo is None:
        #! MongoDB unavailable — skip logging
        return

    try:
        db = mongo["school_logs"]
        collection = db["activity_logs"]

        log_entry = {
            "user_id": user_id,
            "action": action,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.now(timezone.utc),
        }

        collection.insert_one(log_entry)

        #* Automatically delete logs older than 365 days to avoid cluttering the DB
        #? Configurable based on school data retention requirements
        from datetime import timedelta
        cleanup_before = (datetime.now(timezone.utc) - timedelta(days=365)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        collection.delete_many({"timestamp": {"$lt": cleanup_before}})

    except Exception as e:
        #! If logging fails — don't break the main application
        print(f"[!] Logging error: {e}")
