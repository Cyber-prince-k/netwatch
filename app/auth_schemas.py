from pydantic import BaseModel, Field


class RegistrationForm(BaseModel):
    email: str
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=8)


class LoginForm(BaseModel):
    email: str
    password: str


class ProfileForm(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    password: str | None = Field(default=None, min_length=8)
