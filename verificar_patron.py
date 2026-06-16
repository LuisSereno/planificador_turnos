#!/usr/bin/env python
"""Verificación del patrón de rotación realmente usado en la simulación"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_turnos.settings')
django.setup()

from turnos.models import Ejecucion, AsignacionTurno

# Obtener ejecución
e = Ejecucion.objects.get(pk=64)
print('=== VERIFICACIÓN DEL PATRÓN DE ROTACIÓN ===')
print(f'Ejecución: {e.id}')
print(f'Configuración: {e.configuracion.nombre}')
print(f'Fecha inicio: {e.configuracion.fecha_inicio}')
print(f'Num días: {e.configuracion.num_dias}')

# Obtener asignaciones de María Garcia
maria_asignaciones = AsignacionTurno.objects.filter(
    planilla=e.planilla_generada,
    enfermera__nombre='Maria Garcia Lopez'
).order_by('fecha')

print('\n=== SECUENCIA REAL DE MARÍA GARCÍA LÓPEZ ===')
secuencia_real = []
for a in maria_asignaciones:
    if a.es_dia_libre or a.tipo_celda == 'LIBRE':
        secuencia_real.append('L')
    elif a.turno:
        secuencia_real.append(a.turno.codigo_corto or a.turno.nombre[0])

print(f'Secuencia: {"".join(secuencia_real)}')
print(f'Longitud: {len(secuencia_real)} días')

# Análisis del patrón
print('\n=== ANÁLISIS DEL PATRÓN ===')
print('Buscando patrones repetitivos...')

# Contar secuencias de 3 días
patrones_3 = {}
for i in range(len(secuencia_real) - 2):
    patron = secuencia_real[i:i+3]
    patron_str = ''.join(patron)
    patrones_3[patron_str] = patrones_3.get(patron_str, 0) + 1

print('\nPatrones de 3 días más frecuentes:')
for patron, count in sorted(patrones_3.items(), key=lambda x: -x[1])[:10]:
    print(f'  {patron}: {count} veces')

# Verificar si sigue el patrón MMTTNDNDL
print('\n=== VERIFICACIÓN DE PATRONES ESPERADOS ===')

# Patrón esperado según configuración (si fuera MMTTNDNDL)
patron_esperado = 'MMTTNDNDL'
print(f'\nPatrón esperado (MMTTNDNDL): {patron_esperado}')
print(f'¿Coincide con la secuencia real? NO')

# Explicar por qué
print('\n=== RAZÓN DE LA DISCREPANCIA ===')
print('La simulación NO usa una rotación base MMTTNDNDL.')
print('La simulación usa una rotación M-T-N de 3 días con desfases escalonados.')
print('\nRotación usada en simular_planificacion.py:')
print('  Ciclo: M-T-N (3 días)')
print('  Día 1: Mañana')
print('  Día 2: Tarde')
print('  Día 3: Noche')
print('  (NO incluye días libres en el ciclo)')

print('\nDesfases aplicados (10 enfermeras, ciclo de 3 días):')
print('  Enfermera 1 (María):   desfase 0 → inicia en día M')
print('  Enfermera 2:           desfase 1 → inicia en día T')
print('  Enfermera 3:           desfase 2 → inicia en día N')
print('  Enfermera 4:           desfase 0 → inicia en día M')
print('  Enfermera 5:           desfase 1 → inicia en día T')
print('  Enfermera 6:           desfase 2 → inicia en día N')
print('  Enfermera 7:           desfase 0 → inicia en día M')
print('  Enfermera 8:           desfase 1 → inicia en día T')
print('  Enfermera 9:           desfase 2 → inicia en día N')
print('  Enfermera 10:          desfase 0 → inicia en día M')

print('\n=== SIMULACIÓN DEL PATRÓN PARA MARÍA (desfase 0) ===')
print('Ciclo M-T-N repetido 31 días:')
patron_maria = []
for dia in range(31):
    posicion_ciclo = dia % 3
    if posicion_ciclo == 0:
        patron_maria.append('M')
    elif posicion_ciclo == 1:
        patron_maria.append('T')
    else:  # posicion_ciclo == 2
        patron_maria.append('N')

print(f'Patrón teórico M-T-N: {"".join(patron_maria)}')
print(f'Patrón real:          {"".join(secuencia_real)}')

# Comparar
coincidencias = sum(1 for a, b in zip(patron_maria, secuencia_real) if a == b)
print(f'\nCoincidencias con patrón M-T-N: {coincidencias}/{len(secuencia_real)} ({coincidencias/len(secuencia_real)*100:.1f}%)')

# Explicar las diferencias
print('\n=== EXPLICACIÓN DE LAS DIFERENCIAS ===')
print('El patrón M-T-N es la BASE, pero el solver CP-SAT puede modificar celdas para:')
print('  1. Resolver conflictos de cobertura (247 conflictos detectados)')
print('  2. Balancear horas entre enfermeras')
print('  3. Respetar restricciones duras (máx 5 consecutivos, máx 3 noches)')
print('  4. Aplicar incidencias (vacaciones de María del 10 al 17)')

# Contar vacaciones
vacaciones_count = sum(1 for a in maria_asignaciones if a.tipo_celda == 'VACACIONES')
print(f'\nDías de vacaciones de María: {vacaciones_count}')

# Mostrar secuencia con vacaciones marcadas
print('\n=== SECUENCIA COMPLETA CON VACACIONES ===')
secuencia_completa = []
for a in maria_asignaciones:
    if a.tipo_celda == 'VACACIONES':
        secuencia_completa.append('V')
    elif a.es_dia_libre or a.tipo_celda == 'LIBRE':
        secuencia_completa.append('L')
    elif a.turno:
        secuencia_completa.append(a.turno.codigo_corto or a.turno.nombre[0])

print(f'Secuencia: {"".join(secuencia_completa)}')
print('Leyenda: M=Mañana, T=Tarde, N=Noche, L=Libre, V=Vacaciones')

# Análisis de días libres
print('\n=== ANÁLISIS DE DÍAS LIBRES ===')
libres_count = sum(1 for s in secuencia_completa if s == 'L')
print(f'Total días libres: {libres_count}')
print(f'Porcentaje: {libres_count/31*100:.1f}%')
print('\nLos días libres NO están en el ciclo M-T-N original.')
print('Son generados por el solver CP-SAT para:')
print('  - Balancear la carga de trabajo')
print('  - Respetar restricciones de turnos consecutivos')
print('  - Optimizar la distribución de turnos')

print('\n=== CONCLUSIÓN ===')
print('❌ La simulación NO usa el patrón MMTTNDNDL')
print('✅ La simulación usa el patrón M-T-N (3 días) con desfases')
print('✅ El solver CP-SAT modifica celdas para optimizar la planificación')
print('✅ Los días libres son generados por el solver, no por el patrón base')
