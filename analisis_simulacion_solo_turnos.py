#!/usr/bin/env python
"""Análisis de simulación mostrando solo turnos regulares (M/T/N)"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_turnos.settings')
django.setup()

from turnos.models import Ejecucion, AsignacionTurno
from turnos.dominio.dtos import TipoCelda

# Obtener última ejecución
e = Ejecucion.objects.latest('id')
print(f'=== ANÁLISIS DE SIMULACIÓN - SOLO TURNOS REGULARES ===')
print(f'Ejecución: {e.id}')
print(f'Configuración: {e.configuracion.nombre}')
print(f'Fecha inicio: {e.configuracion.fecha_inicio}')
print(f'Num días: {e.configuracion.num_dias}')
print(f'Enfermeras: {e.configuracion.enfermeras.count()}')

# Obtener asignaciones
asignaciones = AsignacionTurno.objects.filter(planilla=e.planilla_generada)

# Filtrar solo celdas de tipo TURNO con turnos reales
turnos_regulares = asignaciones.filter(tipo_celda='TURNO').exclude(turno=None)

print(f'\n=== RESUMEN DE TURNOS REGULARES ===')
print(f'Total celdas en planificación: {asignaciones.count()}')
print(f'Celdas tipo TURNO con turno real: {turnos_regulares.count()}')
print(f'Porcentaje: {turnos_regulares.count() / asignaciones.count() * 100:.1f}%')

# Contar por tipo de turno
from django.db.models import Count
conteo_turnos = turnos_regulares.values('turno__nombre', 'turno__codigo_corto').annotate(
    total=Count('id')
).order_by('turno__nombre')

print(f'\n=== DISTRIBUCIÓN DE TURNOS REGULARES ===')
for t in conteo_turnos:
    print(f'{t["turno__nombre"]} [{t["turno__codigo_corto"]}]: {t["total"]} asignaciones')

# Mostrar secuencia por enfermera (solo turnos regulares)
print(f'\n=== SECUENCIA POR ENFERMERA (SOLO TURNOS REGULARES) ===')
enfermeras = turnos_regulares.values_list('enfermera__nombre', flat=True).distinct()

for enf_nombre in sorted(enfermeras):
    asignaciones_enf = turnos_regulares.filter(
        enfermera__nombre=enf_nombre
    ).order_by('fecha')
    
    secuencia = []
    for a in asignaciones_enf:
        codigo = a.turno.codigo_corto or a.turno.nombre[0]
        secuencia.append(codigo)
    
    print(f'\n{enf_nombre}:')
    print(f'  Secuencia: {"".join(secuencia)}')
    print(f'  Total turnos: {len(secuencia)}')
    
    # Contar por tipo
    m_count = secuencia.count('M')
    t_count = secuencia.count('T')
    n_count = secuencia.count('N')
    print(f'  M: {m_count}, T: {t_count}, N: {n_count}')

# Análisis de horarios
print(f'\n=== HORARIOS DE TURNOS REGULARES ===')
from turnos.models import TipoTurno
turnos_info = TipoTurno.objects.filter(nombre__in=['MANANA', 'TARDE', 'NOCHE'])

for turno in turnos_info:
    print(f'{turno.nombre} [{turno.codigo_corto}]:')
    print(f'  Horario: {turno.hora_inicio.strftime("%H:%M")} - {turno.hora_fin.strftime("%H:%M")}')
    print(f'  Duración: {turno.duracion_horas} horas')
    print(f'  Es nocturno: {"Sí" if turno.es_nocturno else "No"}')

# Excluir incidencias
print(f'\n=== INCIDENCIAS EXCLUIDAS DEL ANÁLISIS ===')
tipos_incidencia = ['VACACIONES', 'PERMISO', 'BAJA', 'FORMACION', 'ASIGNACION_FIJA', 'LIBRE']
incidencias = asignaciones.filter(tipo_celda__in=tipos_incidencia)

conteo_incidencias = incidencias.values('tipo_celda').annotate(total=Count('id')).order_by('tipo_celda')
for inc in conteo_incidencias:
    print(f'{inc["tipo_celda"]}: {inc["total"]} celdas')

print(f'\nTotal celdas excluidas: {incidencias.count()}')

# Resumen final
print(f'\n=== RESUMEN FINAL ===')
print(f'Total celdas: {asignaciones.count()}')
print(f'Turnos regulares (M/T/N): {turnos_regulares.count()} ({turnos_regulares.count() / asignaciones.count() * 100:.1f}%)')
print(f'Incidencias excluidas: {incidencias.count()} ({incidencias.count() / asignaciones.count() * 100:.1f}%)')
print(f'Días libres: {asignaciones.filter(es_dia_libre=True).count()}')
