# -*- coding: utf-8 -*-
import os
from celery import Celery

# CRÍTICO: Mismo settings que Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_turnos.settings')

app = Celery('proyecto_turnos')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')