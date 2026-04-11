import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON, Enum as SAEnum, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import Base




class QDSStepType(str, PyEnum):
    single_select = "single_select"
    multi_select = "multi_select"
    text_input = "text_input"
    numeric_input = "numeric_input"
    yes_no = "yes_no"
    informational = "informational"
    terminal_outcome = "terminal_outcome"




class QDSQualificationStatus(str, PyEnum):
    high_fit = "high_fit"
    medium_fit = "medium_fit"
    low_fit = "low_fit"
    not_qualified = "not_qualified"
    qualified = "qualified"
    warm = "warm"




class QDSSessionStatus(str, PyEnum):
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"




class QDSAsset(Base):
