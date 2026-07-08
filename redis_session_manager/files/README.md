# Discord Bot — Redis Session Cache

## Files

| File | Purpose |
|---|---|
| `redis_session.py` | `SessionManager` class — the only thing you import in your bot |
| `bot.py` | Minimal discord.py example showing all session operations |
| `requirements.txt` | Python dependencies |
| `redis.conf` | Redis config — AOF + RDB persistence |
| `Dockerfile` | Builds the bot image for distribution |
| `docker-compose.yml` | Production: runs bot image + Redis together |
| `docker-compose.override.yml` | Local dev: Redis in Docker, bot runs natively |

---

## Local development

```bash
# 1. Start Redis only
docker compose up redis -d

# 2. Set your token
export DISCORD_TOKEN=your_token_here
export REDIS_HOST=localhost      # default, can omit

# 3. Run the bot — edit freely, no Docker rebuilds needed
python bot.py
```

Inspect session data at any time:
```bash
redis-cli
> KEYS session:*              # list all active sessions
> HGETALL session:123456789   # dump one user's session
> TTL session:123456789       # seconds until eviction
```

---

## Build & distribute

```bash
# Build
docker build -t yourhub/botname:latest .

# Push to Docker Hub (or any registry)
docker push yourhub/botname:latest
```

End users only need `docker-compose.yml` and `redis.conf`.
They create a `.env` file:
```
DISCORD_TOKEN=their_token_here
```
Then:
```bash
docker compose up -d
```

Redis data is stored on the host at `./redis_data/` — survives container
restarts and image upgrades.

---

## Persistence & crash safety

| Scenario | Data loss |
|---|---|
| Ctrl-C / `kill <pid>` / `docker stop` | ≤ 1 second (AOF `everysec`) |
| `kill -9` / power loss | ≤ 1 second of the most recent writes |
| Container removed & recreated | None — data is on the host volume |
| Image upgrade (`docker compose pull && up`) | None |

---

## SessionManager API

```python
from redis_session import SessionManager

session = SessionManager(ttl_seconds=7200)  # 2-hour sliding TTL

# Write
session.set(user_id, "language", "en")
session.set(user_id, "favourites", ["python", "redis"])   # lists fine
session.set_many(user_id, {"level": 5, "xp": 1200})      # atomic bulk write

# Read
session.get(user_id, "language")          # "en"
session.get(user_id, "missing", "en")     # default fallback
session.get_all(user_id)                  # full dict

# Inspect
session.exists(user_id)                   # bool
session.ttl_remaining(user_id)            # seconds

# Delete
session.delete_field(user_id, "xp")      # one field
session.delete_session(user_id)           # whole session
```

Every `get` and `set` resets the TTL (sliding expiration), so active
users stay in Redis while idle sessions are evicted automatically.
