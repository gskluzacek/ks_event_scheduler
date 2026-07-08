"""
redis_session.py
----------------
Per-user session cache for a Discord bot backed by Redis.

Each user gets a Redis Hash at key  session:<user_id>
TTL is applied to the whole hash and reset on every read or write
(sliding expiration), keeping active users in memory while idle
sessions are evicted automatically by Redis.

Nested values (lists, dicts) are transparently JSON-serialised.
"""

import json
import logging
import os
from typing import Any

import redis

log = logging.getLogger(__name__)


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

    Parameters
    ----------
    ttl_seconds : int
        How long (seconds) an idle session stays in Redis before eviction.
        Every read or write resets the clock (sliding TTL).
    host : str
        Redis host.  Defaults to REDIS_HOST env var, then 'localhost'.
    port : int
        Redis port.  Defaults to REDIS_PORT env var, then 6379.
    db : int
        Redis logical database index.
    """

    def __init__(
        self,
        ttl_seconds: int = 3600,
        host: str | None = None,
        port: int | None = None,
        db: int = 0,
    ) -> None:
        self.ttl = ttl_seconds
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

    def _touch(self, key: str) -> None:
        """Reset the TTL on an existing key (sliding expiration)."""
        self._redis.expire(key, self.ttl)

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
        self._redis.expire(key, self.ttl)
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
        self._redis.expire(key, self.ttl)
        log.debug("SET_MANY %s  fields=%s", key, list(data.keys()))

    def get(self, user_id: int | str, field: str, default: Any = None) -> Any:
        """
        Read a single field from the user's session.
        Returns *default* if the session or field does not exist.
        Resets the TTL (sliding expiration).
        """
        key = self._key(user_id)
        raw = self._redis.hget(key, field)
        if raw is None:
            return default
        self._touch(key)
        return _deserialise(raw)

    def get_all(self, user_id: int | str) -> dict[str, Any]:
        """
        Return the entire session dict for a user, or {} if none exists.
        Resets the TTL.
        """
        key = self._key(user_id)
        raw = self._redis.hgetall(key)
        if not raw:
            return {}
        self._touch(key)
        return {field: _deserialise(val) for field, val in raw.items()}

    def delete_field(self, user_id: int | str, field: str) -> None:
        """Remove a single field from the user's session."""
        self._redis.hdel(self._key(user_id), field)

    def delete_session(self, user_id: int | str) -> None:
        """Completely remove a user's session from Redis."""
        self._redis.delete(self._key(user_id))
        log.debug("Deleted session for user %s", user_id)

    def exists(self, user_id: int | str) -> bool:
        """Return True if the user has an active session."""
        return self._redis.exists(self._key(user_id)) == 1

    def ttl_remaining(self, user_id: int | str) -> int:
        """Seconds until the session expires, or -2 if it doesn't exist."""
        return self._redis.ttl(self._key(user_id))
