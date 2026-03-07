"""In-memory data store with Supabase-compatible interface."""

import uuid
from datetime import datetime, timezone
from typing import Optional


class InMemoryStore:
    def __init__(self):
        self.sessions: dict[str, dict] = {}
        self.messages: dict[str, list[dict]] = {}
        self.tasks: dict[str, list[dict]] = {}
        self.user_context: dict[str, dict[str, dict]] = {}
        self.approvals: dict[str, dict] = {}
        self.notifications: list[dict] = []
        self.scanned_meeting_ids: set[str] = set()

    # --- Sessions ---

    def create_session(self, user_id: str, session_id: Optional[str] = None, title: Optional[str] = None) -> dict:
        sid = session_id or str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        session = {
            "session_id": sid,
            "user_id": user_id,
            "title": title or "New conversation",
            "created_at": now,
            "updated_at": now,
        }
        self.sessions[sid] = session
        self.messages[sid] = []
        return session

    def get_session(self, session_id: str) -> Optional[dict]:
        return self.sessions.get(session_id)

    def list_sessions(self, user_id: str) -> list[dict]:
        sessions = [s for s in self.sessions.values() if s["user_id"] == user_id]
        return sorted(sessions, key=lambda s: s["updated_at"], reverse=True)

    def update_session(self, session_id: str, **kwargs) -> Optional[dict]:
        session = self.sessions.get(session_id)
        if not session:
            return None
        if kwargs:
            session.update(kwargs)
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        return session

    # --- Messages ---

    def add_message(self, session_id: str, role: str, content: str) -> dict:
        msg = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "role": role,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if session_id not in self.messages:
            self.messages[session_id] = []
        self.messages[session_id].append(msg)
        return msg

    def get_messages(self, session_id: str) -> list[dict]:
        return self.messages.get(session_id, [])

    # --- Tasks ---

    def create_task(self, user_id: str, title: str, description: Optional[str] = None,
                    priority: str = "medium", due_at: Optional[str] = None,
                    source: str = "agent", source_ref: Optional[str] = None) -> dict:
        task = {
            "task_id": str(uuid.uuid4()),
            "user_id": user_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": "pending",
            "due_at": due_at,
            "source": source,
            "source_ref": source_ref,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if user_id not in self.tasks:
            self.tasks[user_id] = []
        self.tasks[user_id].append(task)
        return task

    def get_tasks(self, user_id: str, status: Optional[str] = None,
                  priority: Optional[str] = None, limit: int = 10) -> list[dict]:
        tasks = self.tasks.get(user_id, [])
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        if priority:
            tasks = [t for t in tasks if t["priority"] == priority]
        return sorted(tasks, key=lambda t: t["created_at"], reverse=True)[:limit]

    def update_task(self, user_id: str, task_id: str, **kwargs) -> Optional[dict]:
        tasks = self.tasks.get(user_id, [])
        for task in tasks:
            if task["task_id"] == task_id:
                task.update(kwargs)
                task["updated_at"] = datetime.now(timezone.utc).isoformat()
                return task
        return None

    # --- User Context ---

    def get_user_context(self, user_id: str, context_key: Optional[str] = None) -> dict | list[dict]:
        user_ctx = self.user_context.get(user_id, {})
        if context_key:
            return user_ctx.get(context_key, {})
        return list(user_ctx.values())

    def save_user_context(self, user_id: str, context_key: str, context_value: dict,
                          confidence: float = 0.5, source: str = "") -> dict:
        if user_id not in self.user_context:
            self.user_context[user_id] = {}
        entry = {
            "context_key": context_key,
            "context_value": context_value,
            "confidence": confidence,
            "source": source,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.user_context[user_id][context_key] = entry
        return entry

    # --- Notifications ---

    def add_notification(self, notif: dict) -> str:
        nid = str(uuid.uuid4())
        notif["id"] = nid
        notif["status"] = notif.get("status", "unread")
        notif["created_at"] = datetime.now(timezone.utc).isoformat()
        notif.setdefault("meeting_id", None)
        notif.setdefault("session_id", None)
        self.notifications.insert(0, notif)
        return nid

    def get_notifications(self, limit: int = 50) -> list[dict]:
        return self.notifications[:limit]

    def get_unread_count(self) -> int:
        return sum(1 for n in self.notifications if n["status"] == "unread")

    def get_notification(self, notification_id: str) -> Optional[dict]:
        for n in self.notifications:
            if n["id"] == notification_id:
                return n
        return None

    def update_notification(self, notification_id: str, **kwargs) -> Optional[dict]:
        for n in self.notifications:
            if n["id"] == notification_id:
                n.update(kwargs)
                return n
        return None

    # --- Scan Tracking ---

    def mark_meeting_scanned(self, meeting_id: str):
        self.scanned_meeting_ids.add(meeting_id)

    def is_meeting_scanned(self, meeting_id: str) -> bool:
        return meeting_id in self.scanned_meeting_ids

    # --- Approvals ---

    def create_approval(self, session_id: str, approval_data: dict) -> str:
        approval_id = str(uuid.uuid4())
        self.approvals[approval_id] = {
            "id": approval_id,
            "session_id": session_id,
            "status": "pending",
            "data": approval_data,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return approval_id

    def resolve_approval(self, approval_id: str, status: str, edited_payload: Optional[dict] = None) -> Optional[dict]:
        approval = self.approvals.get(approval_id)
        if not approval:
            return None
        approval["status"] = status
        approval["edited_payload"] = edited_payload
        approval["resolved_at"] = datetime.now(timezone.utc).isoformat()
        return approval


# Singleton
store = InMemoryStore()
