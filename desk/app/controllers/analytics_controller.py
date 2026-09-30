from datetime import date

from fastapi import APIRouter, Depends, Query

from ..deps import db, role
from ..models.domain import STAFF
from ..services import analytics_service

router = APIRouter()


@router.get("/analytics")
def analytics(from_: date = Query(alias="from"), to: date = Query(), _=Depends(role(*STAFF)), c=Depends(db)):
    return analytics_service.report(c, from_, to)
