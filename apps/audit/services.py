"""Serviço de escrita de logs de auditoria."""

from __future__ import annotations

from apps.audit.models import AuditLog


def get_client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_action(
    *,
    user=None,
    action: str,
    description: str,
    object_type: str = "",
    object_id: str | int = "",
    request=None,
    ip_address: str | None = None,
) -> AuditLog:
    ip = ip_address or get_client_ip(request)
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id != "" else "",
        description=description,
        ip_address=ip,
    )
