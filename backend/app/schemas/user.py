from datetime import datetime
from pydantic import BaseModel, field_validator
from app.models.user import UserStatus


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    university: str
    status: UserStatus
    profile_photo: str | None
    bio: str | None
    instagram: str | None
    kakao_id: str | None
    phone: str | None
    matching_paused: bool
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    bio: str | None = None
    instagram: str | None = None
    kakao_id: str | None = None
    phone: str | None = None

    @field_validator("instagram", "kakao_id", "phone", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: str | None) -> str | None:
        if v == "":
            return None
        return v


class MatchingPauseUpdate(BaseModel):
    matching_paused: bool
