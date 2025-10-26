# -*- coding: utf-8 -*-
"""
Configuración de Celery para proyecto_turnos
"""

import os
from celery import Celery

# ═══════════════════════════════════════════════════════════════
# IMPORTANTE: Usar el mismo settings que Django
# ═══════════════════════════════════════════════════════════════
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_turnos.settings')

app = Celery('proyecto_turnos')

# Leer configuración desde Django settings con namespace CELERY
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descubrir tareas en apps instaladas
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')