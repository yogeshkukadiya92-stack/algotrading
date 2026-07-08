FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY apps/api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api/app app
COPY apps/api/alembic alembic
COPY apps/api/alembic.ini alembic.ini
COPY apps/api/pyproject.toml pyproject.toml
COPY packages /packages
COPY services/market_data_service /services/market_data_service
COPY services/paper_trading_service /services/paper_trading_service

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
