from pydantic import BaseModel, EmailStr, Field


class SignUpRequestSchema(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=8)
    password2: str = Field(..., min_length=8)
    city: str = Field(..., min_length=1, max_length=100)
    country: str = Field(..., min_length=1, max_length=100)


class LogInRequestSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class LogInResponseSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
