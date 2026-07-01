"""
AuditService – centralised audit logging for all platform events.

Every admin action, financial event, and security event MUST be logged
through this service for compliance and traceability.
"""
import logging
from typing import Optional

from django.utils import timezone

from .models import AuditLog, User

logger = logging.getLogger(__name__)


class AuditService:
    """
    Centralised service for creating and querying audit logs.
    All methods are safe to call in hot paths (no transactions required).
    """

    # ── Write ─────────────────────────────────────────────────────────

    @classmethod
    def log(
        cls,
        action: str,
        description: str,
        user: Optional[User] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        changes: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: str = '',
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: Action constant (e.g. 'DEPOSIT', 'WITHDRAWAL').
            description: Human-readable description.
            user: The actor (admin or user). None for system events.
            resource_type: Type of affected entity.
            resource_id: ID of affected entity.
            changes: Before/after dict for state changes.
            ip_address: Request IP.
            user_agent: Request user-agent string.

        Returns:
            The created AuditLog.
        """
        entry = AuditLog.objects.create(
            user=user,
            action=action,
            description=description,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        logger.info(
            f"Audit: action={action} user={user.username if user else 'system'} "
            f"resource={resource_type}:{resource_id}"
        )
        return entry

    @classmethod
    def log_admin_action(
        cls,
        admin_user: User,
        action: str,
        target_type: str,
        target_id: str,
        description: str,
        before: Optional[dict] = None,
        after: Optional[dict] = None,
        reason: str = '',
        request=None,
    ) -> AuditLog:
        """
        Log an admin action with before/after state tracking.
        Convenience wrapper for admin-initiated changes.
        """
        changes = {}
        if before is not None:
            changes['before'] = before
        if after is not None:
            changes['after'] = after
        if reason:
            changes['reason'] = reason

        ip_address = None
        user_agent = ''
        if request:
            ip_address = cls._get_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]

        return cls.log(
            action=action,
            description=description,
            user=admin_user,
            resource_type=target_type,
            resource_id=target_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @classmethod
    def log_financial_event(
        cls,
        user: User,
        event_type: str,
        amount,
        reference_type: str = '',
        reference_id: str = '',
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """Log a financial event (deposit, withdrawal, bet, win)."""
        return cls.log(
            action=event_type,
            description=f'{event_type}: {amount} ref={reference_type}:{reference_id}',
            user=user,
            resource_type=reference_type.upper() if reference_type else 'PAYMENT',
            resource_id=reference_id,
            changes=metadata or {'amount': str(amount)},
        )

    @classmethod
    def log_security_event(
        cls,
        event_type: str,
        description: str,
        user: Optional[User] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> AuditLog:
        """Log a security event (login, failed login, account lock, etc.)."""
        return cls.log(
            action=event_type,
            description=description,
            user=user,
            resource_type='USER',
            resource_id=str(user.id) if user else None,
            changes=metadata or {},
            ip_address=ip_address,
        )

    # ── Read ──────────────────────────────────────────────────────────

    @classmethod
    def get_user_logs(cls, user_id: str, limit: int = 50, offset: int = 0):
        """Get audit logs for a specific user."""
        return AuditLog.objects.filter(user_id=user_id).order_by('-timestamp')[
            offset:offset + limit
        ]

    @classmethod
    def get_action_logs(cls, action: str, limit: int = 50, offset: int = 0):
        """Get audit logs filtered by action type."""
        return AuditLog.objects.filter(action=action).order_by('-timestamp')[
            offset:offset + limit
        ]

    @classmethod
    def get_resource_logs(
        cls, resource_type: str, resource_id: str, limit: int = 50
    ):
        """Get audit logs for a specific resource."""
        return AuditLog.objects.filter(
            resource_type=resource_type,
            resource_id=resource_id,
        ).order_by('-timestamp')[:limit]

    @classmethod
    def get_recent_admin_actions(cls, limit: int = 100):
        """Get the most recent admin actions for the ops dashboard."""
        admin_actions = [
            'CHANGE_ROLE', 'TOGGLE_USER_STATUS', 'WITHDRAWAL',
            'DEPOSIT', 'ADMIN_ADJUSTMENT',
        ]
        return AuditLog.objects.filter(
            action__in=admin_actions,
        ).select_related('user').order_by('-timestamp')[:limit]

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _get_ip(request) -> Optional[str]:
        """Extract IP address from Django request."""
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
