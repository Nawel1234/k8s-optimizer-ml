# ============================================================
# Stage 1 : Build - installation des dependances
# ============================================================
FROM python:3.10-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ============================================================
# Stage 2 : Image finale allegee
# ============================================================
FROM python:3.10-slim

WORKDIR /app

# Copie uniquement les dependances installees (pas les outils de build)
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copie le code source de l'application
COPY api/ ./api/
COPY optimizer/ ./optimizer/
COPY collector/ ./collector/
COPY config/ ./config/
COPY models/ ./models/

# Installe curl pour le healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
