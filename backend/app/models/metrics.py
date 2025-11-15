import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Numeric, ForeignKey, Text, Column, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Metrics(Base):
    """Metrics model for storing user analytics data"""
    __tablename__ = "metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    metric_key = Column(String(100), nullable=False)
    metric_value = Column(Numeric, nullable=True)
    tags = Column(JSONB, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    user = relationship("User", back_populates="metrics")

    # Composite index for efficient querying
    __table_args__ = (
        Index('idx_metrics_key_timestamp', 'metric_key', 'timestamp'),
    )

    def __repr__(self):
        return f"<Metrics(id={self.id}, user_id={self.user_id}, key={self.metric_key}, value={self.metric_value})>"