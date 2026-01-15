FROM python:3.12-slim

WORKDIR /app

# Copy dependency list from the api-server folder
COPY api-server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY api-server/app ./app

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
