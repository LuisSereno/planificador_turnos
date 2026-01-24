# -*- coding: utf-8 -*-
"""Configuración centralizada de logging."""
import logging


def configurar_logging():
    """Configura el logging global para la aplicación."""
    logger = logging.getLogger('turnos')
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        fh = logging.FileHandler('planificacion_debug.log', encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger


class LoggerConfig:
    """Clase para gestionar configuración de logging."""

    @staticmethod
    def obtener_logger(nombre):
        """Obtiene un logger configurado."""
        return logging.getLogger(nombre)
