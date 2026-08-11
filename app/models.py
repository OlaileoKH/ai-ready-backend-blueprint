from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from typing import List

class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(nullable=False)

    # Relationship link: One user can have many tasks
    tasks: Mapped[List["TaskModel"]] = relationship(back_populates="owner")

class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    priority: Mapped[int] = mapped_column(default=1)
    is_completed: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(default="pending")
    
    # New Column: Stores the ID of the user who created this task
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Relationship link back to the user object
    owner: Mapped["UserModel"] = relationship(back_populates="tasks")
