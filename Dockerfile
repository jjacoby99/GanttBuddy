FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/app \
    PORT=8080 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY scripts ./scripts
COPY src ./src

USER app

EXPOSE 8080

CMD ["sh", "-c", "python scripts/render_streamlit_secrets.py && streamlit run src/app.py --server.address=${HOST:-0.0.0.0} --server.port=${PORT:-8080}"]
