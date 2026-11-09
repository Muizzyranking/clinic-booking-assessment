FROM ghcr.io/astral-sh/uv:latest AS uv
FROM python:3.13-slim
COPY --from=uv /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/srv/.venv/bin:$PATH" \
    DATABASE_PATH=/data/clinic.db

WORKDIR /srv

# Dependencies first so this layer is cached until the lockfile changes.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev

COPY app ./app
COPY entrypoint.sh ./entrypoint.sh

# The app runs as "app"; entrypoint.sh fixes volume ownership, then drops root.
RUN useradd --system --uid 1000 app \
    && mkdir /data \
    && chown app:app /data \
    && chmod +x /srv/entrypoint.sh

# Mount a persistent volume at /data so bookings survive restarts and redeploys.
VOLUME ["/data"]
EXPOSE 8000

ENTRYPOINT ["/srv/entrypoint.sh"]
# PORT is set by most hosts; 8000 otherwise. SQLite (WAL + BEGIN IMMEDIATE) keeps
# several workers on one volume consistent.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --proxy-headers --forwarded-allow-ips='*'"]
