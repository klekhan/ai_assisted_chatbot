FROM python:3.11-slim

WORKDIR /app

# System deps needed by some PDF/docx libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Constrain thread pools used by onnxruntime/tokenizers — their defaults size
# themselves to the host machine, which easily overshoots a 512MB container.
ENV OMP_NUM_THREADS=1
ENV TOKENIZERS_PARALLELISM=false

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
