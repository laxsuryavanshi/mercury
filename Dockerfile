FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

EXPOSE 8000

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --frozen --no-install-project

COPY . .

# Creates a non-root user with an explicit UID and adds permission to access the /app folder
RUN adduser -u 5678 --disabled-password --gecos "" turtleby && chown -R turtleby /app
USER turtleby

ENTRYPOINT ["sh", "-c", ". .venv/bin/activate && exec \"$@\"", "--"]

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
