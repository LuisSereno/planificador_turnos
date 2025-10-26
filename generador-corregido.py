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
        self._jornada_maxima_12h()
        self._equidad_turnos_resumen()
        logger.info("="*80)
        logger.info(f"VALIDACIONES OK: {len(self.exitos)}  |  VIOLACIONES: {len(self.violaciones)}")
        logger.info("="*80)
        return {'valido': len(self.violaciones) == 0, 'validaciones': self.exitos, 'violaciones': self.violaciones}

    def _una_enfermera_un_turno_por_dia(self):
        seen = set()
        ok = True
        for a in self.resultado.get('asignaciones', []):
            key = (a['enfermera_id'], a['fecha'])
            if key in seen:
                self._ko("RD020", f"Más de un turno en {a['fecha']} para {a['enfermera_nombre']}")
                ok = False
            else:
                seen.add(key)
        if ok:
            self._ok("RD020", f"{len(seen)} asignaciones únicas")

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
            # Extraer el valor correcto de demanda
            demanda_value = demanda.get(turno_nombre, 1)

            # Si es dict (formato complejo), extraer 'optimo'
            if isinstance(demanda_value, dict):
                demanda_minima = demanda_value.get('optimo', demanda_value.get('min', 1))
            else:
                demanda_minima = int(demanda_value) if demanda_value else 1

            if cantidad < demanda_minima:
                detalles = f"Turno {turno_nombre} el {fecha}: {cantidad} personal (requiere {demanda_minima})"
                logger.warning(f"  ✗ {detalles}")
                valido = False
            else:
                logger.debug(f"  ✓ {turno_nombre} {fecha}: {cantidad} personal (requiere {demanda_minima})")

        # FIX: Usar 'self.exitos' no 'self.validaciones_exitosas'
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
                fa = datetime.fromisoformat(a['fecha'])
                fb = datetime.fromisoformat(b['fecha'])
                ha_fin = datetime.combine(fa.date(), ta.hora_fin)
                hb_ini = datetime.combine(fb.date(), tb.hora_inicio)
                if (hb_ini - ha_fin).total_seconds()/3600 < 12:
                    self._ko("RD006", f"{a['enfermera_nombre']} {a['fecha']}->{b['fecha']} < 12h")
                    ok = False
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
        self.demanda = self._demanda()
        self.rd = self._restricciones_duras()
        self.rb = self._restricciones_blandas()

        logger.info("="*80)
        logger.info("INICIO GENERADOR")
        logger.info("="*80)
        logger.info(f"Config: {configuracion.nombre} | Días: {self.num_dias} | Enfs: {self.num_enfermeras} | Turnos: {self.num_turnos}")
        logger.info(f"Demanda: {self.demanda}")

    def _demanda(self):
        """Procesa demanda - soporta formato simple y complejo"""
        demanda = self.configuracion.demanda_por_turno

        logger.info(f"Demanda raw: {demanda} (type: {type(demanda).__name__})")

        # Si está vacío, usar default
        if not demanda:
            logger.warning("Demanda vacía, usando default (1 por turno)")
            return {turno.nombre: 1 for turno in self.turnos}

        # Si es dict
        if isinstance(demanda, dict):
            resultado = {}
            for k, v in demanda.items():
                turno_nombre = str(k)

                # Si v es dict (formato complejo: {"min": 2, "optimo": 3, "max": 5})
                if isinstance(v, dict):
                    logger.info(f"Formato complejo detectado para {turno_nombre}: {v}")

                    # Preferencia: optimo > min > max > primer valor
                    if 'optimo' in v:
                        valor = v['optimo']
                        logger.debug(f"  Usando 'optimo': {valor}")
                    elif 'min' in v:
                        valor = v['min']
                        logger.debug(f"  Usando 'min': {valor}")
                    elif 'max' in v:
                        valor = v['max']
                        logger.debug(f"  Usando 'max': {valor}")
                    else:
                        # Tomar primer valor numérico del dict
                        valores = [x for x in v.values() if isinstance(x, (int, float))]
                        valor = int(valores[0]) if valores else 1
                        logger.debug(f"  Usando primer valor numérico: {valor}")

                    try:
                        resultado[turno_nombre] = int(valor)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"No se pudo convertir {turno_nombre}={valor}. Usando 1.")
                        resultado[turno_nombre] = 1

                # Si v es número directo (formato simple)
                elif isinstance(v, (int, float)):
                    resultado[turno_nombre] = int(v)
                    logger.info(f"Formato simple para {turno_nombre}: {v}")

                # Si es string, intentar convertir
                elif isinstance(v, str):
                    try:
                        resultado[turno_nombre] = int(v)
                    except ValueError:
                        logger.warning(f"No se pudo convertir string {turno_nombre}={v}. Usando 1.")
                        resultado[turno_nombre] = 1

                else:
                    logger.warning(f"Tipo desconocido para demanda[{turno_nombre}]={v} ({type(v).__name__}). Usando 1.")
                    resultado[turno_nombre] = 1

            logger.info(f"✓ Demanda procesada: {resultado}")
            return resultado

        # Si es lista o string, usar default
        logger.warning(f"Formato de demanda no reconocido: {type(demanda).__name__}. Usando default.")
        return {turno.nombre: 1 for turno in self.turnos}

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
        total = self.num_enfermeras * self.num_dias * self.num_turnos
        logger.info(f"Creamos {total} variables booleanas")
        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                for t in range(self.num_turnos):
                    self.shifts[(e, d, t)] = self.model.NewBoolVar(f"e{e}_d{d}_t{t}")

    def aplicar_restricciones_duras(self):
        # RD020: una enfermera, un turno por día
        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                self.model.Add(sum(self.shifts[(e, d, t)] for t in range(self.num_turnos)) <= 1)
        logger.info("RD020 aplicada (una por día)")

        # RD019: cobertura mínima
        for d in range(self.num_dias):
            for t in range(self.num_turnos):
                nombre = self.turnos[t].nombre
                req = self.demanda.get(nombre, 1)
                self.model.Add(sum(self.shifts[(e, d, t)] for e in range(self.num_enfermeras)) >= req)
        logger.info("RD019 aplicada (cobertura mínima)")

        # RD006: descanso 12h
        idxN = None
        idxM = None
        for ti in range(self.num_turnos):
            if self.turnos[ti].nombre == 'NOCHE':
                idxN = ti
            if self.turnos[ti].nombre == 'MANANA':
                idxM = ti
        if idxN is not None and idxM is not None:
            for e in range(self.num_enfermeras):
                for d in range(self.num_dias - 1):
                    self.model.Add(self.shifts[(e, d, idxN)] + self.shifts[(e, d + 1, idxM)] <= 1)
            logger.info("RD006 aplicada (NOCHE->MAÑANA prohibido)")

        logger.info("RD014-16 verificación en validador")

    def aplicar_restricciones_blandas(self):
        penal = []
        # Equidad por turno
        for t in range(self.num_turnos):
            tot = []
            for e in range(self.num_enfermeras):
                tot.append(sum(self.shifts[(e, d, t)] for d in range(self.num_dias)))
            if tot:
                mx = self.model.NewIntVar(0, self.num_dias, f"mx_t{t}")
                mn = self.model.NewIntVar(0, self.num_dias, f"mn_t{t}")
                self.model.AddMaxEquality(mx, tot)
                self.model.AddMinEquality(mn, tot)
                diff = self.model.NewIntVar(0, self.num_dias, f"df_t{t}")
                self.model.Add(diff == mx - mn)
                penal.append(diff * 100)
        if penal:
            self.model.Minimize(sum(penal))
            logger.info(f"RB equidad aplicada con {len(penal)} términos")

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
        logger.info(f"Asignaciones: {len(asign)}")
        # FIX: Incluir todos los campos requeridos
        return {
            'success': True,
            'status': solver.StatusName(st),
            'es_optima': st == cp_model.OPTIMAL,
            'asignaciones': asign,
            'num_asignaciones': len(asign),
            'tiempo_ejecucion': solver.WallTime()
        }
