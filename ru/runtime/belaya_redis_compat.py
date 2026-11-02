"""belaya-mgla-bot: redis-py 8 fix for unix-socket connections.

The production compose talks to Redis over ``unix:///var/run/redis/redis.sock``.
redis-py 8 enables RESP3 "maintenance notifications" and, for a
``UnixDomainSocketConnection`` (``host`` is ``None``), raises
``ValueError: Cannot enable maintenance notifications for connection object that
doesn't have a host attribute`` on fresh connections. That breaks the scheduler
wake-pop loop and dashboard writes. Maintenance notifications only matter for
managed TCP endpoints, so a host-less connection skips the handshake.

Loaded for every Python process via ``belaya_redis_compat.pth``.
"""

from __future__ import annotations


def _apply() -> None:
    try:
        from redis import connection as _conn
    except Exception:
        return
    for name in ("AbstractConnection", "Connection"):
        cls = getattr(_conn, name, None)
        orig = getattr(cls, "_enable_maintenance_notifications", None) if cls else None
        if orig is None or getattr(orig, "_belaya_patch", False):
            continue

        def _patched(self, *args, _orig=orig, **kwargs):
            if getattr(self, "host", None) is None:
                return None
            return _orig(self, *args, **kwargs)

        _patched._belaya_patch = True
        cls._enable_maintenance_notifications = _patched
        return


_apply()
