#!/bin/bash

# Script para detener el Planificador de Turnos
# Uso: ./stop.sh [--dev]
#   --dev         Detener servidor de desarrollo local (runserver)

MODE="prod"

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dev)
            MODE="dev"
            shift
            ;;
        --help|-h)
            echo "Uso: ./stop.sh [OPCIONES]"
            echo ""
            echo "Opciones:"
            echo "  --dev         Detener servidor de desarrollo local (runserver)"
            echo "  --help, -h    Muestra esta ayuda"
            exit 0
            ;;
        *)
            echo "❌ Argumento desconocido: $1"
            echo "Uso: ./stop.sh [--dev]"
            exit 1
            ;;
    esac
done

echo "🛑 Deteniendo Planificador de Turnos..."
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Este script debe ejecutarse desde el directorio del proyecto"
    exit 1
fi

if [ "$MODE" = "dev" ]; then
    echo "🔧 Deteniendo servicios de desarrollo..."
    echo ""

    # Buscar y matar procesos runserver
    RUNSERVER_PIDS=$(pgrep -f "python manage.py runserver" 2>/dev/null)

    if [ -n "$RUNSERVER_PIDS" ]; then
        echo "   Procesos runserver encontrados:"
        for PID in $RUNSERVER_PIDS; do
            echo "   - PID: $PID"
            kill $PID 2>/dev/null
        done
        echo "   ✅ runserver detenido"
    else
        echo "   No hay servidor de desarrollo activo"
    fi

    # Matar Celery worker
    CELERY_WORKER_PIDS=$(pgrep -f "celery.*worker" 2>/dev/null)
    if [ -n "$CELERY_WORKER_PIDS" ]; then
        echo "   Procesos Celery worker encontrados:"
        for PID in $CELERY_WORKER_PIDS; do
            echo "   - PID: $PID"
            kill $PID 2>/dev/null
        done
        echo "   ✅ Celery worker detenido"
    else
        echo "   No hay Celery worker activo"
    fi

    # Matar Celery beat
    CELERY_BEAT_PIDS=$(pgrep -f "celery.*beat" 2>/dev/null)
    if [ -n "$CELERY_BEAT_PIDS" ]; then
        echo "   Procesos Celery beat encontrados:"
        for PID in $CELERY_BEAT_PIDS; do
            echo "   - PID: $PID"
            kill $PID 2>/dev/null
        done
        echo "   ✅ Celery beat detenido"
    else
        echo "   No hay Celery beat activo"
    fi

    # Matar watchdog/reloader si quedan
    WATCHDOG_PIDS=$(pgrep -f "statreload" 2>/dev/null)
    if [ -n "$WATCHDOG_PIDS" ]; then
        for PID in $WATCHDOG_PIDS; do
            kill $PID 2>/dev/null
        done
    fi

    echo ""
    echo "💡 Si quedan procesos, ejecuta: pkill -f 'runserver|celery'"
    echo "💡 Redis se detiene automáticamente"

    # Detener contenedor Redis de desarrollo si existe
    REDIS_CONTAINER="planificador_dev_redis"
    if command -v podman &>/dev/null; then
        if podman ps -a --format '{{.Names}}' 2>/dev/null | grep -q "^${REDIS_CONTAINER}$"; then
            echo "   Deteniendo contenedor Redis ($REDIS_CONTAINER)..."
            podman stop $REDIS_CONTAINER 2>/dev/null && echo "   ✅ Redis container detenido"
            podman rm $REDIS_CONTAINER 2>/dev/null && echo "   ✅ Redis container eliminado"
        fi
    fi

else
    echo "🐳 Deteniendo contenedores Podman..."
    echo ""

    podman-compose down

    echo ""
    echo "✅ Todos los servicios han sido detenidos"
fi
