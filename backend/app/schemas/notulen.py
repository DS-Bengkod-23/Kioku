from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class NotulenMeta(BaseModel):
    """Status editorial notulen, diturunkan dari Meeting + notulen_versions."""

    status: Optional[Literal["draft", "published"]] = None
    current_version: Optional[int] = None
    last_published_at: Optional[datetime] = None
    edited_at: Optional[datetime] = None
    has_unsent_changes: bool = False
    needs_review_count: int = 0
