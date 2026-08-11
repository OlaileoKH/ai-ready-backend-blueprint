from pydantic import BaseModel, Field
from typing import Optional

# Base rules that both creating and reading a task will share
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="The name of the task")
    description: Optional[str] = Field(None, description="Detailed steps or prompt data")
    priority: int = Field(default=1, ge=1, le=5, description="Priority score from 1 (low) to 5 (high)")

# Rules specifically required when a client creates a new task
class TaskCreate(TaskBase):
    pass  # It inherits everything from TaskBase

# Rules for how data looks when we send it back to the client
class TaskResponse(TaskBase):
    id: int
    is_completed: bool
    status: str  

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str

    class Config:
        from_attributes = True

# The layout of the data card sent back when a user logs in successfully
class TokenResponse(BaseModel):
    access_token: str
    token_type: str
