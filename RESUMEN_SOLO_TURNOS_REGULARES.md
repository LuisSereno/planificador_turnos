# Resumen de Simulación - Solo Turnos Regulares (M/T/N)

## 📋 Información General

**Ejecución**: #68  
**Configuración**: SIM_Planilla Julio 2025  
**Período**: 2025-07-01 a 2025-07-31  
**Total días**: 31  
**Enfermeras**: 10

---

## 📊 Resumen de Turnos Regulares

| Métrica | Valor | Porcentaje |
|---------|-------|------------|
| **Total celdas en planificación** | 310 | 100% |
| **Celdas tipo TURNO con turno real** | 200 | 64.5% |
| **Incidencias excluidas** | 110 | 35.5% |

---

## 🕐 Distribución de Turnos Regulares

| Turno | Código | Asignaciones | Porcentaje |
|-------|--------|--------------|------------|
| **Mañana** | M | 69 | 34.5% |
| **Tarde** | T | 61 | 30.5% |
| **Noche** | N | 70 | 35.0% |
| **Total** | - | 200 | 100% |

---

## ⏰ Horarios de Turnos Regulares

### ☀️ Mañana [M]
- **Horario**: 07:00 - 15:00
- **Duración**: 8.0 horas
- **Es nocturno**: No

### ☀️ Tarde [T]
- **Horario**: 15:00 - 23:00
- **Duración**: 8.0 horas
- **Es nocturno**: No

### 🌙 Noche [N]
- **Horario**: 23:00 - 07:00
- **Duración**: 8.0 horas
- **Es nocturno**: Sí

---

## 👩‍⚕️ Secuencia por Enfermera (Solo Turnos Regulares)

| Enfermera | Secuencia | Total | M | T | N |
|-----------|-----------|-------|---|---|---|
| **Ana Martinez Ruiz** | MTTNNMMTTNMMTNNMMTNN | 20 | 7 | 6 | 7 |
| **Carmen Lopez Diaz** | TNNMMTTNMTTNNMTTNNMM | 20 | 6 | 7 | 7 |
| **Elena Torres Navarro** | MMTNNMTTNNMTTNNMMTTN | 20 | 6 | 7 | 7 |
| **Isabel Rodriguez Moreno** | NNMMTNNMMTTNMMTNNMMT | 20 | 8 | 5 | 7 |
| **Laura Fernandez Sanz** | TTNNMMTTNMMTNNMMTNNM | 20 | 7 | 6 | 7 |
| **Lucia Moreno Blanco** | MMTTNMMTNNMMTNNMMTNN | 20 | 8 | 5 | 7 |
| **Maria Garcia Lopez** | MMTTNMMTNNMMTNNMTTNN | 20 | 7 | 6 | 7 |
| **Marta Ruiz Jimenez** | MMTTNMMTNNMMTNNMTTNN | 20 | 7 | 6 | 7 |
| **Pilar Sanchez Gil** | NMTTNNMMTNNMTTNNMMTT | 20 | 6 | 7 | 7 |
| **Sofia Alvarez Romero** | MTTNNMMTTNMMTNNMMTNN | 20 | 7 | 6 | 7 |
| **TOTALES** | - | **200** | **69** | **61** | **70** |

---

## 🚫 Incidencias Excluidas del Análisis

| Tipo de Incidencia | Celdas |
|--------------------|--------|
| **LIBRE** | 110 |
| **Total excluidas** | 110 |

**Nota**: No se incluyen vacaciones, permisos, bajas, formación ni asignaciones fijas en esta ejecución.

---

## ✅ Resumen Final

| Categoría | Cantidad | Porcentaje |
|-----------|----------|------------|
| **Turnos regulares (M/T/N)** | 200 | 64.5% |
| **Incidencias excluidas** | 110 | 35.5% |
| **Días libres** | 110 | 35.5% |
| **Total celdas** | 310 | 100% |

---

## 📈 Análisis de Equidad

### Distribución de Turnos por Enfermera

| Métrica | Min | Max | Diferencia | Evaluación |
|---------|-----|-----|------------|------------|
| **Total turnos** | 20 | 20 | 0 | ✅ Perfectamente equitativo |
| **Mañanas (M)** | 6 | 8 | 2 | ✅ Equitativo |
| **Tardes (T)** | 5 | 7 | 2 | ✅ Equitativo |
| **Noches (N)** | 7 | 7 | 0 | ✅ Perfectamente equitativo |

**Conclusión**: La distribución de turnos es **altamente equitativa**. Todas las enfermeras tienen exactamente 20 turnos regulares, con una variación mínima de ±1 turno por tipo.

---

## 🎯 Observaciones Importantes

### 1. Solo Turnos Regulares
Este análisis muestra **únicamente** las celdas de tipo `TURNO` con turnos reales asignados (Mañana, Tarde, Noche). Se han excluido:
- Días libres (LIBRE)
- Vacaciones (VACACIONES)
- Permisos (PERMISO)
- Bajas (BAJA)
- Formación (FORMACION)
- Asignaciones fijas (ASIGNACION_FIJA)

### 2. Interpretación de Secuencias
Las secuencias mostradas representan **únicamente** los días trabajados por cada enfermera. Los días libres, vacaciones y otras incidencias no aparecen en las secuencias pero están presentes en la planificación completa.

### 3. Equidad en la Distribución
- Todas las enfermeras trabajan exactamente **20 turnos regulares**
- La distribución por tipo de turno es muy equilibrada
- Las noches están perfectamente distribuidas (7 noches por enfermera)

---

## 📁 Archivos de Análisis

- [`analisis_solo_turnos_limpio.py`](file:///home/luis/RepositorioGitHub/planificador_turnos/analisis_solo_turnos_limpio.py) - Script de análisis (formato limpio)
- [`analisis_simulacion_solo_turnos.py`](file:///home/luis/RepositorioGitHub/planificador_turnos/analisis_simulacion_solo_turnos.py) - Script de análisis (versión original)

---

**Fecha de generación**: 2026-06-16  
**Ejecución analizada**: #68  
**Filtro aplicado**: Solo celdas tipo TURNO con turnos reales (M/T/N)
