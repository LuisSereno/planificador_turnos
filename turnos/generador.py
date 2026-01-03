# -*- coding: utf-8 -*-
import logging
from datetime import timedelta, datetime
from ortools.sat.python import cp_model

logger = logging.getLogger(__name__)
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


class ValidadorRestricciones:
    def __init__(self, configuracion, resultado):
        self.configuracion = configuracion
        self.resultado = resultado
        self.violaciones = []
        self.exitos = []

    def _ok(self, nombre, det=""):
        msg = f"✓ VÁLIDO: {nombre}"
        if det: msg += f" - {det}"
        logger.info(msg)
        self.exitos.append({'nombre': nombre, 'estado': 'OK', 'detalles': det})

    def _ko(self, nombre, det=""):
        msg = f"✗ VIOLACIÓN: {nombre}"
        if det: msg += f" - {det}"
        logger.error(msg)
        self.violaciones.append({'nombre': nombre, 'detalles': det})

    def validar(self):
        logger.info("="*80)
        logger.info("INICIANDO VALIDACIONES")
        logger.info("="*80)
        self._una_enfermera_un_turno_por_dia()
        self._cobertura_minima_por_turno()
        self._descanso_minimo_12h()
        # Validaciones adicionales: descanso post-noche y máximo noches consecutivas
        self._descanso_post_noche()
        self._max_noches_consecutivas()
        self._jornada_maxima_12h()
        self._equidad_turnos_resumen()
        logger.info("="*80)
        logger.info(f"VALIDACIONES OK: {len(self.exitos)}  |  VIOLACIONES: {len(self.violaciones)}")
        logger.info("="*80)
        return {'valido': len(self.violaciones) == 0, 'validaciones': self.exitos, 'violaciones': self.violaciones}

    def _una_enfermera_un_turno_por_dia(self):
        """
        RD020: Valida que cada enfermera no trabaje más turnos por día de los permitidos.
        Ahora configurable con el parámetro `max_turnos`.
        """
        # Obtener max_turnos desde restricciones_duras
        max_turnos = 1  # valor por defecto
        rd = self.configuracion.restricciones_duras or []

        # Convertir a lista si es dict
        if isinstance(rd, dict):
            rd = list(rd.values())

        # Buscar la restricción "un_turno_por_dia" en la lista
        for restriccion in rd:
            if isinstance(restriccion, dict) and restriccion.get('nombre') == 'un_turno_por_dia':
                parametros = restriccion.get('parametros', {})
                if isinstance(parametros, dict):
                    max_turnos = parametros.get('max_turnos', 1)
                break

        # Validar asignaciones
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
                self._ko("RD020", f"{a['enfermera_nombre']} tiene {seen[key]} turnos el {fecha} (máx permitido: {max_turnos})")
                ok = False

        if ok:
            self._ok("RD020", f"{len(seen)} asignaciones únicas (máx {max_turnos} turnos/día)")

    def _cobertura_minima_por_turno(self):
        """RD019: Cobertura mínima por turno"""
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
            self.exitos.append({'nombre': 'RD019', 'estado': 'OK', 'detalles': f'{len(cobertura_por_turno_dia)} turnos'})
        else:
            msg = f"✗ VIOLACIÓN: RD019 - Problemas de cobertura detectados"
            logger.error(msg)
            self.violaciones.append({'nombre': 'RD019', 'detalles': 'Cobertura insuficiente en algunos turnos'})

    def _descanso_minimo_12h(self):
        from collections import defaultdict
        por_enf = defaultdict(list)
        ok = True
        id2turno = {t.id: t for t in self.configuracion.turnos.all()}
        for a in self.resultado.get('asignaciones', []):
            por_enf[a['enfermera_id']].append(a)
        for eid, arr in por_enf.items():
            arr = sorted(arr, key=lambda x: x['fecha'])
            for i in range(len(arr)-1):
                a = arr[i]
                b = arr[i+1]
                ta = id2turno.get(a['turno_id'])
                tb = id2turno.get(b['turno_id'])
                if not ta or not tb:
                    continue
                try:
                    # Get the date and time for the first shift
                    fecha_a = a['fecha']
                    # Ensure fecha_a is a string (should be, but handle cases)
                    if not isinstance(fecha_a, str):
                        fecha_a = fecha_a.isoformat()
                    
                    # Calculate the start datetime for a's shift
                    # Convert to datetime, then add the shift start time
                    start_dt_a = datetime.fromisoformat(fecha_a) + timedelta(hours=ta.hora_inicio.hour, minutes=ta.hora_inicio.minute)
                    
                    # Calculate the end datetime for a's shift using its duration or from start time and end time
                    if hasattr(ta, 'duracion_horas'):
                        duration = ta.duracion_horas
                        end_dt_a = start_dt_a + timedelta(hours=duration)
                    else:
                        # Fallback if duration is not available; compute from start to end time (accounting for possible date change)
                        end_dt_a = start_dt_a + timedelta(days=1) + timedelta(hours=ta.hora_fin.hour, minutes=ta.hora_fin.minute)
                        
                    # Get the date and time for the second shift
                    fecha_b = b['fecha']
                    if not isinstance(fecha_b, str):
                        fecha_b = fecha_b.isoformat()
                    
                    start_dt_b = datetime.fromisoformat(fecha_b) + timedelta(hours=tb.hora_inicio.hour, minutes=tb.hora_inicio.minute)
                    
                    # Now, check the interval between end of first shift and start of second shift
                    # Ensure we're comparing correct times
                    interval = (start_dt_b - end_dt_a).total_seconds() / 3600
                    
                    # Only log if interval is less than 12 hours, but ensure it's not negative due to time calculation errors
                    if interval < 0:
                        logger.warning(f"Illegal interval detected: {start_dt_b} before {end_dt_a}; something wrong with time calculation.")
                        self._ko("RD006", f"Error in time calculation for {eid}")
                    elif interval < 12:
                        self._ko("RD006", f"{a['enfermera_nombre']} {a['fecha']}->{b['fecha']} < 12h")
                        ok = False
                except Exception as e:
                    logger.error(f"Error processing shifts: {e}")
                    continue

        if ok:
            self._ok("RD006", "Descansos verificados")

    def _jornada_maxima_12h(self):
        ok = True
        id2turno = {t.id: t for t in self.configuracion.turnos.all()}
        for a in self.resultado.get('asignaciones', []):
            t = id2turno.get(a['turno_id'])
            if not t:
                continue
            if getattr(t, 'duracion_horas', 0) and t.duracion_horas > 12:
                self._ko("RD009", f"{a['enfermera_nombre']} {t.nombre} {t.duracion_horas}h")
                ok = False
        if ok:
            self._ok("RD009", "Jornadas <= 12h")

    def _equidad_turnos_resumen(self):
        from collections import defaultdict
        por_enf = defaultdict(lambda: defaultdict(int))
        for a in self.resultado.get('asignaciones', []):
            por_enf[a['enfermera_nombre']][a['turno_nombre']] += 1
        for enf, mapa in por_enf.items():
            logger.info(f"[EQ] {enf}: " + ", ".join(f"{k}={v}" for k,v in mapa.items()))
        self._ok("RB001-RB003", "Resumen de equidad generado")

    def _descanso_post_noche(self):
        """Valida la restricción RD_POST_NOCHE si está presente en la configuración.
        Busca en `configuracion.restricciones_duras` la restricción y aplica la comprobación de horas.
        """
        rd = self.configuracion.restricciones_duras or []
        if isinstance(rd, dict):
            rd = list(rd.values())
        id_map = {r.get('id'): r for r in rd}
        if 'RD_POST_NOCHE' not in id_map:
            return

        params = id_map['RD_POST_NOCHE'].get('parametros', {}) or {}
        min_horas = int(params.get('min_horas', params.get('minimo_horas', 12)))
        nocturnos_param = params.get('turnos')

        # mapear id->turno obj
        id2turno = {t.id: t for t in self.configuracion.turnos.all()}

        # determinar nombres de turnos nocturnos
        if nocturnos_param and isinstance(nocturnos_param, list):
            noches_nombres = set(nocturnos_param)
        else:
            noches_nombres = {'NOCHE'}

        # construir por enfermera
        from collections import defaultdict
        por_enf = defaultdict(list)
        for a in self.resultado.get('asignaciones', []):
            por_enf[a['enfermera_id']].append(a)

        for eid, arr in por_enf.items():
            arr = sorted(arr, key=lambda x: x['fecha'])
            for a in arr:
                ta = id2turno.get(a['turno_id'])
                if not ta or ta.nombre not in noches_nombres:
                    continue
                # es un turno nocturno: calcular fin
                try:
                    fecha_a = a['fecha'] if isinstance(a['fecha'], str) else a['fecha'].isoformat()
                    start_dt_a = datetime.fromisoformat(fecha_a) + timedelta(hours=ta.hora_inicio.hour, minutes=ta.hora_inicio.minute)
                    dur = getattr(ta, 'duracion_horas', None)
                    if dur is None:
                        # fallback: usar hora_fin
                        end_dt_a = datetime.fromisoformat(fecha_a) + timedelta(hours=ta.hora_fin.hour, minutes=ta.hora_fin.minute)
                    else:
                        end_dt_a = start_dt_a + timedelta(hours=dur)
                except Exception as ex:
                    logger.debug(f"No se pudo calcular fin de turno nocturno: {ex}")
                    continue

                # comparar con todas las asignaciones posteriores de la misma enfermera
                for b in arr:
                    if b == a:
                        continue
                    try:
                        fecha_b = b['fecha'] if isinstance(b['fecha'], str) else b['fecha'].isoformat()
                        start_dt_b = datetime.fromisoformat(fecha_b) + timedelta(hours=id2turno.get(b['turno_id']).hora_inicio.hour, minutes=id2turno.get(b['turno_id']).hora_inicio.minute)
                        interval_h = (start_dt_b - end_dt_a).total_seconds() / 3600
                        if 0 <= interval_h < min_horas:
                            self._ko('RD_POST_NOCHE', f"{a['enfermera_nombre']} {a['fecha']} -> {b['fecha']} intervalo {interval_h:.1f}h < {min_horas}h")
                    except Exception:
                        continue

        # si no se añaden violaciones, marcar OK
        if not any(v.get('nombre') == 'RD_POST_NOCHE' for v in self.violaciones):
            self._ok('RD_POST_NOCHE', f'Descanso post-noche >= {min_horas}h verificado')

    def _max_noches_consecutivas(self):
        """Valida RD_MAX_NOCHES_CONSECUTIVAS en restricciones duras."""
        rd = self.configuracion.restricciones_duras or []
        if isinstance(rd, dict):
            rd = list(rd.values())
        id_map = {r.get('id'): r for r in rd}
        if 'RD_MAX_NOCHES_CONSECUTIVAS' not in id_map:
            return

        params = id_map['RD_MAX_NOCHES_CONSECUTIVAS'].get('parametros', {}) or {}
        max_noches = int(params.get('max_noches', params.get('max', 2)))
        nocturnos_param = params.get('turnos')
        if nocturnos_param and isinstance(nocturnos_param, list):
            noches_nombres = set(nocturnos_param)
        else:
            noches_nombres = {'NOCHE'}

        from collections import defaultdict
        por_enf = defaultdict(list)
        for a in self.resultado.get('asignaciones', []):
            por_enf[a['enfermera_id']].append(a)

        violated = False
        for eid, arr in por_enf.items():
            arr = sorted(arr, key=lambda x: x['fecha'])
            consec = 0
            last_fecha = None
            for a in arr:
                if a.get('turno_nombre') in noches_nombres:
                    # comprobar si es día siguiente del anterior (consecutivo)
                    if last_fecha is None:
                        consec = 1
                    else:
                        # comparar fechas
                        try:
                            fa = a['fecha'] if isinstance(a['fecha'], str) else a['fecha'].isoformat()
                            fb = last_fecha
                            da = datetime.fromisoformat(fa).date()
                            db = datetime.fromisoformat(fb).date() if isinstance(fb, str) else fb
                            if (da - db).days == 1:
                                consec += 1
                            else:
                                consec = 1
                        except Exception:
                            consec += 1
                    last_fecha = a['fecha']
                else:
                    consec = 0
                    last_fecha = a['fecha']

                if consec > max_noches:
                    self._ko('RD_MAX_NOCHES_CONSECUTIVAS', f"{a['enfermera_nombre']} tiene {consec} noches consecutivas (máx {max_noches})")
                    violated = True

        if not violated:
            self._ok('RD_MAX_NOCHES_CONSECUTIVAS', f'Máximo de noches consecutivas <= {max_noches}')


class GeneradorTurnos:
    def __init__(self, configuracion):
        self.configuracion = configuracion
        self.model = cp_model.CpModel()
        self.num_dias = configuracion.num_dias
        self.enfermeras = list(configuracion.enfermeras.all())
        self.turnos = list(configuracion.turnos.all())
        self.num_enfermeras = len(self.enfermeras)
        self.num_turnos = len(self.turnos)
        self.shifts = {}
        self.off_days = {}
        self.extra_off_days = {}
        self.turnos_map = {self.turnos[i].nombre: i for i in range(self.num_turnos)}
        self.demanda = self.configuracion.demanda_por_turno or {}
        self.rd = self._restricciones_duras()
        self.rb = self._restricciones_blandas()

        logger.info("="*80)
        logger.info("INICIO GENERADOR")
        logger.info("="*80)
        logger.info(f"Config: {configuracion.nombre} | Días: {self.num_dias} | Enfs: {self.num_enfermeras} | Turnos: {self.num_turnos}")
        logger.info(f"Demanda raw: {self.demanda}")

    def _restricciones_duras(self):
        rd = self.configuracion.restricciones_duras
        if isinstance(rd, list):
            logger.info(f"RD (array): {len(rd)}")
            return rd
        if isinstance(rd, dict):
            logger.info(f"RD (dict): {len(rd)}")
            return list(rd.values())
        logger.info("RD vacías")
        return []

    def _restricciones_blandas(self):
        rb = self.configuracion.restricciones_blandas
        if isinstance(rb, list):
            logger.info(f"RB (array): {len(rb)}")
            return rb
        if isinstance(rb, dict):
            logger.info(f"RB (dict): {len(rb)}")
            return list(rb.values())
        logger.info("RB vacías")
        return []

    def crear_variables(self):
        total_shifts = self.num_enfermeras * self.num_dias * self.num_turnos
        logger.info(f"Creamos {total_shifts} variables de turno (shifts)")
        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                for t in range(self.num_turnos):
                    self.shifts[(e, d, t)] = self.model.NewBoolVar(f"e{e}_d{d}_t{t}")

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                self.off_days[(e, d)] = self.model.NewBoolVar(f"off_e{e}_d{d}")

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                turnos_ese_dia = [self.shifts[(e, d, t)] for t in range(self.num_turnos)]
                self.model.Add(sum(turnos_ese_dia) + self.off_days[(e, d)] == 1)
        logger.info(f"✓ Creadas {self.num_enfermeras * self.num_dias} variables de días libres (off_days)")

        idxN = self.turnos_map.get('NOCHE')
        if idxN is not None:
            for e in range(self.num_enfermeras):
                for d in range(self.num_dias):
                    self.extra_off_days[(e, d)] = self.model.NewBoolVar(f"extra_off_e{e}_d{d}")
                    if d == 0:
                        self.model.Add(self.extra_off_days[(e, d)] == self.off_days[(e, d)])
                    else:
                        noche_anterior = self.shifts[(e, d - 1, idxN)]
                        self.model.AddBoolAnd([self.off_days[(e, d)], noche_anterior.Not()]).OnlyEnforceIf(self.extra_off_days[(e, d)])
                        self.model.AddImplication(self.extra_off_days[(e, d)], self.off_days[(e, d)])
                        self.model.AddImplication(self.extra_off_days[(e, d)], noche_anterior.Not())
            logger.info(f"✓ Creadas {self.num_enfermeras * self.num_dias} variables de días libres extra (extra_off_days)")

    def aplicar_restricciones_duras(self):
        """Aplica restricciones duras, incluyendo cobertura MÍNIMA."""
        id_map = {r.get('id'): r for r in self.rd}
        idxN = self.turnos_map.get('NOCHE')
        idxM = self.turnos_map.get('MANANA')

        # RD020: Una enfermera, un turno por día
        # Ahora configurable: si la configuración tiene `turnos_por_dia` seleccionados, solo esos turnos se
        # consideran a la hora de aplicar la restricción. Si está vacío, se usan todos los turnos configurados.
        turnos_por_dia_qs = list(self.configuracion.turnos_por_dia.all()) if getattr(self.configuracion, 'turnos_por_dia', None) is not None else []
        if turnos_por_dia_qs:
            # mapear a índices
            indices_turnos_por_dia = [i for i, t in enumerate(self.turnos) if t in turnos_por_dia_qs]
        else:
            indices_turnos_por_dia = list(range(self.num_turnos))

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                self.model.Add(sum(self.shifts[(e, d, t)] for t in indices_turnos_por_dia) <= 1)
        logger.info("✓ RD020: Una enfermera, un turno por día (configurable)")

        # RD019: Cobertura mínima y máxima por turno
        logger.info(f"Aplicando RD019 con demanda: {self.demanda}")
        for d in range(self.num_dias):
            for t in range(self.num_turnos):
                nombre = self.turnos[t].nombre
                demanda_value = self.demanda.get(nombre)

                req_min, req_optimo, req_max = 1, None, self.num_enfermeras

                if isinstance(demanda_value, dict):
                    req_min = demanda_value.get('min', 1)
                    req_optimo = demanda_value.get('optimo')
                    req_max = demanda_value.get('max', self.num_enfermeras)
                    logger.debug(
                        f"  - {nombre} d{d}: min={req_min} (requerido), optimo={req_optimo} (preferido), max={req_max} (límite)")
                elif isinstance(demanda_value, (int, float)):
                    req_min = int(demanda_value)
                    logger.debug(f"  - {nombre} d{d}: min={req_min} (requerido), max={req_max} (límite)")

                personal_asignado = sum(self.shifts[(e, d, t)] for e in range(self.num_enfermeras))
                self.model.Add(personal_asignado >= req_min).OnlyEnforceIf(req_min > 0)
                self.model.Add(personal_asignado <= req_max)

        # RD006: Descanso mínimo 12h (prohibir NOCHE->MAÑANA)
        if idxN is not None and idxM is not None:
            for e in range(self.num_enfermeras):
                for d in range(self.num_dias - 1):
                    self.model.Add(self.shifts[(e, d, idxN)] + self.shifts[(e, d + 1, idxM)] <= 1)
            logger.info("✓ RD006: Descanso 12h (NOCHE->MAÑANA prohibido)")

        # RD021: Descanso obligatorio post-noche (legacy boolean)
        if 'RD021' in id_map and idxN is not None:
            for e in range(self.num_enfermeras):
                for d in range(self.num_dias - 1):
                    self.model.AddImplication(self.shifts[(e, d, idxN)], self.off_days[(e, d + 1)])
            logger.info("✓ RD021: Descanso obligatorio post-noche")

        # Nueva: RD_POST_NOCHE: descanso N horas después de turno nocturno (parámetros)
        if 'RD_POST_NOCHE' in id_map and idxN is not None:
            params = id_map['RD_POST_NOCHE'].get('parametros', {}) or {}
            min_horas = int(params.get('min_horas', params.get('minimo_horas', 12)))
            nocturnos_param = params.get('turnos')  # lista de nombres opcional

            # determinar índices de turnos considerados nocturnos
            if nocturnos_param and isinstance(nocturnos_param, list):
                noches_idx = [i for i, t in enumerate(self.turnos) if t.nombre in nocturnos_param]
            else:
                noches_idx = [idxN]

            # calcular prohibiciones por pares de turnos
            # Para cada turno nocturno en día d, prohibimos iniciar cualquier turno que comience antes de min_horas desde fin
            # del turno nocturno. Estimamos el fin usando tipo.turno.duracion_horas
            for e in range(self.num_enfermeras):
                for d in range(self.num_dias):
                    for tn in noches_idx:
                        for t2 in range(self.num_turnos):
                            # intentar calcular diferencia en horas entre fin de tn en día d y inicio de t2 en d+delta
                            tn_obj = self.turnos[tn]
                            t2_obj = self.turnos[t2]
                            dur_tn = getattr(tn_obj, 'duracion_horas', None)
                            if dur_tn is None:
                                continue
                            # fin estimado del turno nocturno
                            # si turno cruza medianoche, fin estará en d+1
                            # Duración en horas -> buscaremos el primer d2 >= d tal que inicio_t2 - fin_tn >= min_horas
                            for delta in range(0, (min_horas // 24) + 3):
                                d2 = d + delta
                                if d2 >= self.num_dias:
                                    break
                                # calcular horas entre fin_tn (d) y inicio_t2 (d2)
                                # start_dt_tn = fecha d + hora_inicio_tn
                                # end_dt_tn = start_dt_tn + dur_tn
                                # start_dt_t2 = fecha d2 + hora_inicio_t2
                                start_tn = datetime.combine(self.configuracion.fecha_inicio + timedelta(days=d), tn_obj.hora_inicio)
                                end_tn = start_tn + timedelta(hours=dur_tn)
                                start_t2 = datetime.combine(self.configuracion.fecha_inicio + timedelta(days=d2), t2_obj.hora_inicio)
                                interval_h = (start_t2 - end_tn).total_seconds() / 3600
                                # si interval_h < min_horas, prohibimos asignación conjunta
                                if interval_h < min_horas:
                                    # prohíbe tener tn en d y t2 en d2 para la misma enfermera
                                    self.model.Add(self.shifts[(e, d, tn)] + self.shifts[(e, d2, t2)] <= 1)
            logger.info(f"✓ RD_POST_NOCHE: Descanso obligatorio post-noche aplicado ({min_horas}h)")

        # Nueva: RD_MAX_NOCHES_CONSECUTIVAS: máximo noches consecutivas
        if 'RD_MAX_NOCHES_CONSECUTIVAS' in id_map and idxN is not None:
            params = id_map['RD_MAX_NOCHES_CONSECUTIVAS'].get('parametros', {}) or {}
            max_noches = int(params.get('max_noches', params.get('max', 2)))
            nocturnos_param = params.get('turnos')
            if nocturnos_param and isinstance(nocturnos_param, list):
                noches_idx = [i for i, t in enumerate(self.turnos) if t.nombre in nocturnos_param]
            else:
                noches_idx = [idxN]

            window = max_noches + 1
            for e in range(self.num_enfermeras):
                for start in range(0, self.num_dias - window + 1):
                    suma = None
                    for off in range(window):
                        d = start + off
                        for tn in noches_idx:
                            if suma is None:
                                suma = self.shifts[(e, d, tn)]
                            else:
                                suma = suma + self.shifts[(e, d, tn)]
                    if suma is not None:
                        self.model.Add(suma <= max_noches)
            logger.info(f"✓ RD_MAX_NOCHES_CONSECUTIVAS: Limitado a {max_noches} noches consecutivas")

        # RD021 y RD022 legacy ya aplicados anteriormente si presentes (ver arriba)

        # RD017+RD018: Vacaciones y asuntos particulares (proporción anual)
        dias_libres_requeridos = max(1, int((self.num_dias / 365) * 28))
        for e in range(self.num_enfermeras):
            dias_trabajados = sum(self.shifts[(e, d, t)] for d in range(self.num_dias) for t in range(self.num_turnos))
            self.model.Add(dias_trabajados <= self.num_dias - dias_libres_requeridos)
        logger.info(f"✓ RD017+RD018: Mínimo {dias_libres_requeridos} días libres por enfermera")

        # ✅ RD007: Descanso semanal - SOLO PARA PERÍODOS LARGOS (>= 300 días ≈ anual)
        if self.num_dias >= 300:
            # Número de semanas completas
            num_semanas = self.num_dias // 7

            # Aplicar RD007: al menos 1 día libre por semana (semanas completas)
            for e in range(self.num_enfermeras):
                for semana in range(num_semanas):
                    inicio_semana = semana * 7
                    fin_semana = min((semana + 1) * 7, self.num_dias)
                    # Suma los turnos en esa semana
                    turnos_en_semana = sum(
                        self.shifts[(e, d, t)]
                        for d in range(inicio_semana, fin_semana)
                        for t in range(self.num_turnos)
                    )
                    # Limitar a que tenga al menos un día libre (menos un turno en esa semana)
                    self.model.Add(turnos_en_semana <= (fin_semana - inicio_semana) - 1)
            logger.info("✓ RD007: Descanso semanal aplicado (1 día libre cada 7 días) (versión corregida)")
        else:
            # Para períodos cortos: solo garantizar mínimo 1 día libre total
            for e in range(self.num_enfermeras):
                dias_libres_totales = sum(self.off_days[(e, d)] for d in range(self.num_dias))
                # Al menos 1 día libre (ya garantizado por RD017+RD018, pero explícito)
                self.model.Add(dias_libres_totales >= 1)
            logger.info(f"✓ RD007: ADAPTADA para {self.num_dias} días (mínimo 1 día libre total)")

    def aplicar_restricciones_blandas(self):
        penal = []
        id_map = {r.get('id'): r for r in self.rb}

        logger.info("Aplicando restricciones blandas para cobertura óptima:")
        logger.info("- Mínimo (requerido): Solución debe cumplir este valor")
        logger.info("- Óptimo (preferido): Penalizamos desviaciones pero no afecta validez")
        logger.info("- Máximo (límite): Solución no puede superar este valor")

        tiene_optimo = False
        for d in range(self.num_dias):
            for t in range(self.num_turnos):
                nombre = self.turnos[t].nombre
                demanda_value = self.demanda.get(nombre)
                
                if isinstance(demanda_value, dict) and 'optimo' in demanda_value:
                    tiene_optimo = True
                    req_optimo = demanda_value['optimo']
                    personal_asignado = sum(self.shifts[(e, d, t)] for e in range(self.num_enfermeras))

                    # Penalización por no alcanzar el óptimo (más grave)
                    shortfall = self.model.NewIntVar(0, self.num_enfermeras, f'shortfall_d{d}_t{t}')
                    self.model.Add(shortfall >= req_optimo - personal_asignado)
                    
                    shortfall_sq = self.model.NewIntVar(0, self.num_enfermeras**2, f'shortfall_sq_d{d}_t{t}')
                    self.model.AddMultiplicationEquality(shortfall_sq, [shortfall, shortfall])

                    # Penalización por superar el óptimo (menos grave)
                    overage = self.model.NewIntVar(0, self.num_enfermeras, f'overage_d{d}_t{t}')
                    self.model.Add(overage >= personal_asignado - req_optimo)

                    # Aplicar pesos diferentes a las penalizaciones
                    penal.append(shortfall_sq * 0.1)  # Reduced weight from 100 to 10
                    penal.append(overage * 0.02)    # Reduced weight from 20 to 2
                    
                    logger.debug(f"  - {nombre} d{d}: optimo={req_optimo}, penalización por falta (x0.1 cuadrática) y exceso (x0.02 lineal)")
        
        if tiene_optimo:
            logger.info("✓ RB Cobertura óptima aplicada con penalización cuadrática")
            logger.info("   (Las soluciones se penalizan por deviarse del óptimo, pero siguen siendo válidas si cumplen min/max)")
        else:
            logger.info("✓ RB Sin cobertura óptima definida (solo se aplican min/max como restricciones duras)")

        for t in range(self.num_turnos):
            tot = [sum(self.shifts[(e, d, t)] for d in range(self.num_dias)) for e in range(self.num_enfermeras)]
            if tot:
                mx = self.model.NewIntVar(0, self.num_dias, f"mx_t{t}")
                mn = self.model.NewIntVar(0, self.num_dias, f"mn_t{t}")
                self.model.AddMaxEquality(mx, tot)
                self.model.AddMinEquality(mn, tot)
                diff = self.model.NewIntVar(0, self.num_dias, f"df_t{t}")
                self.model.Add(diff == mx - mn)
                penal.append(diff * 0.1)  # Reduced weight to 0.1 from 100
        logger.info(f"✓ RB Equidad aplicada")

        if 'RB016' in id_map and self.extra_off_days:
            rb016 = id_map['RB016']
            penal_finde = []
            peso = rb016.get('peso', 85)
            fecha_inicio = self.configuracion.fecha_inicio
            
            for e in range(self.num_enfermeras):
                for d in range(self.num_dias):
                    dia_semana = (fecha_inicio + timedelta(days=d)).weekday()
                    if dia_semana < 5:
                        penal_finde.append(self.extra_off_days[(e, d)])
            
            if penal_finde:
                penal.append(sum(penal_finde) * peso)
                logger.info(f"✓ RB016: Penalización de {peso} por día libre extra fuera de fin de semana")

        if penal:
            self.model.Minimize(sum(penal))

    def resolver(self):
        try:
            self.crear_variables()
            self.aplicar_restricciones_duras()
            self.aplicar_restricciones_blandas()

            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = self.configuracion.tiempo_maximo_segundos
            solver.parameters.num_search_workers = self.configuracion.num_trabajadores
            if self.configuracion.seed:
                solver.parameters.random_seed = self.configuracion.seed

            logger.info(f"Resolve: {self.configuracion.tiempo_maximo_segundos}s | workers={self.configuracion.num_trabajadores}")
            st = solver.Solve(self.model)
            logger.info(f"Estado: {solver.StatusName(st)} | Time: {solver.WallTime():.3f}s | Conflicts: {solver.NumConflicts()} | Branches: {solver.NumBranches()}")

            if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                res = self._resultado(solver, st)
                val = ValidadorRestricciones(self.configuracion, res).validar()
                res['validacion'] = val
                return res
            return {'success': False, 'status': solver.StatusName(st), 'mensaje': 'Sin solución factible'}
        except Exception as ex:
            logger.exception(f"Error: {ex}")
            return {'success': False, 'error': str(ex)}

    def _resultado(self, solver, st):
        asign = []
        fi = self.configuracion.fecha_inicio
        for d in range(self.num_dias):
            fecha = fi + timedelta(days=d)
            for e in range(self.num_enfermeras):
                for t in range(self.num_turnos):
                    if solver.BooleanValue(self.shifts[(e, d, t)]):
                        asign.append({
                            'enfermera_id': self.enfermeras[e].id,
                            'enfermera_nombre': self.enfermeras[e].nombre,
                            'fecha': fecha.isoformat(),
                            'turno_id': self.turnos[t].id,
                            'turno_nombre': self.turnos[t].nombre,
                            'es_dia_libre': False
                        })
        logger.info(f"Asignaciones generadas: {len(asign)}")
        logger.info(f"Días cubiertos: {self.num_dias} (desde {fi} hasta {fi + timedelta(days=self.num_dias-1)})")
        logger.info("Resumen por día:")
        for d in range(self.num_dias):
            fecha = fi + timedelta(days=d)
            count = sum(1 for a in asign if a['fecha'] == fecha.isoformat())
            logger.info(f" - {fecha}: {count} asignaciones")
        return {
            'success': True,
            'status': solver.StatusName(st),
            'es_optima': st == cp_model.OPTIMAL,
            'asignaciones': asign,
            'num_asignaciones': len(asign),
            'tiempo_ejecucion': solver.WallTime(),
            'dias_cubiertos': self.num_dias,
            'fecha_inicio': fi.isoformat(),
            'fecha_fin': (fi + timedelta(days=self.num_dias-1)).isoformat()
        }
