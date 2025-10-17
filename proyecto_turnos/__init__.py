# Esto asegurará que la app Celery siempre se importa cuando Django inicia
from .celery import app as celery_app

__all__ = ('celery_app',)
