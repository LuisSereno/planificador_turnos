#!/usr/bin/env python
"""Análisis de simulación mostrando solo turnos regulares (M/T/N) - Formato limpio"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_turnos.settings')
django.setup()

from turnos.models import Ejecucion, AsignacionTurno, TipoTurno
from django.db.models import Count

# Obtener última ejecución
e = Ejecucion.objects.latest('id')

print('\n' + '='*80)
print('ANÁLISIS DE SIMULACIÓN - SOLO TURNOS REGULARES (M/T/N)')
print('='*80)

print(f'\n📋 INFORMACIÓN GENERAL')
print(f'   Ejecución: #{e.id}')
print(f'   Configuración: {e.configuracion.nombre}')
print(f'   Período: {e.configuracion.fecha_inicio} a {e.configuracion.fecha_inicio + __import__("datetime").timedelta(days=e.configuracion.num_dias-1)}')
print(f'   Total días: {e.configuracion.num_dias}')
print(f'   Enfermeras: {e.configuracion.enfermeras.count()}')

# Obtener asignaciones
asignaciones = AsignacionTurno.objects.filter(planilla=e.planilla_generada)

# Filtrar solo celdas de tipo TURNO con turnos reales
turnos_regulares = asignaciones.filter(tipo_celda='TURNO').exclude(turno=None)

print(f'\n📊 RESUMEN DE TURNOS REGULARES')
print(f'   Total celdas en planificación: {asignaciones.count()}')
print(f'   Celdas tipo TURNO con turno real: {turnos_regulares.count()}')
print(f'   Porcentaje: {turnos_regulares.count() / asignaciones.count() * 100:.1f}%')

# Contar por tipo de turno
conteo_turnos = turnos_regulares.values('turno__nombre', 'turno__codigo_corto').annotate(
    total=Count('id')
).order_by('turno__nombre')

print(f'\n🕐 DISTRIBUCIÓN DE TURNOS REGULARES')
for t in conteo_turnos:
    print(f'   {t["turno__nombre"]} [{t["turno__codigo_corto"]}]: {t["total"]} asignaciones')

# Mostrar horarios
print(f'\n⏰ HORARIOS DE TURNOS REGULARES')
turnos_info = TipoTurno.objects.filter(nombre__in=['MANANA', 'TARDE', 'NOCHE']).order_by('nombre')
for turno in turnos_info:
    nocturno = "🌙" if turno.es_nocturno else "☀️"
    print(f'   {nocturno} {turno.nombre} [{turno.codigo_corto}]:')
    print(f'      Horario: {turno.hora_inicio.strftime("%H:%M")} - {turno.hora_fin.strftime("%H:%M")}')
    print(f'      Duración: {turno.duracion_horas} horas')

# Mostrar secuencia por enfermera
print(f'\n👩‍⚕️ SECUENCIA POR ENFERMERA (SOLO TURNOS REGULARES)')
enfermeras = turnos_regulares.values_list('enfermera__nombre', flat=True).distinct().order_by('enfermera__nombre')

for enf_nombre in enfermeras:
    asignaciones_enf = turnos_regulares.filter(
        enfermera__nombre=enf_nombre
    ).order_by('fecha')
    
    secuencia = []
    for a in asignaciones_enf:
        codigo = a.turno.codigo_corto or a.turno.nombre[0]
        secuencia.append(codigo)
    
    m_count = secuencia.count('M')
    t_count = secuencia.count('T')
    n_count = secuencia.count('N')
    
    print(f'\n   {enf_nombre}')
    print(f'      Secuencia: {"".join(secuencia)}')
    print(f'      Total: {len(secuencia)} turnos (M:{m_count} T:{t_count} N:{n_count})')

# Excluir incidencias
print(f'\n🚫 INCIDENCIAS EXCLUIDAS DEL ANÁLISIS')
tipos_incidencia = ['VACACIONES', 'PERMISO', 'BAJA', 'FORMACION', 'ASIGNACION_FIJA', 'LIBRE']
incidencias = asignaciones.filter(tipo_celda__in=tipos_incidencia)

conteo_incidencias = incidencias.values('tipo_celda').annotate(total=Count('id')).order_by('tipo_celda')
for inc in conteo_incidencias:
    print(f'   {inc["tipo_celda"]}: {inc["total"]} celdas')

print(f'   Total celdas excluidas: {incidencias.count()}')

# Resumen final
print(f'\n✅ RESUMEN FINAL')
print(f'   Total celdas: {asignaciones.count()}')
print(f'   Turnos regulares (M/T/N): {turnos_regulares.count()} ({turnos_regulares.count() / asignaciones.count() * 100:.1f}%)')
print(f'   Incidencias excluidas: {incidencias.count()} ({incidencias.count() / asignaciones.count() * 100:.1f}%)')
print(f'   Días libres: {asignaciones.filter(es_dia_libre=True).count()}')

print('\n' + '='*80)
