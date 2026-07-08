# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Create a non-root user with a real home directory (uv needs ~/.cache/uv
# at runtime; without -m -d, Python can't bootstrap and dies with
# "Failed to import encodings module").
RUN groupadd -r appuser && \
    useradd -r -g appuser -m -d /home/appuser appuser

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy project files (manifest + lockfile first for layer caching)
COPY pyproject.toml uv.lock ./

# Copy the actual application source code
COPY server/ ./server/
COPY streaming/ ./streaming/
COPY moviebox/ ./moviebox/
COPY web/ ./web/
COPY assets/ ./assets/

# Install dependencies (creates /app/.venv)
RUN uv sync --frozen --no-dev

# Ensure appuser owns everything (including the .venv)
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the application port
EXPOSE 8000

# Healthcheck on /manifest.json (the only root GET the addon exposes).
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/manifest.json || exit 1

# Start the server using the venv python directly (full path avoids
# PATH resolution issues and `uv run` overhead at runtime).
CMD ["/app/.venv/bin/python", "-m", "server.main"]
