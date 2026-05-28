#!/bin/bash

# Script para arrancar el Planificador de Turnos
# Uso: ./start.sh

echo "🏥 Planificador de Turnos - Iniciando servicios..."
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Este script debe ejecutarse desde el directorio del proyecto"
    exit 1
fi

# Verificar que podman está instalado
if ! command -v podman &> /dev/null; then
    echo "❌ Error: podman no está instalado"
    exit 1
fi

# Verificar que podman-compose está instalado
if ! command -v podman-compose &> /dev/null; then
    echo "❌ Error: podman-compose no está instalado"
    exit 1
fi

echo "📦 Levantando servicios con Podman..."
podman-compose up -d

echo ""
echo "⏳ Esperando a que los servicios estén listos..."
sleep 10

echo ""
echo "✅ Estado de los servicios:"
podman-compose ps

echo ""
echo "🌐 La aplicación está disponible en:"
echo "   http://localhost:8000"
echo ""
echo "👤 Credenciales de administrador:"
echo "   Usuario: admin"
echo "   Contraseña: Admin123!@#"
echo ""
echo "📋 Comandos útiles:"
echo "   Ver logs:     podman-compose logs -f"
echo "   Detener:      podman-compose down"
echo "   Reiniciar:    podman-compose restart"
echo "   Consola Django: podman-compose exec web python manage.py shell"
echo ""
