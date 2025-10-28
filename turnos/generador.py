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

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias):
                self.model.Add(sum(self.shifts[(e, d, t)] for t in range(self.num_turnos)) <= 1)
        logger.info("✓ RD020: Una enfermera, un turno por día")

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
                    logger.debug(f"  - {nombre} d{d}: min={req_min} (requerido), optimo={req_optimo} (preferido), max={req_max} (límite)")
                elif isinstance(demanda_value, (int, float)):
                    req_min = int(demanda_value)
                    logger.debug(f"  - {nombre} d{d}: min={req_min} (requerido), max={req_max} (límite)")
                
                personal_asignado = sum(self.shifts[(e, d, t)] for e in range(self.num_enfermeras))
                self.model.Add(personal_asignado >= req_min).OnlyEnforceIf(req_min > 0)
                self.model.Add(personal_asignado <= req_max)


        if idxN is not None and idxM is not None:
            for e in range(self.num_enfermeras):
                for d in range(self.num_dias - 1):
                    self.model.Add(self.shifts[(e, d, idxN)] + self.shifts[(e, d + 1, idxM)] <= 1)
            logger.info("✓ RD006: Descanso 12h (NOCHE->MAÑANA prohibido)")

        if 'RD021' in id_map and idxN is not None:
            for e in range(self.num_enfermeras):
                for d in range(self.num_dias - 1):
                    self.model.AddImplication(self.shifts[(e, d, idxN)], self.off_days[(e, d + 1)])
            logger.info("✓ RD021: Descanso obligatorio post-noche")

        if 'RD022' in id_map and idxN is not None:
            for e in range(self.num_enfermeras):
                noches_trabajadas = sum(self.shifts[(e, d, idxN)] for d in range(self.num_dias - 1))
                dias_libres_totales = sum(self.off_days[(e, d)] for d in range(self.num_dias))
                self.model.Add(dias_libres_totales >= 2 + noches_trabajadas)
            logger.info("✓ RD022: Mínimo 2 días de descanso extra (además de post-noche)")

        dias_libres_requeridos = int((self.num_dias / 365) * 28)
        for e in range(self.num_enfermeras):
            dias_trabajados = sum(self.shifts[(e, d, t)] for d in range(self.num_dias) for t in range(self.num_turnos))
            self.model.Add(dias_trabajados <= self.num_dias - dias_libres_requeridos)
        logger.info(f"✓ RD017+RD018: Mínimo {dias_libres_requeridos} días libres por enfermera")

        for e in range(self.num_enfermeras):
            for semana in range(0, self.num_dias, 7):
                fin_semana = min(semana + 7, self.num_dias)
                turnos_en_semana = sum(self.shifts[(e, d, t)] for d in range(semana, fin_semana) for t in range(self.num_turnos))
                self.model.Add(turnos_en_semana <= (fin_semana - semana) - 1)
        logger.info("✓ RD007: Descanso semanal (mínimo 1 día libre cada 7 días)")

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
                    penal.append(shortfall_sq * 100)  # Penalización cuadrática por estar por debajo
                    penal.append(overage * 20)    # Penalización lineal por estar por encima
                    
                    logger.debug(f"  - {nombre} d{d}: optimo={req_optimo}, penalización por falta (x100 cuadrática) y exceso (x20 lineal)")
        
        if tiene_optimo:
            logger.info("✓ RB Cobertura óptima aplicada con penalización cuadrática")
            logger.info("   (Las soluciones se penalizan por desviarse del óptimo, pero siguen siendo válidas si cumplen min/max)")
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
                penal.append(diff * 100)
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
