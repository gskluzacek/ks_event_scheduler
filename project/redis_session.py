"""
redis_session.py
----------------
Per-user session cache for a Discord bot backed by Redis (Option B).

Each user gets a Redis Hash at key  session:<user_id>
Redis is both the in-memory cache AND the persistent store (AOF + RDB).
There is no TTL — sessions live until explicitly deleted or purged via
the /sessionreport slash command workflow.

Every read and write stamps a human-readable `last_accessed` field so
idle sessions can be identified without relying on Redis OBJECT IDLETIME.

Nested values (lists, dicts) are transparently JSON-serialised.

Also provides AppStateManager — a single global Redis Hash for
application-wide state (as opposed to per-user session state), using
the same JSON-in-Hash-field serialisation approach.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import redis

log = logging.getLogger(__name__)

_LAST_ACCESSED_FIELD = "last_accessed"
_LAST_ACCESSED_FMT   = "%Y-%m-%d %H:%M:%S UTC"


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime(_LAST_ACCESSED_FMT)


def _serialise(value: Any) -> str:
    """Encode any JSON-serialisable value to a string for Redis storage."""
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _deserialise(raw: str | bytes) -> Any:
    """Decode a Redis field value back to its original Python type."""
    if isinstance(raw, bytes):
        raw = raw.decode()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


class SessionManager:
    """
    Thin wrapper around a Redis Hash per Discord user.

    No TTL is set — Redis persists sessions indefinitely via AOF + RDB.
    Use the /sessionreport slash command to identify and review stale sessions.

    Parameters
    ----------
    host : str
        Redis host.  Defaults to REDIS_HOST env var, then 'localhost'.
    port : int
        Redis port.  Defaults to REDIS_PORT env var, then 6379.
    db : int
        Redis logical database index.
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        db: int = 0,
    ) -> None:
        resolved_host = host or os.getenv("REDIS_HOST", "localhost")
        resolved_port = port or int(os.getenv("REDIS_PORT", 6379))

        self._redis = redis.Redis(
            host=resolved_host,
            port=resolved_port,
            db=db,
            decode_responses=True,
        )
        log.info("SessionManager connected to Redis at %s:%s", resolved_host, resolved_port)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _key(self, user_id: int | str) -> str:
        return f"session:{user_id}"

    def _stamp(self, key: str) -> None:
        """Write last_accessed timestamp — called on every read and write."""
        self._redis.hset(key, _LAST_ACCESSED_FIELD, _now_str())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set(self, user_id: int | str, field: str, value: Any) -> None:
        """
        Write a single field into the user's session hash.

        Example
        -------
        session.set(ctx.author.id, "language", "en")
        session.set(ctx.author.id, "favourites", ["python", "redis"])
        """
        key = self._key(user_id)
        self._redis.hset(key, field, _serialise(value))
        self._stamp(key)
        log.debug("SET %s.%s", key, field)

    def set_many(self, user_id: int | str, data: dict[str, Any]) -> None:
        """
        Write an entire dict of fields into the user's session hash atomically.

        Example
        -------
        session.set_many(ctx.author.id, {"level": 5, "xp": 1200})
        """
        key = self._key(user_id)
        encoded = {field: _serialise(val) for field, val in data.items()}
        self._redis.hset(key, mapping=encoded)
        self._stamp(key)
        log.debug("SET_MANY %s  fields=%s", key, list(data.keys()))

    def get(self, user_id: int | str, field: str, default: Any = None) -> Any:
        """
        Read a single field from the user's session.
        Returns *default* if the session or field does not exist.
        Stamps last_accessed.
        """
        key = self._key(user_id)
        raw = self._redis.hget(key, field)
        if raw is None:
            return default
        self._stamp(key)
        return _deserialise(raw)

    def get_all(self, user_id: int | str) -> dict[str, Any]:
        """
        Return the entire session dict for a user, or {} if none exists.
        Stamps last_accessed.
        """
        key = self._key(user_id)
        raw = self._redis.hgetall(key)
        if not raw:
            return {}
        self._stamp(key)
        return {field: _deserialise(val) for field, val in raw.items()}

    def delete_field(self, user_id: int | str, field: str) -> None:
        """Remove a single field from the user's session."""
        self._redis.hdel(self._key(user_id), field)

    def delete_session(self, user_id: int | str) -> None:
        """Completely remove a user's session from Redis."""
        self._redis.delete(self._key(user_id))
        log.debug("Deleted session for user %s", user_id)

    def clear_all(self) -> int:
        """
        Remove all per-user session hashes from Redis.

        Returns
        -------
        int
            Number of session keys deleted.
        """
        keys = self.all_session_keys()
        if not keys:
            return 0

        deleted = self._redis.delete(*keys)
        log.debug("Deleted all user sessions; count=%s", deleted)
        return deleted

    def exists(self, user_id: int | str) -> bool:
        """Return True if the user has a session in Redis."""
        return self._redis.exists(self._key(user_id)) == 1

    def all_session_keys(self) -> list[str]:
        """Return all session:* keys currently in Redis."""
        return self._redis.keys("session:*")

    def get_last_accessed(self, user_id: int | str) -> datetime | None:
        """
        Return the last_accessed timestamp for a user as a UTC datetime,
        or None if the session doesn't exist or predates this field.
        """
        key = self._key(user_id)
        raw = self._redis.hget(key, _LAST_ACCESSED_FIELD)
        if raw is None:
            return None
        try:
            return datetime.strptime(raw, _LAST_ACCESSED_FMT).replace(tzinfo=timezone.utc)
        except ValueError:
            return None


_APP_STATE_KEY = "appstate:global"


class AppStateManager:
    """
    Single global Redis Hash for application-wide state.

    Same idea as SessionManager, but there's only one key
    ('appstate:global') instead of one per user — think of it as a
    session for the *application itself* rather than for a Discord user.
    Fields are stored/retrieved individually; each field's value can be
    a scalar, list, or dict (JSON-encoded transparently, same as
    SessionManager).

    Parameters
    ----------
    redis_client : redis.Redis, optional
        Reuse an existing connection (e.g. session._redis) instead of
        opening a second one. If omitted, connects using the same
        host/port env-var resolution as SessionManager.
    """

    def __init__(
        self,
        redis_client: "redis.Redis | None" = None,
        host: str | None = None,
        port: int | None = None,
        db: int = 0,
    ) -> None:
        if redis_client is not None:
            self._redis = redis_client
        else:
            resolved_host = host or os.getenv("REDIS_HOST", "localhost")
            resolved_port = port or int(os.getenv("REDIS_PORT", 6379))
            self._redis = redis.Redis(
                host=resolved_host,
                port=resolved_port,
                db=db,
                decode_responses=True,
            )
            log.info(
                "AppStateManager connected to Redis at %s:%s", resolved_host, resolved_port
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def exists(self) -> bool:
        """Return True if the app-state hash exists and has at least one field."""
        return self._redis.exists(_APP_STATE_KEY) == 1

    def set(self, field: str, value: Any) -> None:
        """
        Write a single field into the global app-state hash.

        Example
        -------
        app_state.set("maintenance_mode", False)
        app_state.set("active_events", [101, 102, 103])
        app_state.set("alliance_configs", {"KS1": {"tz": "UTC"}})
        """
        self._redis.hset(_APP_STATE_KEY, field, _serialise(value))
        log.debug("APPSTATE SET %s", field)

    def set_many(self, data: dict[str, Any]) -> None:
        """
        Write multiple fields into the global app-state hash atomically.

        Example
        -------
        app_state.set_many({"maintenance_mode": False, "active_events": [101, 102]})
        """
        encoded = {field: _serialise(val) for field, val in data.items()}
        self._redis.hset(_APP_STATE_KEY, mapping=encoded)
        log.debug("APPSTATE SET_MANY fields=%s", list(data.keys()))

    def get(self, field: str, default: Any = None) -> Any:
        """Read a single field. Returns *default* if the field doesn't exist."""
        raw = self._redis.hget(_APP_STATE_KEY, field)
        if raw is None:
            return default
        return _deserialise(raw)

    def get_all(self) -> dict[str, Any]:
        """Return the entire app-state dict, or {} if nothing has been set."""
        raw = self._redis.hgetall(_APP_STATE_KEY)
        return {field: _deserialise(val) for field, val in raw.items()}

    def delete_field(self, field: str) -> None:
        """Remove a single field from the app state."""
        self._redis.hdel(_APP_STATE_KEY, field)
        log.debug("APPSTATE DELETE %s", field)

    def has_field(self, field: str) -> bool:
        """Return True if the given field exists in the app state."""
        return self._redis.hexists(_APP_STATE_KEY, field) == 1

    def clear(self) -> None:
        """Wipe the entire app-state hash."""
        self._redis.delete(_APP_STATE_KEY)
        log.debug("APPSTATE cleared")
