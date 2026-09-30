from datetime import date
from typing import Optional

from pydantic import BaseModel, Field

from .domain import Role, Status


class Login(BaseModel):
    email: str
    password: str


class NewUser(BaseModel):
    email: str
    name: str
    password: str = Field(min_length=8)
    role: Role


class UserPatch(BaseModel):
    role: Optional[Role] = None
    active: Optional[bool] = None


class NewRequest(BaseModel):
    task_name: str = Field(min_length=1)
    episodes_requested: int = Field(gt=0)
    deadline: date
    notes: str = ""


class StatusIn(BaseModel):
    status: Status


class AssignIn(BaseModel):
    episode_ids: list[str] = Field(min_length=1)
