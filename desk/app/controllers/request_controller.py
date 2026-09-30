from fastapi import APIRouter, Depends

from ..deps import current_user, db, role
from ..models.schemas import AssignIn, NewRequest, StatusIn
from ..services import episode_service, request_service

router = APIRouter(prefix="/requests")


@router.post("", status_code=201)
def create(b: NewRequest, u=Depends(role("client")), c=Depends(db)):
    return request_service.create(c, u, b)


@router.get("")
def list_requests(u=Depends(current_user), c=Depends(db)):
    return request_service.list_for(c, u)


@router.get("/{rid}")
def show(rid: int, u=Depends(current_user), c=Depends(db)):
    return request_service.detail(c, u, rid)


@router.post("/{rid}/status")
def change_status(rid: int, b: StatusIn, u=Depends(current_user), c=Depends(db)):
    return request_service.change_status(c, u, rid, b.status)


@router.post("/{rid}/episodes")
def assign(rid: int, b: AssignIn, u=Depends(role("operator", "admin")), c=Depends(db)):
    return episode_service.assign(c, u, rid, b.episode_ids)
