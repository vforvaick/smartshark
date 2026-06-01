from pydantic import BaseModel

from app.models.user import Role


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    role: Role

    model_config = {"from_attributes": True}


class CreateAnalystRequest(BaseModel):
    username: str
    password: str
