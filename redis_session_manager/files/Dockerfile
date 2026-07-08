# Dockerfile
# ----------
# Builds the Discord bot image.
# Redis runs as a separate container (see docker-compose.yml).
#
# Build:  docker build -t yourhub/botname:latest .
# Push:   docker push yourhub/botname:latest

FROM python:3.12-slim

# Keeps Python from buffering stdout/stderr (important for docker logs)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first — layer is cached unless requirements change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source last so code changes don't invalidate the dependency layer
COPY . .

CMD ["python", "bot.py"]
