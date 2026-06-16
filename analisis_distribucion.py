#!/usr/bin/env python
"""Análisis de la distribución de turnos por enfermera"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_turnos.settings')
django.setup()

from turnos.models import Ejecucion, AsignacionTurno

# Obtener ejecución
e = Ejecucion.objects.get(pk=66)
print('=== EJECUCIÓN 63 ===')
print(f'Estado: {e.estado}')
print(f'Configuración: {e.configuracion.nombre}')
print(f'Enfermeras: {e.configuracion.enfermeras.count()}')
print(f'Días: {e.configuracion.num_dias}')

# Obtener asignaciones
asignaciones = AsignacionTurno.objects.filter(planilla=e.planilla_generada)

# Construir matriz de distribución
enfermeras = {}
for a in asignaciones:
    enf = a.enfermera.nombre
    if enf not in enfermeras:
        enfermeras[enf] = {'M': 0, 'T': 0, 'N': 0, 'LIBRE': 0}
    
    if a.es_dia_libre or a.tipo_celda == 'LIBRE':
        enfermeras[enf]['LIBRE'] += 1
    elif a.turno:
        codigo = a.turno.codigo_corto or a.turno.nombre[0]
        enfermeras[enf][codigo] += 1

# Imprimir tabla
print('\n=== DISTRIBUCIÓN POR ENFERMERA ===')
print(f'{"Enfermera":<30} {"M":<6} {"T":<6} {"N":<6} {"LIBRE":<7} {"Total":<7} {"% Libre":<8}')
print('-' * 75)

for enf, counts in sorted(enfermeras.items()):
    total = sum(counts.values())
    pct_libre = (counts['LIBRE'] / total * 100) if total > 0 else 0
    print(f'{enf:<30} {counts["M"]:<6} {counts["T"]:<6} {counts["N"]:<6} {counts["LIBRE"]:<7} {total:<7} {pct_libre:.1f}%')

# Totales generales
print('-' * 75)
total_m = sum(c['M'] for c in enfermeras.values())
total_t = sum(c['T'] for c in enfermeras.values())
total_n = sum(c['N'] for c in enfermeras.values())
total_libre = sum(c['LIBRE'] for c in enfermeras.values())
total_general = total_m + total_t + total_n + total_libre

print(f'{"TOTALES":<30} {total_m:<6} {total_t:<6} {total_n:<6} {total_libre:<7} {total_general:<7} {total_libre/total_general*100:.1f}%')

# Análisis de patrones
print('\n=== ANÁLISIS DE PATRONES ===')
print(f'Total turnos trabajados: {total_m + total_t + total_n}')
print(f'Total días libres: {total_libre}')
print(f'Promedio turnos por enfermera: {(total_m + total_t + total_n) / len(enfermeras):.1f}')
print(f'Promedio días libres por enfermera: {total_libre / len(enfermeras):.1f}')

# Verificar equidad
print('\n=== EQUIDAD EN LA DISTRIBUCIÓN ===')
turnos_por_enf = [sum(c.values()) - c['LIBRE'] for c in enfermeras.values()]
libres_por_enf = [c['LIBRE'] for c in enfermeras.values()]

print(f'Turnos trabajados - Min: {min(turnos_por_enf)}, Max: {max(turnos_por_enf)}, Diferencia: {max(turnos_por_enf) - min(turnos_por_enf)}')
print(f'Días libres - Min: {min(libres_por_enf)}, Max: {max(libres_por_enf)}, Diferencia: {max(libres_por_enf) - min(libres_por_enf)}')

# Revisar patrones de secuencia
print('\n=== PATRONES DE SECUENCIA (ejemplo: María Garcia) ===')
maria_asignaciones = asignaciones.filter(enfermera__nombre='Maria Garcia Lopez').order_by('fecha')
secuencia = []
for a in maria_asignaciones:
    if a.es_dia_libre or a.tipo_celda == 'LIBRE':
        secuencia.append('L')
    elif a.turno:
        secuencia.append(a.turno.codigo_corto or a.turno.nombre[0])

print(f'Secuencia de 31 días: {"".join(secuencia)}')

# Contar turnos consecutivos
max_consecutivos = 0
actual = 0
for dia in secuencia:
    if dia != 'L':
        actual += 1
        max_consecutivos = max(max_consecutivos, actual)
    else:
        actual = 0

print(f'Máximo días consecutivos trabajando: {max_consecutivos}')

# Contar noches consecutivas
noches_consecutivas = 0
max_noches = 0
for a in maria_asignaciones.order_by('fecha'):
    if a.turno and a.turno.nombre == 'NOCHE':
        noches_consecutivas += 1
        max_noches = max(max_noches, noches_consecutivas)
    else:
        noches_consecutivas = 0

print(f'Máximo noches consecutivas: {max_noches}')
