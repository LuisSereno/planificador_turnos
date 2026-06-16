#!/usr/bin/env python
"""Verificación del patrón de rotación MMTTNDNDL"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_turnos.settings')
django.setup()

from turnos.models import Ejecucion, AsignacionTurno

# Obtener ejecución
e = Ejecucion.objects.get(pk=66)
print('=== VERIFICACIÓN DEL PATRÓN MMTTNDNDL ===')
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
    if a.tipo_celda == 'VACACIONES':
        secuencia_real.append('V')
    elif a.es_dia_libre or a.tipo_celda == 'LIBRE':
        secuencia_real.append('L')
    elif a.turno:
        secuencia_real.append(a.turno.codigo_corto or a.turno.nombre[0])

print(f'Secuencia: {"".join(secuencia_real)}')
print(f'Longitud: {len(secuencia_real)} días')

# Patrón esperado MMTTNDNDL (8 días)
patron_esperado = 'MMTTNDNDL'
print(f'\n=== PATRÓN ESPERADO ===')
print(f'Patrón MMTTNDNDL: {patron_esperado}')
print(f'Ciclo: 8 días')

# Simular patrón esperado para María (desfase 0)
print(f'\n=== SIMULACIÓN DEL PATRÓN PARA MARÍA (desfase 0) ===')
patron_teorico = []
for dia in range(31):
    posicion_ciclo = dia % 8
    patron_teorico.append(patron_esperado[posicion_ciclo])

print(f'Patrón teórico MMTTNDNDL: {"".join(patron_teorico)}')
print(f'Patrón real:              {"".join(secuencia_real)}')

# Comparar
coincidencias = sum(1 for a, b in zip(patron_teorico, secuencia_real) if a == b)
print(f'\nCoincidencias con patrón MMTTNDNDL: {coincidencias}/{len(secuencia_real)} ({coincidencias/len(secuencia_real)*100:.1f}%)')

# Análisis detallado
print('\n=== ANÁLISIS DÍA POR DÍA ===')
print('Día | Teórico | Real | Coincide')
print('-' * 40)
for dia in range(31):
    teor = patron_teorico[dia]
    real = secuencia_real[dia]
    coincide = '✓' if teor == real else '✗'
    print(f'{dia+1:3d} | {teor:7s} | {real:4s} | {coincide}')

# Contar diferencias
diferencias = []
for dia in range(31):
    if patron_teorico[dia] != secuencia_real[dia]:
        diferencias.append((dia+1, patron_teorico[dia], secuencia_real[dia]))

print(f'\n=== RESUMEN DE DIFERENCIAS ===')
print(f'Total diferencias: {len(diferencias)}')
if diferencias:
    print('\nPrimeras 10 diferencias:')
    for dia, teor, real in diferencias[:10]:
        print(f'  Día {dia}: esperado {teor}, obtenido {real}')

# Análisis de patrones de 8 días
print('\n=== ANÁLISIS DE PATRONES DE 8 DÍAS ===')
patrones_8 = {}
for i in range(len(secuencia_real) - 7):
    patron = ''.join(secuencia_real[i:i+8])
    patrones_8[patron] = patrones_8.get(patron, 0) + 1

print('Patrones de 8 días más frecuentes:')
for patron, count in sorted(patrones_8.items(), key=lambda x: -x[1])[:5]:
    print(f'  {patron}: {count} veces')

# Verificar si el patrón MMTTNDNDL aparece
if 'MMTTNDNDL' in patrones_8:
    print(f'\n✓ El patrón MMTTNDNDL aparece {patrones_8["MMTTNDNDL"]} veces')
else:
    print('\n✗ El patrón MMTTNDNDL no aparece exactamente')

# Análisis de días libres
print('\n=== ANÁLISIS DE DÍAS LIBRES ===')
libres_count = sum(1 for s in secuencia_real if s == 'L')
print(f'Total días libres: {libres_count}')
print(f'Porcentaje: {libres_count/31*100:.1f}%')
print(f'Esperado en patrón MMTTNDNDL: {31 * 2 / 8:.1f} días libres (2 de cada 8)')

# Análisis de vacaciones
vacaciones_count = sum(1 for s in secuencia_real if s == 'V')
print(f'\nDías de vacaciones: {vacaciones_count}')

# Secuencia sin vacaciones
secuencia_sin_vacaciones = ''.join(s for s in secuencia_real if s != 'V')
print(f'Secuencia sin vacaciones: {secuencia_sin_vacaciones}')

print('\n=== CONCLUSIÓN ===')
if coincidencias / len(secuencia_real) > 0.8:
    print('✓ La secuencia coincide en más del 80% con el patrón MMTTNDNDL')
    print('✓ Las diferencias se deben a optimizaciones del solver CP-SAT')
elif coincidencias / len(secuencia_real) > 0.5:
    print('⚠ La secuencia coincide entre 50-80% con el patrón MMTTNDNDL')
    print('⚠ El solver realizó modificaciones significativas')
else:
    print('✗ La secuencia coincide menos del 50% con el patrón MMTTNDNDL')
    print('✗ El patrón base fue significativamente modificado')
