from uuid import uuid4
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, UTC

class Base(DeclarativeBase):
    pass

class CorpusRecord(Base):
    __tablename__ = "corpus_record"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    target_statement = Column(String, nullable=False)
    parameter_name = Column(String, nullable=False)
    is_control_target = Column(Boolean, default=False, nullable=False)
    age_in_hours = Column(Integer, nullable=True)
    
    # Admin State
    admin_awareness_tier = Column(String, nullable=False)
    admin_psychological_context = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
