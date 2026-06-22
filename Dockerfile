FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/app/static/uploads

RUN useradd -m -u 1000 user && chown -R user:user /app
USER user

ENV DEMO_MODE=true
ENV DATABASE_URL=sqlite+aiosqlite:///./school.db
RUN python seed_data.py

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
