import logging
import sys
from typing import Any, Dict

import structlog
from structlog.stdlib import LoggerFactory

from app.core.config import settings


def configure_logging() -> None:
    """Configure structured logging for the application"""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not settings.DEBUG
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    )

    # Set log levels for specific libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.WARNING if not settings.DEBUG else logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("stripe").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger"""
    return structlog.get_logger(name)


class RequestLogger:
    """Middleware for logging HTTP requests"""

    def __init__(self, logger_name: str = "request"):
        self.logger = get_logger(logger_name)

    def log_request(
        self,
        method: str,
        url: str,
        status_code: int,
        duration: float,
        user_id: str = None,
        **kwargs
    ) -> None:
        """Log HTTP request"""
        self.logger.info(
            "HTTP Request",
            method=method,
            url=url,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            user_id=user_id,
            **kwargs
        )

    def log_error(
        self,
        method: str,
        url: str,
        error: str,
        user_id: str = None,
        **kwargs
    ) -> None:
        """Log HTTP error"""
        self.logger.error(
            "HTTP Error",
            method=method,
            url=url,
            error=error,
            user_id=user_id,
            **kwargs
        )


class SecurityLogger:
    """Logger for security events"""

    def __init__(self, logger_name: str = "security"):
        self.logger = get_logger(logger_name)

    def log_auth_success(
        self,
        email: str,
        method: str = "password",
        ip_address: str = None,
        user_agent: str = None
    ) -> None:
        """Log successful authentication"""
        self.logger.info(
            "Authentication Success",
            email=email,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent
        )

    def log_auth_failure(
        self,
        email: str,
        reason: str,
        method: str = "password",
        ip_address: str = None,
        user_agent: str = None
    ) -> None:
        """Log failed authentication"""
        self.logger.warning(
            "Authentication Failure",
            email=email,
            reason=reason,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent
        )

    def log_permission_denied(
        self,
        user_id: str,
        resource: str,
        action: str,
        ip_address: str = None
    ) -> None:
        """Log permission denied event"""
        self.logger.warning(
            "Permission Denied",
            user_id=user_id,
            resource=resource,
            action=action,
            ip_address=ip_address
        )

    def log_rate_limit_exceeded(
        self,
        identifier: str,
        endpoint: str,
        ip_address: str = None
    ) -> None:
        """Log rate limit exceeded"""
        self.logger.warning(
            "Rate Limit Exceeded",
            identifier=identifier,
            endpoint=endpoint,
            ip_address=ip_address
        )


class AuditLogger:
    """Logger for audit events"""

    def __init__(self, logger_name: str = "audit"):
        self.logger = get_logger(logger_name)

    def log_action(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str = None,
        metadata: Dict[str, Any] = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> None:
        """Log user action for audit"""
        self.logger.info(
            "User Action",
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent
        )

    def log_admin_action(
        self,
        admin_id: str,
        action: str,
        target_user_id: str = None,
        metadata: Dict[str, Any] = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> None:
        """Log admin action for audit"""
        self.logger.warning(
            "Admin Action",
            admin_id=admin_id,
            action=action,
            target_user_id=target_user_id,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent
        )


class BusinessLogger:
    """Logger for business events"""

    def __init__(self, logger_name: str = "business"):
        self.logger = get_logger(logger_name)

    def log_subscription_event(
        self,
        user_id: str,
        event_type: str,
        plan: str,
        amount: float = None,
        currency: str = None,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Log subscription business event"""
        self.logger.info(
            "Subscription Event",
            user_id=user_id,
            event_type=event_type,
            plan=plan,
            amount=amount,
            currency=currency,
            metadata=metadata or {}
        )

    def log_user_lifecycle_event(
        self,
        user_id: str,
        event_type: str,
        metadata: Dict[str, Any] = None
    ) -> None:
        """Log user lifecycle event"""
        self.logger.info(
            "User Lifecycle Event",
            user_id=user_id,
            event_type=event_type,
            metadata=metadata or {}
        )


# Initialize logging on import
configure_logging()

# Create logger instances
request_logger = RequestLogger()
security_logger = SecurityLogger()
audit_logger = AuditLogger()
business_logger = BusinessLogger()