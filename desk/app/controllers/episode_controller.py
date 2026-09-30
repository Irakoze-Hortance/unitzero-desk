from typing import Optional

from fastapi import APIRouter, Body, Depends, Query

from ..deps import db, role
from ..models.domain import STAFF, Quality
from ..services import episode_service

router = APIRouter()


@router.get("/episodes")
def list_episodes(task_name: Optional[str] = None, quality: Optional[Quality] = None, unassigned: bool = False,
                  limit: int = Query(100, le=500), offset: int = 0, _=Depends(role(*STAFF)), c=Depends(db)):
    return episode_service.list_episodes(c, task_name, quality, unassigned, limit, offset)


@router.post("/import")
def import_episodes(data: bytes = Body(..., media_type="text/csv"), _=Depends(role(*STAFF)), c=Depends(db)):
    return episode_service.import_episodes(c, data)
