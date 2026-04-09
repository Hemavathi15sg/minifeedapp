from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class PostCreate(BaseModel):
    """Schema for creating a new post."""
    caption: str = Field(..., min_length=1, description="Post caption")
    image_url: str = Field(..., min_length=1, description="Post image URL")


class PostUpdate(BaseModel):
    """Schema for updating a post."""
    caption: Optional[str] = Field(None, description="Post caption")
    image_url: Optional[str] = Field(None, description="Post image URL")


class PostResponse(BaseModel):
    """Schema for post response."""
    id: int
    caption: str
    image_url: str
    created_at: datetime

    model_config = {"from_attributes": True}
