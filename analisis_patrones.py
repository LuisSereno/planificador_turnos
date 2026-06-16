#!/usr/bin/env python
"""Análisis de patrones de turnos configurados"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_turnos.settings')
django.setup()

from turnos.models import ConfiguracionPlanificacion

# Obtener configuración
c = ConfiguracionPlanificacion.objects.get(pk=19)
print('=== CONFIGURACIÓN DE SIMULACIÓN ===')
print(f'Nombre: {c.nombre}')
print(f'Fecha inicio: {c.fecha_inicio}')
print(f'Num días: {c.num_dias}')
print(f'Enfermeras: {c.enfermeras.count()}')
print(f'Turnos: {c.turnos.count()}')

# Patrones JSON
print('\n=== PATRONES CONFIGURADOS (JSON) ===')
if c.patrones_turnos_json:
    print(json.dumps(c.patrones_turnos_json, indent=2, ensure_ascii=False))
else:
    print('No hay patrones JSON configurados')

# Patrones ManyToMany (legacy)
print('\n=== PATRONES MANY-TO-MANY (LEGACY) ===')
patrones_legacy = c.patrones_turnos.all()
if patrones_legacy:
    for p in patrones_legacy:
        print(f'  - {p.nombre} [{p.get_tipo_display()}]')
        print(f'    Dura: {p.es_restriccion_dura}')
        print(f'    Configuración: {p.configuracion}')
else:
    print('No hay patrones ManyToMany configurados')

# Restricciones duras
print('\n=== RESTRICCIONES DURAS ===')
if c.restricciones_duras:
    print(json.dumps(c.restricciones_duras, indent=2, ensure_ascii=False))
else:
    print('No hay restricciones duras configuradas')

# Demanda por turno
print('\n=== DEMANDA POR TURNO ===')
if c.demanda_por_turno:
    print(json.dumps(c.demanda_por_turno, indent=2, ensure_ascii=False))
else:
    print('No hay demanda por turno configurada')

# Análisis de la planificación generada
print('\n=== ANÁLISIS DE LA PLANIFICACIÓN ===')
print('La planificación usa una rotación base determinista 2M-2T-2N-2L')
print('con desfases para escalonar a las 10 enfermeras')
print('\nRotación base:')
print('  Día 1-2: Mañana (M)')
print('  Día 3-4: Tarde (T)')
print('  Día 5-6: Noche (N)')
print('  Día 7-8: Libre (L)')
print('\nDesfases aplicados:')
print('  Enfermeras 1,4,7,10: desfase 0')
print('  Enfermeras 2,5,8: desfase 1')
print('  Enfermeras 3,6,9: desfase 2')
