FROM python:3.12-alpine

WORKDIR /app

# Les dépendances d'abord pour profiter du cache Docker
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# Le code source
COPY src/ ./src/
RUN pip install --no-cache-dir --no-deps .

CMD ["bot"]
