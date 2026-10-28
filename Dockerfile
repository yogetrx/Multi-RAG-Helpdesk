
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

COPY requirements.txt .

# Install application dependencies first, excluding the default PyTorch resolver
RUN grep -v '^sentence-transformers$' requirements.txt > /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt

# Install CPU-only PyTorch
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install Sentence Transformers using the existing CPU-only PyTorch
# Install Sentence Transformers and resolve its dependencies
RUN pip install --no-cache-dir sentence-transformers \
    --extra-index-url https://download.pytorch.org/whl/cpu

COPY src/ ./src/
COPY data/ ./data/

EXPOSE 8000

CMD ["uvicorn", "helpdesk.main:app", "--host", "0.0.0.0", "--port", "8000"]
