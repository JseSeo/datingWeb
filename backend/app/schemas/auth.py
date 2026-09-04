from typing import Literal
from pydantic import BaseModel, EmailStr, field_validator, model_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    university: str
    gender: Literal["male", "female"]
    agreed_terms: bool
    agreed_privacy: bool
    agreed_age_14: bool
    instagram: str | None = None
    kakao_id: str | None = None
    phone: str | None = None

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("비밀번호는 8자 이상이어야 합니다")
        return v

    @field_validator("name", "university")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("빈 값은 허용되지 않습니다")
        return v.strip()

    @field_validator("instagram", "kakao_id", "phone", mode="before")
    @classmethod
    def empty_string_to_none(cls, v: str | None) -> str | None:
        return None if v == "" else v

    @model_validator(mode="after")
    def at_least_one_contact(self):
        """연락처가 없으면 매칭돼도 서로 닿을 방법이 없다 (설계 §7.1)."""
        if not (self.instagram or self.kakao_id or self.phone):
            raise ValueError("연락처를 최소 1개 입력하세요")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
