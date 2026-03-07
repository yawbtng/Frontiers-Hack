from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from models.schemas import CreateTaskRequest, UpdateTaskRequest, TaskResponse
from services.store import store

router = APIRouter(tags=["tasks"])


@router.get("/")
async def list_tasks(
    user_id: str = Query(default="default"),
    status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=100),
):
    """List tasks with optional filters."""
    tasks = store.get_tasks(user_id, status=status, priority=priority, limit=limit)
    return tasks


@router.post("/", response_model=TaskResponse)
async def create_task(request: CreateTaskRequest):
    """Create a new task."""
    task = store.create_task(
        user_id=request.user_id,
        title=request.title,
        description=request.description,
        priority=request.priority,
        due_at=request.due_at,
        source=request.source,
        source_ref=request.source_ref,
    )
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, request: UpdateTaskRequest, user_id: str = Query(default="default")):
    """Update an existing task."""
    task = store.update_task(
        user_id=user_id,
        task_id=task_id,
        status=request.status,
        priority=request.priority,
        title=request.title,
        description=request.description,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
