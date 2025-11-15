import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Enum, ForeignKey, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Subscription(Base):
    """Subscription model for billing"""
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    stripe_customer_id = Column(String(255), unique=True, nullable=True, index=True)
    stripe_subscription_id = Column(String(255), unique=True, nullable=True, index=True)
    plan = Column(
        Enum('free', 'pro', 'enterprise', name='subscription_plan'),
        default='free',
        nullable=False
    )
    status = Column(
        Enum('trial', 'active', 'past_due', 'canceled', 'unpaid', name='subscription_status'),
        default='trial',
        nullable=False,
        index=True
    )
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    user = relationship("User", back_populates="subscription")

    @property
    def is_active(self) -> bool:
        """Check if subscription is currently active"""
        now = datetime.utcnow()
        if self.status == 'canceled':
            return False
        if self.status == 'unpaid':
            return False
        if self.status == 'past_due':
            return False
        if self.trial_ends_at and now > self.trial_ends_at:
            return False
        if self.current_period_end and now > self.current_period_end:
            return False
        return True

    @property
    def can_access_feature(self, feature: str) -> bool:
        """Check if user can access specific feature based on plan"""
        feature_access = {
            'free': ['basic_dashboard', 'limited_metrics'],
            'pro': ['basic_dashboard', 'advanced_analytics', 'api_access'],
            'enterprise': ['basic_dashboard', 'advanced_analytics', 'api_access', 'priority_support', 'custom_integrations']
        }
        return feature in feature_access.get(self.plan, [])

    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, plan={self.plan}, status={self.status})>"