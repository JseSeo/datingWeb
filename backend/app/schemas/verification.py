from datetime import datetime
from pydantic import BaseModel, field_validator
from app.models.verification import VerificationStatus


class VerificationOut(BaseModel):
    id: int
    user_id: int
    status: VerificationStatus
    reviewed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminVerificationOut(BaseModel):
    id: int
    user_id: int
    status: VerificationStatus
    reviewed_at: datetime | None
    created_at: datetime
    name: str
    university: str


class VerificationAction(BaseModel):
    action: str  # "approve" or "reject"

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("action must be 'approve' or 'reject'")
        return v
