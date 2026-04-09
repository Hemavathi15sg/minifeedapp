from dataclasses import dataclass
from datetime import datetime


@dataclass
class Post:
    """Post model for database representation."""
    id: int
    caption: str
    image_url: str
    created_at: datetime
    
    @classmethod
    def from_dict(cls, data):
        """Create Post instance from dictionary."""
        return cls(
            id=data["id"],
            caption=data["caption"],
            image_url=data["image_url"],
            created_at=datetime.fromisoformat(data["created_at"])
        )
    
    def to_dict(self):
        """Convert Post instance to dictionary."""
        return {
            "id": self.id,
            "caption": self.caption,
            "image_url": self.image_url,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class Comment:
    """Comment model for database representation."""
    id: int
    post_id: int
    body: str
    created_at: datetime

    @classmethod
    def from_dict(cls, data):
        """Create Comment instance from dictionary."""
        return cls(
            id=data["id"],
            post_id=data["post_id"],
            body=data["body"],
            created_at=datetime.fromisoformat(data["created_at"])
        )

    def to_dict(self):
        """Convert Comment instance to dictionary."""
        return {
            "id": self.id,
            "post_id": self.post_id,
            "body": self.body,
            "created_at": self.created_at.isoformat()
        }
