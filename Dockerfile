# A read-only DATAHQ: the pages, the live DuckDB, the evidence screenshots and the signed releases. No agents, no Chrome, no writes.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
ENV LEDGER_READONLY=1 PORT=3610 PATH="/app/.venv/bin:$PATH"
EXPOSE 3610
CMD ["python", "-m", "ledger", "app", "--host", "0.0.0.0"]
