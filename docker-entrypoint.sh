#!/bin/bash
set -e

# Esperar a que los servicios dependientes estén disponibles
if [[ "$1" != "" ]]; then
    echo "Esperando a PostgreSQL..."
    /wait-for-it.sh db:5432 --timeout=60 -- echo "PostgreSQL está listo"

    echo "Esperando a Redis..."
    /wait-for-it.sh redis:6379 --timeout=60 -- echo "Redis está listo"
fi

echo "Iniciando: $*"
exec "$@"
