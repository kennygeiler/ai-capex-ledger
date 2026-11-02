# A read-only Kenny's Data Emporium: the pages, the live DuckDB, the distilled XBRL instances, the evidence screenshots and the signed releases. No agents, no Chrome, no writes.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
# data/raw is not uploaded (3.6 GB). The restatement guard (proof._restated) reads the distilled XBRL instances
# (data/raw/<cik>/filings/<accession>.facts.json); the golden fixtures carry those for every company in scope, so the
# hosted copy reads them from there. Without them the hosted Proof counts restated rows open while the local one explains them.
RUN [ -d data/raw ] || cp -r fixtures/data/raw data/raw
ENV LEDGER_READONLY=1 PORT=3610 PATH="/app/.venv/bin:$PATH"
EXPOSE 3610
CMD ["python", "-m", "ledger", "app", "--host", "0.0.0.0"]
