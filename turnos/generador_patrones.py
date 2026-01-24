# -*- coding: utf-8 -*-
import logging
from ortools.sat.python import cp_model

logger = logging.getLogger(__name__)

class AplicadorPatrones:
    """Aplica patrones de turnos personalizados al modelo CP-SAT"""
    
    def __init__(self, generador):
        self.generador = generador
        self.model = generador.model
        self.shifts = generador.shifts
        self.off_days = generador.off_days
        self.num_dias = generador.num_dias
        self.num_enfermeras = generador.num_enfermeras
        self.num_turnos = generador.num_turnos
        self.turnos = generador.turnos
        self.turnos_map = generador.turnos_map
        
    def aplicar_patrones(self, patrones):
        """Aplica lista de patrones y retorna penalizaciones blandas"""
        if not patrones:
            logger.info("📋 No hay patrones de turnos para aplicar")
            return []
        
        logger.info(f"Aplicando {len(patrones)} patrones de turnos...")
        penalizaciones = []
        
        for patron in patrones:
            try:
                if not patron.activo:
                    logger.debug(f"⏭️  Patrón '{patron.nombre}' desactivado")
                    continue
                
                tipo = patron.tipo
                es_dura = patron.es_restriccion_dura
                config = patron.configuracion or {}
                
                logger.info(f"📌 {patron.nombre} [{tipo}] - {'DURA' if es_dura else f'BLANDA (Peso: {patron.peso_penalizacion})'}")
                
                if tipo == 'DESCANSO_POST_TURNO':
                    penalties = self._aplicar_descanso_post_turno(patron, config, es_dura)
                    if penalties:
                        penalizaciones.extend(penalties)
                        
                elif tipo == 'MAX_CONSECUTIVOS':
                    penalties = self._aplicar_max_consecutivos(patron, config, es_dura)
                    if penalties:
                        penalizaciones.extend(penalties)
                        
                elif tipo == 'ROTACION':
                    penalties = self._aplicar_rotacion(patron, config, es_dura)
                    if penalties:
                        penalizaciones.extend(penalties)
                        
                else:
                    logger.warning(f"⚠️  Tipo de patrón no implementado: {tipo}")
                    
            except Exception as e:
                logger.error(f"❌ Error aplicando patrón '{patron.nombre}': {e}")
        
        logger.info(f"✅ Patrones aplicados. Penalizaciones blandas: {len(penalizaciones)}")
        return penalizaciones
    
    def _aplicar_descanso_post_turno(self, patron, config, es_dura):
        """
        Aplica patrón: Después de N turnos consecutivos de un tipo,
        se requieren M días de descanso.
        
        Config esperado:
        {
            "turno_tipo": "NOCHE",
            "cantidad_consecutiva": 2,
            "dias_descanso_requeridos": 3
        }
        """
        try:
            turno_tipo = config.get('turno_tipo', 'NOCHE')
            cantidad_consecutiva = int(config.get('cantidad_consecutiva', 2))
            dias_descanso = int(config.get('dias_descanso_requeridos', 3))
            
            logger.info(f"   └─ Config: turno_tipo={turno_tipo}, cantidad_consecutiva={cantidad_consecutiva}, dias_descanso_requeridos={dias_descanso}")
            
            # Obtener índice del turno
            idx_turno = self.turnos_map.get(turno_tipo)
            if idx_turno is None:
                logger.error(f"   └─ ❌ Turno '{turno_tipo}' no encontrado en configuración")
                return []
            
            penalizaciones = []
            restricciones_aplicadas = 0
            
            # Para cada enfermera y cada ventana de días
            for e in range(self.num_enfermeras):
                for d_inicio in range(self.num_dias - cantidad_consecutiva - dias_descanso + 1):
                    # Verificar si hay 'cantidad_consecutiva' turnos del tipo especificado
                    # Usamos variables auxiliares para detectar secuencias
                    turnos_consecutivos = []
                    
                    for offset in range(cantidad_consecutiva):
                        d = d_inicio + offset
                        if d < self.num_dias:
                            turnos_consecutivos.append(self.shifts[(e, d, idx_turno)])
                    
                    # Si hay exactamente 'cantidad_consecutiva' turnos consecutivos del tipo,
                    # entonces los siguientes 'dias_descanso' deben ser libres
                    
                    if len(turnos_consecutivos) == cantidad_consecutiva:
                        # Variable auxiliar: ¿hay secuencia completa?
                        secuencia_var = self.model.NewBoolVar(
                            f'secuencia_e{e}_d{d_inicio}_{turno_tipo}'
                        )
                        
                        # secuencia_var = 1 si todos los turnos consecutivos están activos
                        self.model.AddBoolAnd(turnos_consecutivos).OnlyEnforceIf(secuencia_var)
                        self.model.AddBoolOr([t.Not() for t in turnos_consecutivos]).OnlyEnforceIf(secuencia_var.Not())
                        
                        # Si secuencia_var = 1, entonces los siguientes días deben ser libres
                        for offset_desc in range(1, dias_descanso + 1):
                            d_descanso = d_inicio + cantidad_consecutiva - 1 + offset_desc
                            
                            if d_descanso < self.num_dias:
                                if es_dura:
                                    # Restricción DURA: si hay secuencia, ese día DEBE ser libre
                                    self.model.AddImplication(
                                        secuencia_var,
                                        self.off_days[(e, d_descanso)]
                                    )
                                    restricciones_aplicadas += 1
                                else:
                                    # Restricción BLANDA: penalizar si NO es día libre
                                    violation_var = self.model.NewBoolVar(
                                        f'violation_e{e}_d{d_descanso}_{turno_tipo}'
                                    )
                                    
                                    # violation_var = secuencia_var AND NOT off_days
                                    self.model.AddBoolAnd([
                                        secuencia_var,
                                        self.off_days[(e, d_descanso)].Not()
                                    ]).OnlyEnforceIf(violation_var)
                                    
                                    self.model.AddBoolOr([
                                        secuencia_var.Not(),
                                        self.off_days[(e, d_descanso)]
                                    ]).OnlyEnforceIf(violation_var.Not())
                                    
                                    penalizaciones.append((violation_var, patron.peso_penalizacion))
            
            if es_dura:
                logger.info(f"   └─ ✅ {restricciones_aplicadas} restricciones DURAS aplicadas")
            else:
                logger.info(f"   └─ ✅ {len(penalizaciones)} penalizaciones BLANDAS configuradas")
            
            return penalizaciones
            
        except Exception as e:
            logger.error(f"   └─ ❌ Error en _aplicar_descanso_post_turno: {e}")
            return []
    
    def _aplicar_max_consecutivos(self, patron, config, es_dura):
        """
        Aplica patrón: Máximo N turnos consecutivos de un tipo.
        
        Config esperado:
        {
            "turno_tipo": "NOCHE",
            "max_consecutivos": 2
        }
        """
        try:
            turno_tipo = config.get('turno_tipo', 'NOCHE')
            max_consec = int(config.get('max_consecutivos', 2))
            
            logger.info(f"   └─ Config: turno_tipo={turno_tipo}, max_consecutivos={max_consec}")
            
            idx_turno = self.turnos_map.get(turno_tipo)
            if idx_turno is None:
                logger.error(f"   └─ ❌ Turno '{turno_tipo}' no encontrado")
                return []
            
            penalizaciones = []
            restricciones_aplicadas = 0
            
            # Ventana deslizante de tamaño (max_consec + 1)
            window = max_consec + 1
            
            for e in range(self.num_enfermeras):
                for d_inicio in range(self.num_dias - window + 1):
                    turnos_en_ventana = [
                        self.shifts[(e, d_inicio + offset, idx_turno)]
                        for offset in range(window)
                    ]
                    
                    if es_dura:
                        # DURA: no más de max_consec en ventana de (max_consec + 1)
                        self.model.Add(sum(turnos_en_ventana) <= max_consec)
                        restricciones_aplicadas += 1
                    else:
                        # BLANDA: penalizar si excede
                        excess_var = self.model.NewIntVar(
                            0, window,
                            f'excess_e{e}_d{d_inicio}_{turno_tipo}'
                        )
                        self.model.Add(excess_var >= sum(turnos_en_ventana) - max_consec)
                        penalizaciones.append((excess_var, patron.peso_penalizacion))
            
            if es_dura:
                logger.info(f"   └─ ✅ {restricciones_aplicadas} restricciones DURAS aplicadas")
            else:
                logger.info(f"   └─ ✅ {len(penalizaciones)} penalizaciones BLANDAS configuradas")
            
            return penalizaciones
            
        except Exception as e:
            logger.error(f"   └─ ❌ Error en _aplicar_max_consecutivos: {e}")
            return []
    
    def _aplicar_rotacion(self, patron, config, es_dura):
        """
        Aplica patrón de rotación entre turnos.
        
        Config esperado:
        {
            "secuencia": ["MAÑANA", "TARDE", "NOCHE"],
            "dias_por_turno": 3
        }
        """
        logger.warning("⚠️  Patrón ROTACION no implementado completamente")
        return []
