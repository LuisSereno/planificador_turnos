#!/bin/bash

# Script para arrancar el Planificador de Turnos
# Uso: ./start.sh [--dev] [--port PUERTO]
#   --dev         Modo desarrollo local (sin Docker, usa SQLite y runserver)
#   --port PUERTO Puerto para el servidor (default: 8080 prod, 8001 dev)

MODE="prod"
PORT=""

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dev)
            MODE="dev"
            shift
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Uso: ./start.sh [OPCIONES]"
            echo ""
            echo "Opciones:"
            echo "  --dev         Modo desarrollo local (sin Docker, usa SQLite y runserver)"
            echo "  --port PUERTO Puerto para el servidor (default: 8080 prod, 8001 dev)"
            echo "  --help, -h    Muestra esta ayuda"
            echo ""
            echo "Ejemplos:"
            echo "  ./start.sh                # Modo producción con Podman"
            echo "  ./start.sh --dev          # Modo desarrollo local"
            echo "  ./start.sh --dev --port 9000  # Dev en puerto personalizado"
            exit 0
            ;;
        *)
            echo "❌ Argumento desconocido: $1"
            echo "Uso: ./start.sh [--dev] [--port PUERTO]"
            exit 1
            ;;
    esac
done

# Puertos por defecto
if [ -z "$PORT" ]; then
    if [ "$MODE" = "dev" ]; then
        PORT=8001
    else
        PORT=8080
    fi
fi

echo "🏥 Planificador de Turnos - Iniciando servicios..."
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "manage.py" ]; then
    echo "❌ Error: Este script debe ejecutarse desde el directorio del proyecto"
    exit 1
fi

if [ "$MODE" = "dev" ]; then
    echo "🔧 Modo: DESARROLLO LOCAL (SQLite + runserver + Celery)"
    echo ""

    # Verificar que existe el virtualenv
    if [ ! -d ".venv" ]; then
        echo "❌ Error: No se encuentra el directorio .venv"
        echo "   Crea el entorno virtual: python3 -m venv .venv"
        exit 1
    fi

    # Activar virtualenv e instalar dependencias si es necesario
    source .venv/bin/activate

    # Verificar que Django está instalado
    if ! python -c "import django" 2>/dev/null; then
        echo "📦 Instalando dependencias..."
        pip install -r requirements.txt >/dev/null 2>&1
    fi

    # Aplicar migraciones
    echo "🗄️ Aplicando migraciones..."
    python manage.py migrate --noinput 2>&1 | tail -3

    # Verificar superusuario
    echo "👤 Verificando superusuario..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@planificador.com', 'Admin123!@#')
    print('   Superusuario admin creado')
else:
    print('   Superusuario admin ya existe')
" 2>/dev/null

    echo ""

    # Iniciar Redis en contenedor Podman
    REDIS_AVAILABLE=false
    REDIS_CONTAINER="planificador_dev_redis"
    REDIS_PORT=6380  # Puerto diferente al de producción (6379)

    if command -v podman &>/dev/null; then
        # Verificar si el contenedor ya está corriendo
        if podman ps --format '{{.Names}}' 2>/dev/null | grep -q "^${REDIS_CONTAINER}$"; then
            echo "✅ Redis ya está corriendo en contenedor ($REDIS_CONTAINER, puerto $REDIS_PORT)"
            REDIS_AVAILABLE=true
        else
            echo "🔴 Iniciando Redis en contenedor Podman (puerto $REDIS_PORT)..."
            # Eliminar contenedor existente si hay
            podman rm -f $REDIS_CONTAINER &>/dev/null
            podman run -d --name $REDIS_CONTAINER \
                -p $REDIS_PORT:6379 \
                redis:7-alpine 2>/dev/null
            sleep 3

            if podman ps --format '{{.Names}}' 2>/dev/null | grep -q "^${REDIS_CONTAINER}$"; then
                echo "✅ Redis iniciado en contenedor ($REDIS_CONTAINER, puerto $REDIS_PORT)"
                REDIS_AVAILABLE=true
            else
                echo "⚠️  No se pudo iniciar Redis en contenedor"
                podman logs $REDIS_CONTAINER 2>&1 | tail -3
            fi
        fi
    elif command -v redis-server &>/dev/null; then
        # Fallback a Redis local si no hay podman
        if redis-cli ping 2>/dev/null | grep -q PONG; then
            echo "✅ Redis ya está corriendo (local)"
            REDIS_AVAILABLE=true
        else
            echo "🔴 Iniciando Redis local..."
            redis-server --daemonize yes --loglevel warning 2>/dev/null
            sleep 1
            if redis-cli ping 2>/dev/null | grep -q PONG; then
                echo "✅ Redis iniciado (local)"
                REDIS_AVAILABLE=true
            else
                echo "⚠️  No se pudo iniciar Redis"
            fi
        fi
    else
        echo "⚠️  Ni podman ni redis-server están disponibles"
    fi

    # Configurar variables de entorno para Celery
    if [ "$REDIS_AVAILABLE" = true ]; then
        export CELERY_BROKER_URL="redis://localhost:${REDIS_PORT}/0"
        export CELERY_RESULT_BACKEND="redis://localhost:${REDIS_PORT}/0"
        echo "✅ Celery broker: Redis (puerto $REDIS_PORT)"
    else
        export CELERY_BROKER_URL="memory://"
        export CELERY_RESULT_BACKEND="cache+memory://"
        echo "⚠️  Celery broker: memoria (solo para pruebas básicas)"
    fi

    # Iniciar Celery worker en background
    echo "🔨 Iniciando Celery worker..."
    celery -A proyecto_turnos worker -l info --concurrency=2 &>/tmp/celery_worker.log &
    CELERY_WORKER_PID=$!
    sleep 2

    if kill -0 $CELERY_WORKER_PID 2>/dev/null; then
        echo "✅ Celery worker iniciado (PID: $CELERY_WORKER_PID)"
    else
        echo "❌ Error al iniciar Celery worker. Ver /tmp/celery_worker.log"
        tail -5 /tmp/celery_worker.log
    fi

    # Iniciar Celery beat en background
    echo "⏰ Iniciando Celery beat..."
    celery -A proyecto_turnos beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler &>/tmp/celery_beat.log &
    CELERY_BEAT_PID=$!
    sleep 2

    if kill -0 $CELERY_BEAT_PID 2>/dev/null; then
        echo "✅ Celery beat iniciado (PID: $CELERY_BEAT_PID)"
    else
        echo "❌ Error al iniciar Celery beat. Ver /tmp/celery_beat.log"
        tail -5 /tmp/celery_beat.log
    fi

    echo ""
    echo "🚀 Iniciando servidor de desarrollo..."
    echo "   URL: http://localhost:$PORT"
    echo "   Login: admin / Admin123!@#"
    echo "   Ctrl+C para detener"
    echo ""
    echo "📋 Procesos activos:"
    echo "   - Django runserver (este terminal)"
    echo "   - Celery worker (PID: $CELERY_WORKER_PID)"
    echo "   - Celery beat (PID: $CELERY_BEAT_PID)"
    echo "   - Logs worker: /tmp/celery_worker.log"
    echo "   - Logs beat: /tmp/celery_beat.log"
    echo ""

    # Cleanup al salir
    cleanup() {
        echo ""
        echo "🛑 Deteniendo servicios..."
        [ -n "$CELERY_WORKER_PID" ] && kill $CELERY_WORKER_PID 2>/dev/null && echo "   Worker detenido"
        [ -n "$CELERY_BEAT_PID" ] && kill $CELERY_BEAT_PID 2>/dev/null && echo "   Beat detenido"
        # No parar Redis, puede ser reutilizado
        echo "💡 Redis queda activo (reutilizable). Para pararlo: ./stop.sh --dev"
        echo "✅ Servicios detenidos"
        exit 0
    }
    trap cleanup INT TERM

    python manage.py runserver 0.0.0.0:$PORT

else
    # Modo producción con Podman
    echo "🐳 Modo: PRODUCCIÓN (Podman + PostgreSQL + Redis)"
    echo ""

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

    echo "📦 Levantando servicios con Podman (reconstruyendo imágenes)..."
    podman-compose up -d --build

    echo ""
    echo "⏳ Esperando a que los servicios estén listos..."
    sleep 10

    echo ""
    echo "✅ Estado de los servicios:"
    podman-compose ps

    echo ""
    echo "🌐 La aplicación está disponible en:"
    echo "   http://localhost:$PORT"
    echo ""
    echo "👤 Credenciales de administrador:"
    echo "   Usuario: admin"
    echo "   Contraseña: Admin123!@#"
    echo ""
    echo "📋 Comandos útiles:"
    echo "   Ver logs:     podman-compose logs -f"
    echo "   Detener:      ./stop.sh"
    echo "   Reiniciar:    podman-compose restart"
    echo "   Consola Django: podman-compose exec web python manage.py shell"
    echo ""
fi
