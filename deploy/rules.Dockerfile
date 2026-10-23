FROM python:3.12.10-slim@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY data/policies ./data/policies
RUN useradd --uid 10001 --create-home appuser
USER 10001
CMD ["uvicorn", "src.rules_api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
