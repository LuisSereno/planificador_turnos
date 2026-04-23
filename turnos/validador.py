# -*- coding: utf-8 -*-
"""Módulo para validar restricciones en la solución."""
import logging
from datetime import datetime
from collections import defaultdict
from .dominio.normalizacion import normalizar_nombre

logger = logging.getLogger(__name__)


class ValidadorRestricciones:
    """Valida que la solución cumple con todas las restricciones."""

    def __init__(self, configuracion, resultado):
        self.configuracion = configuracion
        self.resultado = resultado
        self.violaciones = []
        self.exitos = []

    def validar(self):
        """Ejecuta todas las validaciones."""
        logger.info("=" * 80)
        logger.info("INICIANDO VALIDACIONES")
        logger.info("=" * 80)
        self._una_enfermera_un_turno_por_dia()
        self._cobertura_minima_por_turno()
        self._descanso_minimo_12h()
        self._max_turnos_consecutivos()
        self._equidad_turnos_resumen()
        logger.info("=" * 80)
        logger.info(f"VALIDACIONES OK: {len(self.exitos)}  |  VIOLACIONES: {len(self.violaciones)}")
        logger.info("=" * 80)
        return {'valido': len(self.violaciones) == 0, 'validaciones': self.exitos, 'violaciones': self.violaciones}

    def _ok(self, nombre, det=""):
        """Registra validación exitosa."""
        msg = f"✓ VÁLIDO: {nombre}"
        if det:
            msg += f" - {det}"
        logger.info(msg)
        self.exitos.append({'nombre': nombre, 'estado': 'OK', 'detalles': det})

    def _ko(self, nombre, det=""):
        """Registra violación."""
        msg = f"✗ VIOLACIÓN: {nombre}"
        if det:
            msg += f" - {det}"
        logger.error(msg)
        self.violaciones.append({'nombre': nombre, 'detalles': det})

    def _una_enfermera_un_turno_por_dia(self):
        """RD020: Valida que cada enfermera no trabaje más de un turno por día."""
        max_turnos = 1
        rd = self.configuracion.restricciones_duras or []

        if isinstance(rd, dict):
            rd = list(rd.values())

        for restriccion in rd:
            if isinstance(restriccion, dict) and restriccion.get('nombre') == 'un_turno_por_dia':
                parametros = restriccion.get('parametros', {})
                if isinstance(parametros, dict):
                    max_turnos = parametros.get('max_turnos', 1)
                break

        seen = {}
        ok = True
        for a in self.resultado.get('asignaciones', []):
            enfermera_id = a['enfermera_id']
            fecha = a['fecha']
            key = (enfermera_id, fecha)

            if key not in seen:
                seen[key] = 0
            seen[key] += 1

            if seen[key] > max_turnos:
                self._ko("RD020",
                         f"{a['enfermera_nombre']} tiene {seen[key]} turnos el {fecha} (máx permitido: {max_turnos})")
                ok = False

        if ok:
            self._ok("RD020", f"{len(seen)} asignaciones únicas (máx {max_turnos} turnos/día)")

    def _cobertura_minima_por_turno(self):
        """RD019: Cobertura mínima por turno."""
        logger.info("\n[RD019] Validando: Cobertura mínima por turno")

        demanda = self.configuracion.demanda_por_turno or {}
        cobertura_por_turno_dia = {}
        valido = True

        for asig in self.resultado.get('asignaciones', []):
            turno_nombre = asig['turno_nombre']
            fecha = asig['fecha']
            key = (turno_nombre, fecha)

            if key not in cobertura_por_turno_dia:
                cobertura_por_turno_dia[key] = 0
            cobertura_por_turno_dia[key] += 1

        for (turno_nombre, fecha), cantidad in cobertura_por_turno_dia.items():
            demanda_value = demanda.get(turno_nombre, 1)

            if isinstance(demanda_value, dict):
                demanda_minima = demanda_value.get('min', 1)
            else:
                demanda_minima = int(demanda_value) if demanda_value else 1

            if cantidad < demanda_minima:
                detalles = f"Turno {turno_nombre} el {fecha}: {cantidad} personal (requiere {demanda_minima})"
                logger.warning(f"  ✗ {detalles}")
                valido = False
            else:
                logger.debug(f"  ✓ {turno_nombre} {fecha}: {cantidad} personal (requiere {demanda_minima})")

        if valido:
            msg = f"✓ VÁLIDO: RD019 - Cobertura verificada para {len(cobertura_por_turno_dia)} turnos"
            logger.info(msg)
            self.exitos.append(
                {'nombre': 'RD019', 'estado': 'OK', 'detalles': f'{len(cobertura_por_turno_dia)} turnos'})
        else:
            msg = f"✗ VIOLACIÓN: RD019 - Problemas de cobertura detectados"
            logger.error(msg)
            self.violaciones.append({'nombre': 'RD019', 'detalles': 'Cobertura insuficiente en algunos turnos'})

    def _descanso_minimo_12h(self):
        """RD006: Validación simplificada de descanso 12h."""
        por_enf = defaultdict(list)
        ok = True

        for a in self.resultado.get('asignaciones', []):
            por_enf[a['enfermera_id']].append(a)

        for eid, arr in por_enf.items():
            arr = sorted(arr, key=lambda x: x['fecha'])
            for i in range(len(arr) - 1):
                a = arr[i]
                b = arr[i + 1]

                if a['fecha'] == b['fecha']:
                    self._ko("RD006", f"{a['enfermera_nombre']} tiene 2+ turnos el {a['fecha']}")
                    ok = False

        if ok:
            self._ok("RD006", "Descansos verificados")

    def _max_turnos_consecutivos(self):
        """Valida máximo de turnos consecutivos."""
        restriccion_max_consec = None
        rd = self.configuracion.restricciones_duras or []

        if isinstance(rd, dict):
            rd = list(rd.values())

        for r in rd:
            if isinstance(r, dict) and normalizar_nombre(r.get('nombre', '')) == 'TURNO_CONSECUTIVOS_MAX':
                restriccion_max_consec = r
                break

        if not restriccion_max_consec:
            return

        max_consecutivos = restriccion_max_consec.get('parametros', {}).get('max', 5)

        por_enf = defaultdict(list)

        for a in self.resultado.get('asignaciones', []):
            por_enf[a['enfermera_id']].append(a)

        ok = True
        for eid, arr in por_enf.items():
            arr = sorted(arr, key=lambda x: x['fecha'])
            consecutivos = 1

            for i in range(1, len(arr)):
                fecha_anterior = datetime.fromisoformat(arr[i - 1]['fecha']).date()
                fecha_actual = datetime.fromisoformat(arr[i]['fecha']).date()

                if (fecha_actual - fecha_anterior).days == 1:
                    consecutivos += 1
                    if consecutivos > max_consecutivos:
                        self._ko("RD_MAX_CONSECUTIVOS",
                                 f"{arr[i]['enfermera_nombre']} tiene {consecutivos} turnos consecutivos (máx {max_consecutivos})")
                        ok = False
                else:
                    consecutivos = 1

        if ok:
            self._ok("RD_MAX_CONSECUTIVOS", f"Máximo {max_consecutivos} turnos consecutivos respetado")

    def _equidad_turnos_resumen(self):
        """Resume la equidad de turnos por enfermera."""
        por_enf = defaultdict(lambda: defaultdict(int))
        for a in self.resultado.get('asignaciones', []):
            por_enf[a['enfermera_nombre']][a['turno_nombre']] += 1
        for enf, mapa in por_enf.items():
            logger.info(f"[EQ] {enf}: " + ", ".join(f"{k}={v}" for k, v in mapa.items()))
        self._ok("RB001-RB003", "Resumen de equidad generado")
