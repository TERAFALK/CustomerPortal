FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
    libcairo2 libgdk-pixbuf2.0-0 \
    libharfbuzz0b libfontconfig1 \
    libjpeg62-turbo libopenjp2-7 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Skapa data-kataloger och kör som icke-privilegierad användare.
# Katalogerna chownas så att nya namngivna volymer ärver rätt ägare.
RUN useradd -m -u 10001 appuser \
    && mkdir -p /app/reports_output /app/order_documents /app/ticket_attachments \
    && chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health').getcode()==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
