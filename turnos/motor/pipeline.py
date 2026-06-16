# -*- coding: utf-8 -*-
"""
Pipeline principal de planificación.
Orquesta las fases: rotación base → ajuste horas → cobertura → reparación →
validación.

La generación automática SOLO produce turnos regulares (patrón base + ajustes).
Las incidencias (vacaciones, permisos, bajas) se aplican manualmente después
sobre la planificación ya generada, usando OverlayIncidencias como herramienta
independiente.
"""
import logging
from datetime import date
from typing import List, Dict, Optional

from ..dominio.dtos import (
    MatrizPlanificacion,
    ResultadoPlanificacion,
    RotacionCiclo,
    Incidencia,
)
from .rotacion_base import RotacionBaseBuilder
from .ajuste_horas import AjustadorHoras
from .cobertura import AnalizadorCobertura
from .reparador import ReparadorCPSAT
from .validador_motor import ValidadorMotor

logger = logging.getLogger(__name__)


class PipelinePlanificacion:
    """
    Orquestador del pipeline de planificación.
    
    Ejecuta las fases secuenciales:
    1. Construcción determinista de rotación base
    2. Ajuste de horas por contrato (exceso/déficit)
    3. Cálculo de cobertura y desviaciones
    4. Reparación con CP-SAT (si hay conflictos)
    5. Validación del resultado
    
    Las incidencias (vacaciones, permisos, bajas) NO se aplican durante la
    generación automática. Se aplican manualmente después usando
    OverlayIncidencias como herramienta independiente.
    """
    
    def __init__(
        self,
        fechas: List[date],
        enfermeras: Dict[int, str],
        asignaciones_rotacion: Dict[int, RotacionCiclo],
        desfases: Dict[int, int],
        incidencias: List[Incidencia] = None,
        horas_objetivo: Dict[int, float] = None,
        cobertura_minima: Optional[Dict[int, int]] = None,
        configuracion_solver: Optional[Dict] = None,
        turnos_info: Optional[Dict[int, 'TurnoInfo']] = None,
        restricciones_duras: List[dict] = None,
        restricciones_blandas: List[dict] = None,
        balances_historicos: Optional[Dict[int, dict]] = None,
    ):
        self.fechas = fechas
        self.enfermeras = enfermeras
        self.asignaciones_rotacion = asignaciones_rotacion
        self.desfases = desfases
        self.incidencias = incidencias or []
        self.horas_objetivo = horas_objetivo or {}
        self.cobertura_minima = cobertura_minima or {}
        self.configuracion_solver = configuracion_solver or {}
        self.turnos_info = turnos_info or {}
        self.restricciones_duras = restricciones_duras or []
        self.restricciones_blandas = restricciones_blandas or []
        self.balances_historicos = balances_historicos or {}
        
        # Normalizar cobertura_minima para asegurar que sean enteros
        self.cobertura_minima = self._normalizar_cobertura_minima(self.cobertura_minima)
    
    def _normalizar_cobertura_minima(self, cobertura: dict) -> dict:
        """
        Normaliza la cobertura mínima para asegurar que los valores sean enteros.
        
        Maneja tanto el formato antiguo (int) como el nuevo (dict con min/optimo/max).
        """
        cobertura_normalizada = {}
        for turno_id, valor in cobertura.items():
            if isinstance(valor, dict):
                cobertura_normalizada[turno_id] = valor.get('min', 0)
            else:
                cobertura_normalizada[turno_id] = int(valor) if valor else 0
        return cobertura_normalizada
        
    def ejecutar(self) -> ResultadoPlanificacion:
        """
        Ejecuta el pipeline de planificación en 5 fases.
        
        SOLO genera turnos regulares (patrón base + ajustes del solver).
        Las incidencias (vacaciones, permisos, bajas) NO se aplican aquí;
        se aplican manualmente después con OverlayIncidencias.
        
        Returns:
            ResultadoPlanificacion con la matriz de turnos regulares
        """
        logger.info("=" * 80)
        logger.info("INICIANDO PIPELINE DE PLANIFICACIÓN (5 fases)")
        logger.info("=" * 80)
        
        try:
            # ── FASE 1: Construcción de rotación base ──────────────────────
            logger.info("FASE 1: Construyendo rotación base...")
            matriz_base = RotacionBaseBuilder(
                fechas=self.fechas,
                enfermeras=self.enfermeras,
                asignaciones_rotacion=self.asignaciones_rotacion,
                desfases=self.desfases,
            ).construir()
            logger.info(f"Rotación base: {matriz_base.total_celdas()} celdas generadas")
            
            # ── FASE 2: Ajuste de horas por contrato ──────────────────────
            logger.info("FASE 2: Ajustando horas por contrato...")
            matriz_ajustada = AjustadorHoras(
                matriz=matriz_base,
                horas_objetivo=self.horas_objetivo,
                turnos_info=self.turnos_info,
            ).ajustar()
            
            # Contar celdas modificadas por el ajuste de horas
            celdas_modificadas_ajuste = sum(
                1 for enf_id in matriz_ajustada.celdas
                for fecha, celda in matriz_ajustada.celdas[enf_id].items()
                if celda._turno_base_original_id is not None and celda.turno is None
                or (celda._turno_base_original_id is None and celda.turno is not None)
                or (celda._turno_base_original_id is not None and celda.turno is not None
                    and celda._turno_base_original_id != celda.turno.id)
            )
            logger.info(f"Ajuste de horas: {celdas_modificadas_ajuste} celdas modificadas")
            
            # ── FASE 3: Análisis de cobertura ─────────────────────────────
            logger.info("FASE 3: Analizando cobertura...")

            from ..dominio.normalizacion import normalizar_nombre
            max_consecutivos = 6
            max_noches_consecutivas = 3
            for r in self.restricciones_duras:
                nombre_raw = r.get('nombre', '') or r.get('tipo', '')
                nombre_norm = normalizar_nombre(nombre_raw)
                params = r.get('parametros', {})
                if nombre_norm == 'TURNO_CONSECUTIVOS_MAX':
                    max_consecutivos = int(
                        params.get('max_dias_consecutivos', r.get('valor', 6))
                    )
                elif nombre_norm == 'NOCHES_CONSECUTIVAS_MAX':
                    max_noches_consecutivas = int(
                        params.get('max_noches_consecutivas', r.get('valor', 3))
                    )

            analisis = AnalizadorCobertura(
                matriz=matriz_ajustada,
                horas_objetivo_enfermeras=self.horas_objetivo,
                cobertura_minima_turnos=self.cobertura_minima,
                balances_historicos=self.balances_historicos,
                max_consecutivos=max_consecutivos,
                max_noches_consecutivas=max_noches_consecutivas,
            ).analizar()
            
            if analisis['tiene_conflictos']:
                logger.warning(f"{len(analisis['conflictos'])} conflictos de cobertura detectados")
            else:
                logger.info("Sin conflictos de cobertura")
            
            # ── FASE 4: Reparación con CP-SAT (si es necesario) ───────────
            matriz_final = matriz_ajustada
            celdas_modificadas = 0
            estado_solver = 'NO_EJECUTADO'
            
            if analisis['tiene_conflictos']:
                logger.info("FASE 4: Iniciando reparación con CP-SAT...")
                reparador = ReparadorCPSAT(
                    matriz_bloqueada=matriz_ajustada,
                    analisis_cobertura=analisis,
                    turnos_info=self.turnos_info,
                    restricciones_duras=self.restricciones_duras,
                    objetivos=self.restricciones_blandas,
                    cobertura_minima=self.cobertura_minima,
                    horas_objetivo=self.horas_objetivo,
                    balances_historicos=self.balances_historicos,
                )
                matriz_final = reparador.reparar()
                estado_solver = reparador.solver_status if hasattr(reparador, 'solver_status') else 'EJECUTADO'
                
                celdas_modificadas = sum(
                    1
                    for enf_id in matriz_final.celdas
                    for fecha, celda in matriz_final.celdas[enf_id].items()
                    if matriz_ajustada.obtener_celda(enf_id, fecha) and \
                       celda.turno != matriz_ajustada.obtener_celda(enf_id, fecha).turno
                )
                logger.info(f"Reparación completada: {celdas_modificadas} celdas modificadas")
            else:
                logger.info("FASE 4: No se requiere reparación")
            
            # ── FASE 5: Validación del resultado ──────────────────────────
            logger.info("FASE 5: Validando resultado...")
            
            configuracion_validador = self._extraer_configuracion_validador()
            
            validador = ValidadorMotor(
                matriz=matriz_final,
                turnos_info=self.turnos_info,
                configuracion=configuracion_validador,
                balances_historicos=self.balances_historicos,
            )
            
            resultado_validacion = validador.validar()
            
            # Construir resultado final (solo turnos regulares, sin overlay)
            resultado = ResultadoPlanificacion(
                exitosa=resultado_validacion.exitosa,
                matriz=matriz_final,
                balances=resultado_validacion.balances,
                metricas=resultado_validacion.metricas,
                estado_solver=estado_solver,
                tiempo_resolucion=resultado_validacion.tiempo_resolucion,
                celdas_modificadas=celdas_modificadas,
                celdas_totales=resultado_validacion.celdas_totales,
                restricciones_duras_cumplidas=resultado_validacion.restricciones_duras_cumplidas,
                violaciones=resultado_validacion.violaciones,
                warnings=resultado_validacion.warnings,
            )
            
            logger.info("=" * 80)
            logger.info("PIPELINE COMPLETADO EXITOSAMENTE")
            logger.info("=" * 80)
            
            return resultado
            
        except Exception as e:
            logger.error(f"Error en pipeline: {str(e)}", exc_info=True)
            return ResultadoPlanificacion(
                exitosa=False,
                matriz=MatrizPlanificacion(),
                balances={},
                metricas={},
                estado_solver='ERROR',
                violaciones=[str(e)],
            )

    def _extraer_configuracion_validador(self) -> dict:
        """Extrae configuración para el validador desde restricciones duras."""
        from ..dominio.normalizacion import normalizar_nombre
        
        configuracion = {
            'COBERTURA_MINIMA': self.cobertura_minima,
        }
        
        for r in self.restricciones_duras:
            nombre_raw = r.get('nombre', '') or r.get('tipo', '')
            nombre_normalizado = normalizar_nombre(nombre_raw)
            if nombre_normalizado == 'TURNO_CONSECUTIVOS_MAX':
                configuracion['TURNO_CONSECUTIVOS_MAX'] = int(r.get('valor', 6))
            elif nombre_normalizado == 'NOCHES_CONSECUTIVAS_MAX':
                configuracion['NOCHES_CONSECUTIVAS_MAX'] = int(r.get('valor', 3))
        
        configuracion.setdefault('TURNO_CONSECUTIVOS_MAX', 6)
        configuracion.setdefault('NOCHES_CONSECUTIVAS_MAX', 3)
        
        return configuracion
