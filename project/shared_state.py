from redis_session import SessionManager, AppStateManager

_session: SessionManager | None = None
_app_state: AppStateManager | None = None

def init_shared_state():
    """Initialize the global SessionManager and AppStateManager."""
    global _session, _app_state
    _session = SessionManager()
    # reuse the same redis connection for AppStateManager
    _app_state = AppStateManager(redis_client=_session._redis)

def get_session() -> SessionManager:
    """Return the global UserSessionManager instance."""
    if _session is None:
        raise RuntimeError("SessionManager not initialized. Call init_shared_state() first.")
    return _session

def get_app_state() -> AppStateManager:
    """Return the global AppStateManager instance."""
    if _app_state is None:
        raise RuntimeError("AppStateManager not initialized. Call init_shared_state() first.")
    return _app_state
