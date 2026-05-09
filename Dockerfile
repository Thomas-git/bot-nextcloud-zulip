FROM python:3.12-alpine

WORKDIR /app

# Les dépendances d'abord pour profiter du cache Docker
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# Le code source
COPY src/ ./src/
RUN pip install --no-cache-dir --no-deps .

HEALTHCHECK --interval=2m --timeout=10s --start-period=30s --retries=3 \
    CMD python -c \
        "import os,time; s=os.stat('/tmp/bot_heartbeat'); exit(0 if time.time()-s.st_mtime<180 else 1)"

CMD ["bot"]
