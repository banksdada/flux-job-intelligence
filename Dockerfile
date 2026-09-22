FROM python:3.12-slim

WORKDIR /app

# System deps: none beyond what python-docx/requests need (pure Python wheels).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persisted data (jobs/cv/bookmarks JSON) — mount a volume at /app/data
# in docker-compose.yml / Coolify's storage settings so it survives redeploys.
RUN mkdir -p /app/data
ENV FLUX_DATA_DIR=/app/data
ENV HOST=0.0.0.0
ENV PORT=8765

# Run as a non-root user.
RUN useradd --create-home --uid 1000 flux \
    && chown -R flux:flux /app
USER flux

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT','8765') + '/api/health', timeout=3)" || exit 1

CMD ["python", "app.py"]
