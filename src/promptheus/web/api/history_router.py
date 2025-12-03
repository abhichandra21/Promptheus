"""History API router for Promptheus Web UI."""
import logging
from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from promptheus.config import Config
from promptheus.history import get_history
from promptheus.utils import get_user_email, get_device_category

router = APIRouter()
logger = logging.getLogger(__name__)

class HistoryEntry(BaseModel):
    timestamp: str
    task_type: str
    original_prompt: str
    refined_prompt: str
    provider: str
    model: str


class HistoryResponse(BaseModel):
    entries: List[HistoryEntry]
    total: int


@router.get("/history", response_model=HistoryResponse)
async def get_history_entries(limit: int = 50, offset: int = 0):
    """Get prompt history entries."""
    try:
        app_config = Config()
        history = get_history(app_config)
        
        # Get paginated entries and total count
        paginated_entries, total_entries = history.get_paginated(offset=offset, limit=limit)
        
        history_entries = []
        for entry in paginated_entries:
            history_entries.append(HistoryEntry(
                timestamp=entry.timestamp,
                task_type=entry.task_type or "",
                original_prompt=entry.original_prompt,
                refined_prompt=entry.refined_prompt,
                provider=entry.provider or "",
                model=entry.model or ""
            ))
        
        return HistoryResponse(
            entries=history_entries,
            total=total_entries
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{timestamp}")
async def delete_history_entry(timestamp: str, request: Request):
    """Delete a specific history entry by timestamp."""
    try:
        app_config = Config()
        history = get_history(app_config)
        success = history.delete_by_timestamp(timestamp)

        if not success:
            # Log failed user action
            logger.warning(
                "User failed to delete history entry - not found",
                extra={
                    "user": get_user_email(request),
                    "action": "history_delete",
                    "timestamp": timestamp,
                    "success": False,
                }
            )
            raise HTTPException(status_code=404, detail="History entry not found")

        # Log successful user action
        logger.info(
            "User deleted history entry",
            extra={
                "user": get_user_email(request),
                "action": "history_delete",
                "timestamp": timestamp,
                "device_category": get_device_category(request),
                "success": True,
            }
        )

        return {"message": "History entry deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        # Log failed user action
        logger.error(
            "User history delete failed",
            extra={
                "user": get_user_email(request),
                "action": "history_delete",
                "timestamp": timestamp,
                "success": False,
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history")
async def clear_history(request: Request):
    """Clear all history entries."""
    try:
        app_config = Config()
        history = get_history(app_config)
        history.clear()

        # Log successful user action
        logger.info(
            "User cleared history",
            extra={
                "user": get_user_email(request),
                "action": "history_clear",
                "device_category": get_device_category(request),
                "success": True,
            }
        )

        return {"message": "History cleared successfully"}
    except Exception as e:
        # Log failed user action
        logger.error(
            "User history clear failed",
            extra={
                "user": get_user_email(request),
                "action": "history_clear",
                "success": False,
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))
