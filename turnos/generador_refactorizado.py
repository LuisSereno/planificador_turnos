# -*- coding: utf-8 -*-
"""Módulo principal para la generación de planificación de turnos."""
import logging
import json
from datetime import timedelta
from ortools.sat.python import cp_model
from .variables import AdministradorVariables
from .restricciones_duras import AplicadorRestriccionesDuras
from .restricciones_blandas import AplicadorRestriccionesBlandas
from .patrones import AplicadorPatronesPersonalizados
from .resolvedor import ResolvedorModelo
from .logger_config import LoggerConfig

logger = logging.getLogger(__name__)


class GeneradorTurnos:
    """Clase principal que orquesta la generación de turnos."""

    def __init__(self, configuracion):
        self.configuracion = configuracion
        self.model = cp_model.CpModel()
        self.num_dias = configuracion.num_dias
        self.enfermeras = list(configuracion.enfermeras.all())
        self.turnos = list(configuracion.turnos.all())
        self.num_enfermeras = len(self.enfermeras)
        self.num_turnos = len(self.turnos)

        self.turnos_map = {self.turnos[i].nombre: i for i in range(self.num_turnos)}
        self.acronimos_map = {self.turnos[i].codigo_corto: i for i in range(self.num_turnos) if self.turnos[i].codigo_corto}
        self.demanda = self.configuracion.demanda_por_turno or {}

        self.administrador_variables = AdministradorVariables(
            self.model, self.num_enfermeras, self.num_dias, self.num_turnos, self.turnos_map
        )

        logger.info('=' * 80)
        logger.info('INICIO GENERADOR')
        logger.info('=' * 80)
        logger.info(
            f"Config: {configuracion.nombre} | Días: {self.num_dias} | Enfs: {self.num_enfermeras} | Turnos: {self.num_turnos}")
        
        # Comprimir JSON para logs
        demanda_json = json.dumps(self.demanda, separators=(',', ':'), ensure_ascii=False)
        logger.info(f"Demanda raw: {demanda_json}")

        self.log_configuracion_completa()

    def log_configuracion_completa(self):
        """Registra todos los parámetros de configuración."""
        try:
            logger.info('=' * 80)
            logger.info('CONFIGURACIÓN COMPLETA DE EJECUCIÓN')
            logger.info('=' * 80)

            logger.info('1. INFORMACIÓN BÁSICA')
            logger.info(f'  Nombre: {self.configuracion.nombre}')
            logger.info(f'  ID: {self.configuracion.id}')
            logger.info(f'  Descripción: {self.configuracion.descripcion or "N/A"}')
            logger.info(f'  Activa: {self.configuracion.activa}')
            logger.info(
                f'  Creado por: {self.configuracion.creado_por.username if self.configuracion.creado_por else "N/A"}')
            logger.info(f'  Fecha de creación: {self.configuracion.fecha_creacion}')

            logger.info('2. PERÍODO DE PLANIFICACIÓN')
            logger.info(f'  Número de días: {self.num_dias}')
            logger.info(f'  Fecha inicio: {self.configuracion.fecha_inicio}')
            fecha_fin = self.configuracion.fecha_inicio + timedelta(days=self.num_dias - 1)
            logger.info(f'  Fecha fin: {fecha_fin}')

            logger.info('3. RECURSOS HUMANOS')
            logger.info(f'  Total enfermeras: {self.num_enfermeras}')
            if self.num_enfermeras <= 20:
                for i, enf in enumerate(self.enfermeras, 1):
                    logger.info(f'    {i}. {enf.nombre} (ID: {enf.id})')

            logger.info('4. TIPOS DE TURNO')
            logger.info(f'  Total turnos: {self.num_turnos}')
            for i, turno in enumerate(self.turnos, 1):
                logger.info(f'    {i}. {turno.nombre}')

            logger.info('6. DEMANDA POR TURNO')
            for turno_nombre, demanda_value in self.demanda.items():
                if isinstance(demanda_value, dict):
                    min_d = demanda_value.get('min', 'N/A')
                    optimo = demanda_value.get('optimo', 'N/A')
                    max_d = demanda_value.get('max', 'N/A')
                    logger.info(f'  {turno_nombre}: min={min_d}, óptimo={optimo}, máx={max_d}')

            logger.info('8.5 PATRONES DE TURNOS')
            patrones = self.configuracion.get_patrones_combinados()
            if patrones:
                for idx, p in enumerate(patrones, 1):
                    tipo = p.get('tipo', 'N/A')
                    nombre = p.get('nombre', 'Sin nombre')
                    logger.info(f'  {idx}. {nombre} ({tipo})')
            else:
                logger.info('  NO APARECE NINGÚN PATRÓN')

            logger.info('=' * 80)

        except Exception as e:
            logger.warning(f"Error al loguear configuración: {str(e)}")

    def generar(self):
        """Genera la planificación completa."""
        self.administrador_variables.crear_todas()

        aplicador_rd = AplicadorRestriccionesDuras(
            self.model, self.turnos_map, self.turnos, self.num_enfermeras,
            self.num_dias, self.administrador_variables.shifts,
            self.administrador_variables.offdays, self.configuracion, self.demanda
        )
        aplicador_rd.aplicar_todas()

        aplicador_patrones = AplicadorPatronesPersonalizados(
            self.model, self.turnos_map, self.turnos, self.num_enfermeras,
            self.num_dias, self.administrador_variables.shifts,
            self.administrador_variables.offdays, self.configuracion,
            acronimos_map=self.acronimos_map
        )
        aplicador_patrones.aplicar_todos()

        aplicador_rb = AplicadorRestriccionesBlandas(
            self.model, self.turnos_map, self.turnos, self.num_enfermeras,
            self.num_dias, self.administrador_variables.shifts,
            self.configuracion, self.demanda, aplicador_patrones.patrones_penalties
        )
        aplicador_rb.aplicar_todas()

        resolvedor = ResolvedorModelo(
            self.model, self.configuracion, self.enfermeras,
            self.turnos, self.administrador_variables.shifts
        )
        return resolvedor.resolver()

    def resolver(self):
        """Alias para compatibilidad legacy."""
        return self.generar()
