# Restricciones de Planificación de Turnos Enfermería SACYL 2025 - Versión Completa

Basado en ORDEN SAN/1462/2024, Decreto-Ley 1/2023 y normativa complementaria.

```json
{
  "metadata": {
    "version": "2025_v3.0_arrays",
    "fecha_actualizacion": "2025-01-01",
    "normativa_base": [
      "ORDEN SAN/1462/2024 (BOCYL-D-13122024-20)",
      "Decreto-Ley 1/2023, de 30 de marzo",
      "Ley 55/2003 Estatuto Marco"
    ],
    "alcance": "Enfermeras SACYL Castilla y León"
  },
  
  "restricciones_duras": [
    {
      "id": "RD001",
      "nombre": "jornada_anual_turno_diurno_sin_guardias",
      "tipo": "jornada_anual",
      "obligatorio": true,
      "parametros": {
        "horas_anuales": 1533,
        "promedio_semanal": 35,
        "promedio_diario": 7
      },
      "descripcion": "Jornada anual para turno diurno sin jornada complementaria",
      "formula": "suma_horas_trabajadas[enfermera] == 1533",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD002",
      "nombre": "jornada_anual_turno_diurno_con_guardias",
      "tipo": "jornada_anual",
      "obligatorio": true,
      "parametros": {
        "tabla_ponderacion": {
          "1": 1529, "2": 1526, "3": 1523, "4": 1520, "5": 1516,
          "6": 1513, "7": 1510, "8": 1507, "9": 1503, "10": 1500,
          "11": 1497, "12": 1494, "13": 1491, "14": 1487, "15": 1484,
          "16": 1481, "17": 1478, "18": 1474, "19": 1471, "20": 1468,
          "21": 1465, "22": 1461, "23": 1458, "24": 1455, "25": 1452,
          "26": 1449, "27": 1445, "28": 1442, "29": 1439, "30": 1436,
          "31": 1432, "32": 1429, "33": 1426, "34": 1423, "35": 1420
        },
        "minimo_absoluto": 1420,
        "reduccion_por_guardia": 3
      },
      "descripcion": "Jornada reducida según número de guardias nocturnas realizadas",
      "formula": "suma_horas[e] == 1533 - (num_guardias[e] * 3)",
      "condiciones": ["guardias NO en víspera festivo", "guardias NO en víspera descanso"],
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD003",
      "nombre": "jornada_anual_turno_rotatorio",
      "tipo": "jornada_anual",
      "obligatorio": true,
      "parametros": {
        "horas_anuales": 1498,
        "noches_base": 42
      },
      "descripcion": "Turno rotatorio mañana-tarde-noche",
      "formula": "suma_horas[enfermera] == 1498",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD004",
      "nombre": "jornada_anual_turno_nocturno_fijo",
      "tipo": "jornada_anual",
      "obligatorio": true,
      "parametros": {
        "horas_anuales": 1420,
        "noches_anuales": 142
      },
      "descripcion": "Turno permanente de noche",
      "formula": "suma_horas[enfermera] == 1420",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD005",
      "nombre": "jornada_anual_personal_area_atencion_primaria",
      "tipo": "jornada_anual",
      "obligatorio": true,
      "parametros": {
        "horas_anuales": 1540,
        "horas_mensuales_promedio": 140,
        "incluye_vacaciones": 165,
        "incluye_asuntos_particulares": 45
      },
      "descripcion": "Jornada específica personal de área en Atención Primaria",
      "formula": "suma_horas[enfermera] == 1540",
      "aplica_a": ["enfermero_area_AP"],
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD006",
      "nombre": "descanso_minimo_entre_jornadas_12h",
      "tipo": "descanso",
      "obligatorio": true,
      "parametros": {
        "minimo_horas": 12,
        "caracter": "ininterrumpido"
      },
      "descripcion": "Descanso mínimo 12 horas entre fin de jornada y comienzo siguiente",
      "formula": "fin_turno[e][d] + 12 <= inicio_turno[e][d+1]",
      "excepciones": ["cambio_equipo_turnos", "emergencia_asistencial_justificada"],
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD007",
      "nombre": "descanso_semanal_36h",
      "tipo": "descanso",
      "obligatorio": true,
      "parametros": {
        "minimo_horas": 36,
        "composicion": "24h + 12h",
        "caracter": "ininterrumpido",
        "periodo_referencia_dias": 14
      },
      "descripcion": "Descanso semanal de 36 horas consecutivas (24h semanales + 12h diarias)",
      "formula": "existe_periodo_36h_consecutivas[e][periodo_14_dias]",
      "alternativa": {
        "horas": 72,
        "periodo_dias": 14,
        "condicion": "cuando no se pueda dar 36h semanales"
      },
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD008",
      "nombre": "descanso_intra_jornada_20min",
      "tipo": "descanso",
      "obligatorio": true,
      "parametros": {
        "duracion_minutos": 20,
        "computa_como": "trabajo_efectivo",
        "plantilla_minima_presente": 0.5
      },
      "descripcion": "Descanso de 20 minutos durante jornada con al menos 50% plantilla presente",
      "formula": "descanso_20min[e][d] AND suma(presentes[d][momento]) >= 0.5 * total_plantilla",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD009",
      "nombre": "jornada_maxima_ordinaria_12h",
      "tipo": "jornada_maxima",
      "obligatorio": true,
      "parametros": {
        "maxima_horas": 12,
        "caracter": "ininterrumpida"
      },
      "descripcion": "Jornada ordinaria máxima de 12 horas ininterrumpidas",
      "formula": "duracion_turno[e][d] <= 12",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD010",
      "nombre": "jornada_excepcional_24h",
      "tipo": "jornada_maxima",
      "obligatorio": true,
      "parametros": {
        "maxima_horas": 24,
        "descanso_posterior": 12,
        "requiere_autorizacion": true
      },
      "descripcion": "Jornada excepcional máxima de 24h solo con autorización y descanso posterior",
      "formula": "IF duracion_turno[e][d] == 24 THEN descanso_posterior[e][d] >= 12",
      "condiciones": ["autorizacion_gerencia", "emergencia_asistencial", "personal_area"],
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD011",
      "nombre": "jornada_conjunta_maxima_48h_semanal",
      "tipo": "jornada_maxima",
      "obligatorio": true,
      "parametros": {
        "horas_semanales": 48,
        "tipo_promedio": "semestral",
        "incluye": ["ordinaria", "complementaria"],
        "excluye": ["localizacion_sin_llamada"]
      },
      "descripcion": "Jornada conjunta máxima de 48h semanales en promedio semestral",
      "formula": "suma(horas_ordinarias[e][semestre] + horas_complementarias[e][semestre]) / 26 <= 48",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD012",
      "nombre": "guardias_no_vispera_festivo",
      "tipo": "guardia",
      "obligatorio": true,
      "parametros": {
        "tipos_afectados": ["presencia_fisica", "alerta_localizada"]
      },
      "descripcion": "Las guardias NO se pueden realizar en víspera de festivo",
      "formula": "guardia[e][d] => NOT festivo[d+1]",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD013",
      "nombre": "guardias_no_vispera_descanso",
      "tipo": "guardia",
      "obligatorio": true,
      "parametros": {
        "tipos_afectados": ["presencia_fisica", "alerta_localizada"]
      },
      "descripcion": "Las guardias NO se pueden realizar en víspera de día de descanso programado",
      "formula": "guardia[e][d] => NOT descanso[e][d+1]",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD014",
      "nombre": "horario_turno_manana",
      "tipo": "horario",
      "obligatorio": true,
      "parametros": {
        "inicio": "08:00",
        "fin": "15:00",
        "duracion": 7
      },
      "descripcion": "Horario fijo turno de mañana",
      "formula": "turno[e][d] == 'mañana' => hora_inicio[e][d] == 8 AND hora_fin[e][d] == 15",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD015",
      "nombre": "horario_turno_tarde",
      "tipo": "horario",
      "obligatorio": true,
      "parametros": {
        "inicio": "15:00",
        "fin": "22:00",
        "duracion": 7
      },
      "descripcion": "Horario fijo turno de tarde",
      "formula": "turno[e][d] == 'tarde' => hora_inicio[e][d] == 15 AND hora_fin[e][d] == 22",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD016",
      "nombre": "horario_turno_noche",
      "tipo": "horario",
      "obligatorio": true,
      "parametros": {
        "inicio": "22:00",
        "fin": "08:00",
        "duracion": 10
      },
      "descripcion": "Horario fijo turno de noche",
      "formula": "turno[e][d] == 'noche' => hora_inicio[e][d] == 22 AND hora_fin[e][d] == 8",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD017",
      "nombre": "vacaciones_anuales_22_dias",
      "tipo": "vacaciones_permisos",
      "obligatorio": true,
      "parametros": {
        "dias": 22,
        "horas_dia": 7,
        "total_horas": 154
      },
      "descripcion": "Mínimo 22 días de vacaciones anuales",
      "formula": "suma(dias_vacaciones[e]) >= 22",
      "periodo": "año_natural",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD018",
      "nombre": "asuntos_particulares_6_dias",
      "tipo": "vacaciones_permisos",
      "obligatorio": true,
      "parametros": {
        "dias": 6,
        "horas_dia": 7,
        "total_horas": 42
      },
      "descripcion": "Mínimo 6 días de asuntos particulares anuales",
      "formula": "suma(dias_asuntos_particulares[e]) >= 6",
      "periodo": "año_natural",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD019",
      "nombre": "cobertura_minima_por_turno",
      "tipo": "cobertura",
      "obligatorio": true,
      "parametros": {
        "minimo_por_turno": "variable_segun_servicio",
        "factor_ajuste": 1.0
      },
      "descripcion": "Cobertura mínima de personal por turno según necesidades servicio",
      "formula": "suma(asignadas[turno][d]) >= cobertura_minima[turno][d]",
      "penalizacion_violacion": "INFINITO"
    },
    {
      "id": "RD020",
      "nombre": "no_solapamiento_turnos_misma_enfermera",
      "tipo": "asignacion",
      "obligatorio": true,
      "parametros": {},
      "descripcion": "Una enfermera no puede estar asignada a dos turnos simultáneamente",
      "formula": "suma(turnos[e][d]) <= 1",
      "penalizacion_violacion": "INFINITO"
    }
  ],
  
  "restricciones_blandas": [
    {
      "id": "RB001",
      "nombre": "distribucion_equitativa_festivos",
      "tipo": "equidad",
      "peso": 100,
      "parametros": {
        "desviacion_maxima_aceptable": 2,
        "periodo": "anual"
      },
      "descripcion": "Distribución equitativa de festivos trabajados entre todo el personal",
      "formula": "minimizar(max(festivos[e]) - min(festivos[e]))",
      "objetivo": "equidad"
    },
    {
      "id": "RB002",
      "nombre": "distribucion_equitativa_domingos",
      "tipo": "equidad",
      "peso": 90,
      "parametros": {
        "desviacion_maxima_aceptable": 2,
        "periodo": "anual"
      },
      "descripcion": "Distribución equitativa de domingos trabajados",
      "formula": "minimizar(max(domingos[e]) - min(domingos[e]))",
      "objetivo": "equidad"
    },
    {
      "id": "RB003",
      "nombre": "distribucion_equitativa_noches",
      "tipo": "equidad",
      "peso": 85,
      "parametros": {
        "referencia_turno_rotatorio": 42,
        "desviacion_maxima_aceptable": 5
      },
      "descripcion": "Distribución equitativa de turnos de noche en turno rotatorio",
      "formula": "minimizar(max(noches[e]) - min(noches[e]))",
      "objetivo": "equidad"
    },
    {
      "id": "RB004",
      "nombre": "fin_semana_completo_mensual",
      "tipo": "conciliacion",
      "peso": 80,
      "parametros": {
        "minimo_mensual": 1,
        "incluye": ["sabado_completo", "domingo_completo"]
      },
      "descripcion": "Garantizar al menos 1 fin de semana completo libre por mes",
      "formula": "suma(findes_libres[e][mes]) >= 1",
      "objetivo": "conciliacion_vida_familiar",
      "aplica_preferentemente": ["personal_area_AP"]
    },
    {
      "id": "RB005",
      "nombre": "evitar_cambios_turno_consecutivos",
      "tipo": "fatiga",
      "peso": 70,
      "parametros": {
        "penalizacion_cambio": 10,
        "especialmente": ["noche_manana", "tarde_manana"]
      },
      "descripcion": "Minimizar cambios bruscos de turno entre días consecutivos",
      "formula": "minimizar(suma(cambios_turno[e][d]))",
      "objetivo": "reducir_fatiga"
    },
    {
      "id": "RB006",
      "nombre": "rotacion_minima_turnicidad",
      "tipo": "organizacion",
      "peso": 60,
      "parametros": {
        "modulos_semanales_noche_mes": 1,
        "aplica_turno": "rotatorio"
      },
      "descripcion": "Rotación mínima de un módulo semanal en noche por mes para turno rotatorio",
      "formula": "suma(semanas_noche[e][mes]) >= 1",
      "objetivo": "turnicidad_adecuada"
    },
    {
      "id": "RB007",
      "nombre": "preferencias_personales_turnos",
      "tipo": "preferencias",
      "peso": 50,
      "parametros": {
        "max_preferencias_por_enfermera": 10,
        "periodo": "mensual"
      },
      "descripcion": "Considerar preferencias personales de turnos cuando sea posible",
      "formula": "maximizar(suma(preferencias_satisfechas[e]))",
      "objetivo": "satisfaccion_personal",
      "input": "matriz_preferencias[enfermera][dia]"
    },
    {
      "id": "RB008",
      "nombre": "dias_consecutivos_mismo_turno",
      "tipo": "organizacion",
      "peso": 55,
      "parametros": {
        "minimo_dias": 2,
        "maximo_dias": 5,
        "excepto_noche": 3
      },
      "descripcion": "Favorecer secuencias de 2-5 días consecutivos con mismo turno",
      "formula": "minimizar(cambios_turno_innecesarios[e])",
      "objetivo": "estabilidad_horaria"
    },
    {
      "id": "RB009",
      "nombre": "distribucion_guardias_mes",
      "tipo": "organizacion",
      "peso": 65,
      "parametros": {
        "distribucion_ideal": "uniforme",
        "max_guardias_semana": 2
      },
      "descripcion": "Distribución uniforme de guardias a lo largo del mes",
      "formula": "minimizar(varianza(guardias_por_semana[e]))",
      "objetivo": "carga_trabajo_equilibrada"
    },
    {
      "id": "RB010",
      "nombre": "anticipacion_planificacion",
      "tipo": "organizacion",
      "peso": 40,
      "parametros": {
        "meses_anticipacion": 6
      },
      "descripcion": "Planificación con al menos 6 meses de anticipación",
      "formula": "calendario_aprobado[mes] <= mes - 6",
      "objetivo": "previsibilidad"
    },
    {
      "id": "RB011",
      "nombre": "cobertura_descanso_20min_rotativo",
      "tipo": "organizacion",
      "peso": 45,
      "parametros": {
        "plantilla_minima_presente": 0.5,
        "organizacion": "rotativa"
      },
      "descripcion": "Organizar descansos de 20 min de forma rotativa manteniendo 50% plantilla",
      "formula": "rotacion_descansos[turno][d] AND presencia[d] >= 0.5",
      "objetivo": "servicio_adecuado"
    },
    {
      "id": "RB012",
      "nombre": "limite_horas_complementarias_voluntarias",
      "tipo": "jornada_especial",
      "peso": 75,
      "parametros": {
        "limite_anual": 150,
        "voluntariedad": true
      },
      "descripcion": "Limitar jornada complementaria voluntaria a 150h anuales",
      "formula": "suma(horas_complementarias_voluntarias[e]) <= 150",
      "objetivo": "proteccion_trabajador"
    },
    {
      "id": "RB013",
      "nombre": "descanso_post_24h_trabajo",
      "tipo": "descanso",
      "peso": 95,
      "parametros": {
        "descanso_minimo": 12,
        "aplica_tras": "jornada_24h"
      },
      "descripcion": "Garantizar descanso adecuado tras jornadas de 24h",
      "formula": "IF duracion[e][d] == 24 THEN descanso[e][d+1] >= 12",
      "objetivo": "recuperacion_fatiga"
    },
    {
      "id": "RB014",
      "nombre": "evitar_noches_aisladas",
      "tipo": "organizacion",
      "peso": 50,
      "parametros": {
        "minimo_noches_consecutivas": 2,
        "maximo_noches_consecutivas": 4
      },
      "descripcion": "Agrupar turnos de noche en secuencias de 2-4 días",
      "formula": "IF noche[e][d] THEN suma(noche[e][d-1:d+1]) >= 2",
      "objetivo": "adaptacion_ritmo_circadiano"
    },
    {
      "id": "RB015",
      "nombre": "vacaciones_periodo_estival_preferente",
      "tipo": "conciliacion",
      "peso": 60,
      "parametros": {
        "periodo": ["julio", "agosto"],
        "minimo_dias": 15
      },
      "descripcion": "Facilitar disfrute de vacaciones en periodo estival",
      "formula": "suma(vacaciones[e][julio:agosto]) >= 15",
      "objetivo": "conciliacion_familiar"
    }
  ],

  "configuracion_ortools": {
    "solver": "CP-SAT",
    "parametros": {
      "num_search_workers": 8,
      "max_time_in_seconds": 300,
      "log_search_progress": true
    },
    "estrategia_busqueda": {
      "prioridad_variables": [
        "asignacion_turnos",
        "contador_guardias",
        "dias_descanso"
      ],
      "heuristica": "CHOOSE_FIRST"
    },
    "funcion_objetivo": {
      "tipo": "minimizacion",
      "formula": "suma(peso[restriccion_blanda] * violacion[restriccion_blanda])"
    }
  },

  "validaciones": {
    "checks_diarios": [
      "RD019_cobertura_minima",
      "RD020_no_solapamiento",
      "RD006_descanso_12h"
    ],
    "checks_semanales": [
      "RD007_descanso_36h",
      "RD011_max_48h"
    ],
    "checks_mensuales": [
      "RB004_fin_semana_mensual",
      "RB009_distribucion_guardias"
    ],
    "checks_anuales": [
      "RD001_RD005_jornada_anual",
      "RD017_vacaciones",
      "RD018_asuntos_particulares"
    ]
  }
}
```