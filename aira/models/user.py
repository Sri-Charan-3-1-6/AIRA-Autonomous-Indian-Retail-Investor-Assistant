"""AIRA module: models/user.py"""

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., min_length=1, max_length=120, description="Display name")
    risk_profile: str = Field(default="moderate", description="Investor risk profile")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "investor@example.com",
                "name": "Riya Sharma",
                "risk_profile": "moderate",
            }
        }
    }


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), description="User UUID")
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., description="Display name")
    risk_profile: str = Field(default="moderate", description="Investor risk profile")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "b6f9c653-39a1-4c0f-b7a2-1213ab4f4a6e",
                "email": "investor@example.com",
                "name": "Riya Sharma",
                "risk_profile": "moderate",
                "created_at": "2026-03-26T06:30:00Z",
            }
        }
    }
