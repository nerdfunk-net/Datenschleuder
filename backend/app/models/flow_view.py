"""Flow view model for storing user-defined column views"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

from app.core.database import Base


class FlowView(Base):
    """Flow view configuration - stores which columns to display"""

    __tablename__ = "flow_views"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(
        String, nullable=False, index=True
    )  # e.g., "Source View", "Destination View"
    description = Column(String, nullable=True)  # Optional description
    visible_columns = Column(Text, nullable=False)  # JSON array of column names
    column_widths = Column(
        Text, nullable=True
    )  # JSON object of column widths {column_key: width_px}
    is_default = Column(Boolean, nullable=False, default=False)  # Default view for user
    created_by = Column(String, nullable=True)  # Username who created it
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    modified_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# Pydantic schemas
class FlowViewCreate(BaseModel):
    """Schema for creating a view"""

    name: str
    description: Optional[str] = None
    visible_columns: List[str]
    column_widths: Optional[dict] = None
    is_default: bool = False


class FlowViewUpdate(BaseModel):
    """Schema for updating a view"""

    name: Optional[str] = None
    description: Optional[str] = None
    visible_columns: Optional[List[str]] = None
    column_widths: Optional[dict] = None
    is_default: Optional[bool] = None


class FlowViewResponse(BaseModel):
    """Schema for view response"""

    id: int
    name: str
    description: Optional[str]
    visible_columns: List[str]
    column_widths: Optional[dict]
    is_default: bool
    created_by: Optional[str]
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True
