# Imagen base de Python 3.11
FROM python:3.11-slim-bookworm

# Información del maintainer
LABEL maintainer="Planificador Turnos <admin@planificador.com>"
LABEL version="1.0"
LABEL description="Sistema de Planificación de Turnos de Enfermería"

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Crear usuario no-root para seguridad
RUN groupadd -r django && useradd -r -g django django

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dependencias de PostgreSQL
    libpq-dev \
    postgresql-client \
    # Dependencias de compilación
    gcc \
    g++ \
    make \
    # Herramientas útiles
    curl \
    wget \
    git \
    # Dependencias para reportes PDF
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    # Dependencias para OR-Tools
    libc-bin \
    # Limpieza
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear directorios
RUN mkdir -p /app /app/logs /app/media /app/static /app/staticfiles \
    && chown -R django:django /app

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements y instalar dependencias de Python
COPY --chown=django:django requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install gunicorn==21.2.0

# Copiar código de la aplicación
COPY --chown=django:django proyecto_turnos .

# Copiar scripts de entrada
COPY --chown=django:django docker-entrypoint.sh /docker-entrypoint.sh
COPY --chown=django:django wait-for-it.sh /wait-for-it.sh
RUN chmod +x /docker-entrypoint.sh /wait-for-it.sh

# Crear directorios adicionales
RUN mkdir -p /app/logs /app/media /app/staticfiles && \
    chown -R django:django /app/logs /app/media /app/staticfiles

# Cambiar a usuario no-root
USER django

# Exponer puerto
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Punto de entrada
ENTRYPOINT ["/docker-entrypoint.sh"]

# Comando por defecto
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "config.wsgi:application"]
