FROM python:3.12-slim

WORKDIR /app

# Copy dependency list from the web-server folder
COPY web-server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY web-server/app ./app

# Copy UI (sibling folder at repo root)
COPY web-ui ./web-ui

EXPOSE 9000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
