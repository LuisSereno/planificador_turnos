# -*- coding: utf-8 -*-
"""Módulo para aplicar patrones de turnos personalizados."""
import logging

logger = logging.getLogger(__name__)


class AplicadorPatronesPersonalizados:
    """Maneja la aplicación de patrones de turnos (descanso post-turno, secuencias, etc.)."""

    def __init__(self, modelo, turnos_map, turnos, num_enfermeras, num_dias, shifts, offdays, configuracion):
        self.model = modelo
        self.turnos_map = turnos_map
        self.turnos = turnos
        self.num_enfermeras = num_enfermeras
        self.num_dias = num_dias
        self.shifts = shifts
        self.offdays = offdays
        self.configuracion = configuracion
        self.patrones_penalties = []

    def aplicar_todos(self):
        """Aplica todos los patrones configurados."""
        patrones_data = self.configuracion.get_patrones_combinados()

        if not patrones_data:
            logger.info("📋 No hay patrones de turnos configurados")
            return

        logger.info(f"📋 Aplicando {len(patrones_data)} patrones de turnos")

        for p_data in patrones_data:
            try:
                tipo = p_data.get('tipo')
                nombre = p_data.get('nombre', f'Patrón {tipo}')
                config = p_data.get('configuracion', {})
                es_dura = p_data.get('es_restriccion_dura', True)
                peso = p_data.get('peso_penalizacion', 100)

                logger.info(
                    f"  → Procesando patrón: {nombre} ({tipo}) - {'DURA' if es_dura else f'BLANDA (peso {peso})'}")

                if tipo == 'DESCANSO_POST_TURNO':
                    self._aplicar_patron_descanso_post_turno(config, es_dura, peso, nombre)
                elif tipo == 'SECUENCIA_TURNOS':
                    self._aplicar_patron_secuencia_turnos(config, es_dura, peso, nombre)
                elif tipo == 'DISTRIBUCION_EQUITATIVA':
                    self._aplicar_patron_distribucion_equitativa(config, es_dura, peso, nombre)
                elif tipo == 'ROTACION_TURNOS':
                    self._aplicar_patron_rotacion_turnos(config, es_dura, peso, nombre)
                elif tipo == 'MAX_CONSECUTIVOS':
                    self._aplicar_patron_max_consecutivos(config, es_dura, peso, nombre)
                else:
                    logger.warning(f"  ⚠️ Tipo de patrón desconocido: {tipo}")

            except Exception as e:
                logger.error(f"  ❌ Error aplicando patrón {p_data.get('nombre', 'sin nombre')}: {str(e)}")

    def _aplicar_patron_descanso_post_turno(self, config, es_dura, peso, nombre):
        """Patrón: N turnos consecutivos → M días de descanso."""
        turno_tipo = config.get('turno_tipo')
        cantidad_consecutiva = config.get('cantidad_consecutiva', 2)
        dias_descanso_requeridos = config.get('dias_descanso_requeridos', 3)

        if not turno_tipo:
            logger.warning(f"  ⚠️ Patrón {nombre}: falta turno_tipo")
            return

        idx_turno = self.turnos_map.get(turno_tipo)
        if idx_turno is None:
            logger.warning(f"  ⚠️ Patrón {nombre}: turno '{turno_tipo}' no encontrado")
            return

        restricciones_aplicadas = 0

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias - cantidad_consecutiva - dias_descanso_requeridos + 1):
                turnos_consecutivos = [self.shifts[e, d + offset, idx_turno] for offset in range(cantidad_consecutiva)]
                turnos_activos = self.model.NewBoolVar(f'patron_{nombre}_e{e}_d{d}')
                self.model.AddMinEquality(turnos_activos, turnos_consecutivos)

                for offset_descanso in range(cantidad_consecutiva, cantidad_consecutiva + dias_descanso_requeridos):
                    dia_descanso = d + offset_descanso
                    if dia_descanso < self.num_dias:
                        if es_dura:
                            self.model.AddImplication(turnos_activos, self.offdays[e, dia_descanso])
                        else:
                            violacion = self.model.NewBoolVar(f'violacion_{nombre}_e{e}_d{dia_descanso}')
                            self.model.AddBoolOr([turnos_activos.Not(), self.offdays[e, dia_descanso]]).OnlyEnforceIf(
                                violacion.Not())
                            self.model.AddBoolAnd([turnos_activos, self.offdays[e, dia_descanso].Not()]).OnlyEnforceIf(
                                violacion)
                            self.patrones_penalties.append((violacion, peso, f'{nombre}_e{e}_d{dia_descanso}'))

                        restricciones_aplicadas += 1

        logger.info(
            f"    ✓ Aplicado: {cantidad_consecutiva} {turno_tipo} → {dias_descanso_requeridos} días descanso ({restricciones_aplicadas} restricciones)")

    def _aplicar_patron_secuencia_turnos(self, config, es_dura, peso, nombre):
        """Patrón: Secuencia obligatoria de turnos."""
        secuencia = config.get('secuencia', [])

        if not secuencia or len(secuencia) < 2:
            logger.warning(f"  ⚠️ Patrón {nombre}: secuencia inválida")
            return

        indices_secuencia = []
        for turno_nombre in secuencia:
            idx = self.turnos_map.get(turno_nombre)
            if idx is None:
                logger.warning(f"  ⚠️ Patrón {nombre}: turno '{turno_nombre}' no encontrado")
                return
            indices_secuencia.append(idx)

        restricciones_aplicadas = 0
        longitud_secuencia = len(indices_secuencia)

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias - longitud_secuencia + 1):
                for idx_seq in range(longitud_secuencia):
                    dia_actual = d + idx_seq
                    turno_esperado = indices_secuencia[idx_seq]

                    if es_dura:
                        if idx_seq == 0:
                            inicio_secuencia = self.shifts[e, dia_actual, turno_esperado]
                        else:
                            self.model.AddImplication(inicio_secuencia, self.shifts[e, dia_actual, turno_esperado])
                    else:
                        violacion = self.model.NewBoolVar(f'violacion_{nombre}_e{e}_d{dia_actual}_seq{idx_seq}')
                        if idx_seq == 0:
                            inicio_secuencia = self.shifts[e, dia_actual, turno_esperado]
                            self.model.Add(violacion == 0)
                        else:
                            self.model.AddBoolOr(
                                [inicio_secuencia.Not(), self.shifts[e, dia_actual, turno_esperado]]).OnlyEnforceIf(
                                violacion.Not())
                            self.model.AddBoolAnd(
                                [inicio_secuencia, self.shifts[e, dia_actual, turno_esperado].Not()]).OnlyEnforceIf(
                                violacion)
                            self.patrones_penalties.append((violacion, peso, f'{nombre}_e{e}_d{dia_actual}'))

                    restricciones_aplicadas += 1

        logger.info(f"    ✓ Aplicado: Secuencia {' → '.join(secuencia)} ({restricciones_aplicadas} restricciones)")

    def _aplicar_patron_distribucion_equitativa(self, config, es_dura, peso, nombre):
        """Patrón: Distribución equitativa de un tipo de turno."""
        turno_tipo = config.get('turno_tipo')
        tolerancia = config.get('tolerancia', 2)

        if not turno_tipo:
            logger.warning(f"  ⚠️ Patrón {nombre}: falta turno_tipo")
            return

        idx_turno = self.turnos_map.get(turno_tipo)
        if idx_turno is None:
            logger.warning(f"  ⚠️ Patrón {nombre}: turno '{turno_tipo}' no encontrado")
            return

        contadores = []
        for e in range(self.num_enfermeras):
            contador = self.model.NewIntVar(0, self.num_dias, f'contador_{turno_tipo}_e{e}')
            self.model.Add(contador == sum([self.shifts[e, d, idx_turno] for d in range(self.num_dias)]))
            contadores.append(contador)

        restricciones_aplicadas = 0
        for e1 in range(self.num_enfermeras):
            for e2 in range(e1 + 1, self.num_enfermeras):
                diferencia = self.model.NewIntVar(-self.num_dias, self.num_dias, f'diff_{nombre}_e{e1}_e{e2}')
                self.model.Add(diferencia == contadores[e1] - contadores[e2])

                if es_dura:
                    self.model.Add(diferencia <= tolerancia)
                    self.model.Add(diferencia >= -tolerancia)
                else:
                    violacion_positiva = self.model.NewBoolVar(f'violacion_pos_{nombre}_e{e1}_e{e2}')
                    violacion_negativa = self.model.NewBoolVar(f'violacion_neg_{nombre}_e{e1}_e{e2}')

                    self.model.Add(diferencia > tolerancia).OnlyEnforceIf(violacion_positiva)
                    self.model.Add(diferencia <= tolerancia).OnlyEnforceIf(violacion_positiva.Not())

                    self.model.Add(diferencia < -tolerancia).OnlyEnforceIf(violacion_negativa)
                    self.model.Add(diferencia >= -tolerancia).OnlyEnforceIf(violacion_negativa.Not())

                    self.patrones_penalties.append((violacion_positiva, peso, f'{nombre}_pos_e{e1}_e{e2}'))
                    self.patrones_penalties.append((violacion_negativa, peso, f'{nombre}_neg_e{e1}_e{e2}'))

                restricciones_aplicadas += 1

        logger.info(
            f"    ✓ Aplicado: Distribución equitativa de {turno_tipo} (tolerancia={tolerancia}, {restricciones_aplicadas} pares)")

    def _aplicar_patron_rotacion_turnos(self, config, es_dura, peso, nombre):
        """Patrón: Rotación equilibrada entre tipos de turnos."""
        turnos_rotar = config.get('turnos', [])
        ventana_dias = config.get('ventana_dias', 14)

        if not turnos_rotar or len(turnos_rotar) < 2:
            logger.warning(f"  ⚠️ Patrón {nombre}: debe especificar al menos 2 turnos para rotar")
            return

        indices_turnos = []
        for turno_nombre in turnos_rotar:
            idx = self.turnos_map.get(turno_nombre)
            if idx is None:
                logger.warning(f"  ⚠️ Patrón {nombre}: turno '{turno_nombre}' no encontrado")
                return
            indices_turnos.append(idx)

        restricciones_aplicadas = 0

        for e in range(self.num_enfermeras):
            num_ventanas = (self.num_dias // ventana_dias)
            for ventana in range(num_ventanas):
                inicio = ventana * ventana_dias
                fin = min(inicio + ventana_dias, self.num_dias)

                for idx_turno in indices_turnos:
                    turnos_en_ventana = [self.shifts[e, d, idx_turno] for d in range(inicio, fin)]

                    if es_dura:
                        self.model.Add(sum(turnos_en_ventana) >= 1)
                    else:
                        tiene_turno = self.model.NewBoolVar(f'tiene_{self.turnos[idx_turno].nombre}_e{e}_v{ventana}')
                        self.model.Add(sum(turnos_en_ventana) >= 1).OnlyEnforceIf(tiene_turno)
                        self.model.Add(sum(turnos_en_ventana) == 0).OnlyEnforceIf(tiene_turno.Not())

                        self.patrones_penalties.append(
                            (tiene_turno.Not(), peso, f'{nombre}_e{e}_v{ventana}_{self.turnos[idx_turno].nombre}'))

                    restricciones_aplicadas += 1

        logger.info(
            f"    ✓ Aplicado: Rotación de {len(indices_turnos)} turnos cada {ventana_dias} días ({restricciones_aplicadas} restricciones)")

    def _aplicar_patron_max_consecutivos(self, config, es_dura, peso, nombre):
        """Patrón: Máximo N turnos consecutivos de un tipo."""
        turno_tipo = config.get('turno_tipo')
        max_consecutivos = config.get('max_consecutivos', 2)

        if not turno_tipo:
            logger.warning(f"  ⚠️ Patrón {nombre}: falta turno_tipo")
            return

        idx_turno = self.turnos_map.get(turno_tipo)
        if idx_turno is None:
            logger.warning(f"  ⚠️ Patrón {nombre}: turno '{turno_tipo}' no encontrado")
            return

        restricciones_aplicadas = 0
        ventana = max_consecutivos + 1

        for e in range(self.num_enfermeras):
            for d in range(self.num_dias - ventana + 1):
                turnos_en_ventana = [self.shifts[e, d + offset, idx_turno] for offset in range(ventana)]

                if es_dura:
                    self.model.Add(sum(turnos_en_ventana) <= max_consecutivos)
                else:
                    violacion = self.model.NewBoolVar(f'violacion_{nombre}_e{e}_d{d}')
                    self.model.Add(sum(turnos_en_ventana) > max_consecutivos).OnlyEnforceIf(violacion)
                    self.model.Add(sum(turnos_en_ventana) <= max_consecutivos).OnlyEnforceIf(violacion.Not())
                    self.patrones_penalties.append((violacion, peso, f'{nombre}_e{e}_d{d}'))

                restricciones_aplicadas += 1

        logger.info(
            f"    ✓ Aplicado: Máximo {max_consecutivos} turnos consecutivos de {turno_tipo} ({restricciones_aplicadas} restricciones)")
