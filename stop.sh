#!/bin/bash

# Script para detener el Planificador de Turnos
# Uso: ./stop.sh

echo "🛑 Deteniendo Planificador de Turnos..."
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Este script debe ejecutarse desde el directorio del proyecto"
    exit 1
fi

podman-compose down

echo ""
echo "✅ Todos los servicios han sido detenidos"
