from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class CalendarStatusResponse(BaseModel):
    connected: bool
    connected_at: Optional[datetime] = None
