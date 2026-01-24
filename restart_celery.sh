#!/bin/bash
# Script para reiniciar Celery y recargar el código actualizado

echo "════════════════════════════════════════════════════════════"
echo "REINICIANDO CELERY WORKER Y BEAT"
echo "════════════════════════════════════════════════════════════"

# 1. Eliminar procesos de Celery anteriores
echo "1. Deteniendo procesos Celery anteriores..."
pkill -f 'celery.*worker' || true
pkill -f 'celery.*beat' || true
sleep 2

# 2. Limpiar archivos de estado/caché
echo "2. Limpiando archivos de caché y estado..."
rm -f celerybeat-schedule
rm -f *.db
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# 3. Reiniciar Celery Worker
echo "3. Iniciando Celery Worker con reload automático..."
celery -A proyecto_turnos worker -l info --autoscale=4,1 &
WORKER_PID=$!
echo "   Worker PID: $WORKER_PID"

# 4. Reiniciar Celery Beat (opcional, si usas scheduled tasks)
echo "4. Iniciando Celery Beat..."
celery -A proyecto_turnos beat -l info &
BEAT_PID=$!
echo "   Beat PID: $BEAT_PID"

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✓ Celery reiniciado correctamente"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "PIDs en ejecución:"
echo "  Worker: $WORKER_PID"
echo "  Beat:   $BEAT_PID"
echo ""
echo "Para detener Celery:"
echo "  kill $WORKER_PID $BEAT_PID"
echo ""

