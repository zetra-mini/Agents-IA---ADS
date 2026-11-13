FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    IN_DOCKER=true \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    ANONYMIZED_TELEMETRY=false \
    CREWAI_DISABLE_TELEMETRY=true \
    BROWSER_USE_SETUP_LOGGING=true

WORKDIR /app

# Dependências básicas de sistema + instalação dos navegadores Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python antes do código-fonte para aproveitar cache de camadas
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium --with-deps && \
    chmod -R a+rX /ms-playwright

# Cria usuário não-root e diretórios persistentes para sessão do navegador
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /app/browser_profile && \
    chown -R appuser:appuser /app

COPY --chown=appuser:appuser . .

USER appuser

EXPOSE 8000

# Bind explícito em 0.0.0.0 para evitar escuta apenas em IPv6 dentro do container
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
