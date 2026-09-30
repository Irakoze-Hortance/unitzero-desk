from fastapi import APIRouter, Depends

from ..deps import db, role
from ..models.schemas import Login, NewUser, UserPatch
from ..services import auth_service

router = APIRouter()


@router.get("/health")
def health(c=Depends(db)):
    c.execute("select 1")
    return {"status": "ok"}


@router.post("/login")
def login(b: Login, c=Depends(db)):
    return auth_service.login(c, b.email, b.password)


@router.post("/users", status_code=201)
def create_user(b: NewUser, _=Depends(role("admin")), c=Depends(db)):
    return auth_service.create_user(c, b)


@router.patch("/users/{uid}")
def patch_user(uid: int, b: UserPatch, me=Depends(role("admin")), c=Depends(db)):
    return auth_service.patch_user(c, me, uid, b)
