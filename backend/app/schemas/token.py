from pydantic import BaseModel
from app.schemas.user import UserResponse


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenPayload(BaseModel):
    sub: str | None = None
    role: str | None = None
    exp: int | None = None
