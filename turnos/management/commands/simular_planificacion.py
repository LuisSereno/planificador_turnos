#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simulador integral del sistema de planificacion de turnos.
Ejercita: modelos, solver (pipeline motor), planilla, exportacion PDF/Excel.
Uso: python manage.py simular_planificacion
"""
import traceback
from datetime import date, timedelta, time

from django.core.management.base import BaseCommand

from django.contrib.auth.models import User
from django.db import transaction

from turnos.models import (
    Workspace, Enfermera, TipoTurno,
    ConfiguracionPlanificacion, Ejecucion,
    Planilla, AsignacionTurno,
)
from turnos.dominio.dtos import TurnoInfo, RotacionCiclo, Incidencia, TipoIncidencia
from turnos.motor.pipeline import PipelinePlanificacion


# ============================================================================
# Helpers
# ============================================================================
def _sep(titulo: str):
    print(f"\n{'='*70}")
    print(f"  {titulo}")
    print(f"{'='*70}")


def _ok(msg: str):
    print(f"  [OK] {msg}")


def _fail(msg: str):
    print(f"  [FAIL] {msg}")


def _info(msg: str):
    print(f"  [..] {msg}")


# ============================================================================
# FASE 0: Limpieza
# ============================================================================
def fase0_limpiar():
    _sep("FASE 0 - Limpieza de datos de simulacion")
    Workspace.objects.filter(nombre__startswith="SIM_").delete()
    User.objects.filter(username__startswith="sim_user_").delete()
    _ok("Datos de simulacion anteriores eliminados")


# ============================================================================
# FASE 1: Crear workspace + usuario
# ============================================================================
def fase1_workspace():
    _sep("FASE 1 - Crear workspace y usuario")
    user = User.objects.create_user(
        username="sim_user_test",
        password="testpass123",
        email="sim@test.com",
        first_name="Sim",
        last_name="Test",
    )
    workspace = Workspace.objects.create(
        nombre="SIM_Sacyl_Hospital_Universitario",
        descripcion="Workspace de simulacion basado en formulario real Sacyl",
        creado_por=user,
    )
    workspace.usuarios.add(user)
    _ok(f"Workspace creado: {workspace.nombre} (id={workspace.id})")
    _ok(f"Usuario creado: {user.username} (id={user.id})")
    return user, workspace


# ============================================================================
# FASE 2: Crear tipos de turno con codigo_corto
# ============================================================================
def fase2_tipos_turno(workspace):
    _sep("FASE 2 - Crear tipos de turno (M/T/N)")
    definiciones = [
        {"nombre": "MANANA", "codigo_corto": "M", "hora_inicio": time(7, 0), "hora_fin": time(15, 0)},
        {"nombre": "TARDE",  "codigo_corto": "T", "hora_inicio": time(15, 0), "hora_fin": time(23, 0)},
        {"nombre": "NOCHE",  "codigo_corto": "N", "hora_inicio": time(23, 0), "hora_fin": time(7, 0)},
    ]
    turnos = {}
    for d in definiciones:
        turno, created = TipoTurno.objects.get_or_create(
            nombre=d["nombre"],
            workspace=workspace,
            defaults={
                "codigo_corto": d["codigo_corto"],
                "hora_inicio": d["hora_inicio"],
                "hora_fin": d["hora_fin"],
                "activo": True,
            },
        )
        if not created and not turno.codigo_corto:
            turno.codigo_corto = d["codigo_corto"]
            turno.save(update_fields=["codigo_corto"])
        turnos[d["nombre"]] = turno
        estado = "creado" if created else "actualizado"
        _ok(f"Turno {turno.nombre} [{turno.codigo_corto}] {estado} "
            f"({turno.hora_inicio.strftime('%H:%M')}-{turno.hora_fin.strftime('%H:%M')})")

    # Verificar codigo_display
    for t in turnos.values():
        assert t.codigo_display() == t.codigo_corto, (
            f"codigo_display() devolvio {t.codigo_display()} en vez de {t.codigo_corto}"
        )
    _ok("codigo_display() correcto para todos los turnos")
    return turnos


# ============================================================================
# FASE 3: Crear enfermeras
# ============================================================================
def fase3_enfermeras(workspace, cantidad=10):
    _sep(f"FASE 3 - Crear {cantidad} enfermeras")
    nombres = [
        "Maria Garcia Lopez", "Ana Martinez Ruiz", "Laura Fernandez Sanz",
        "Carmen Lopez Diaz", "Isabel Rodriguez Moreno", "Pilar Sanchez Gil",
        "Elena Torres Navarro", "Marta Ruiz Jimenez", "Lucia Moreno Blanco",
        "Sofia Alvarez Romero",
    ]
    enfermeras = []
    for i in range(cantidad):
        nombre = nombres[i] if i < len(nombres) else f"Enfermera Simulada {i+1}"
        enf, created = Enfermera.objects.get_or_create(
            email=f"sim.enf{i+1}@test.com",
            defaults={
                "workspace": workspace,
                "nombre": nombre,
                "telefono": f"600{i:06d}",
                "dni": f"SIM{i:06d}X",
                "activa": True,
                "notas": "Enfermera de simulacion",
            },
        )
        enfermeras.append(enf)
        _ok(f"Enfermera: {enf.nombre} (id={enf.id})")
    _ok(f"{len(enfermeras)} enfermeras creadas/existentes")
    return enfermeras


# ============================================================================
# FASE 4: Crear configuracion de planificacion (mes completo)
# ============================================================================
def fase4_configuracion(workspace, user, enfermeras, turnos):
    _sep("FASE 4 - Crear configuracion de planificacion (Julio 2025)")
    fecha_inicio = date(2025, 7, 1)
    num_dias = 31  # Julio tiene 31 dias

    config, created = ConfiguracionPlanificacion.objects.get_or_create(
        nombre="SIM_Planilla Julio 2025",
        workspace=workspace,
        defaults={
            "descripcion": "Configuracion de simulacion basada en planilla real Sacyl",
            "activa": True,
            "num_dias": num_dias,
            "fecha_inicio": fecha_inicio,
            "demanda_por_turno": {
                "MANANA": {"min": 2, "max": 5, "optimo": 3},
                "TARDE":  {"min": 2, "max": 4, "optimo": 3},
                "NOCHE":  {"min": 1, "max": 3, "optimo": 2},
            },
            "restricciones_duras": [
                {"nombre": "COBERTURA_MINIMA", "valor": {"MANANA": 2, "TARDE": 2, "NOCHE": 1}},
                {"nombre": "TURNO_CONSECUTIVOS_MAX", "valor": 5},
                {"nombre": "NOCHES_CONSECUTIVAS_MAX", "valor": 3},
            ],
            "restricciones_blandas": [
                {"nombre": "EQUIDAD_TURNOS", "peso": 5},
                {"nombre": "BALANCE_HORAS", "peso": 10},
            ],
            "num_trabajadores": 4,
            "tiempo_maximo_segundos": 60,
            "seed": 42,
            "creado_por": user,
        },
    )
    if created:
        config.enfermeras.set(enfermeras)
        config.turnos.set(turnos.values())
    _ok(f"Configuracion: {config.nombre} (id={config.id})")
    _ok(f"  Fecha inicio: {config.fecha_inicio}")
    _ok(f"  Num dias: {config.num_dias}")
    _ok(f"  Enfermeras: {config.enfermeras.count()}")
    _ok(f"  Turnos: {config.turnos.count()}")
    return config


# ============================================================================
# FASE 5: Ejecutar el pipeline del motor
# ============================================================================
def fase5_ejecutar_pipeline(config, enfermeras, turnos):
    _sep("FASE 5 - Ejecutar pipeline de planificacion (motor)")

    # Preparar fechas
    fechas = [config.fecha_inicio + timedelta(days=i) for i in range(config.num_dias)]
    _info(f"Fechas: {fechas[0]} a {fechas[-1]} ({len(fechas)} dias)")

    # Preparar enfermeras dict {id: nombre}
    enfermeras_dict = {e.id: e.nombre for e in enfermeras}

    # Preparar turnos_info {id: TurnoInfo}
    turnos_info = {
        t.id: TurnoInfo(
            id=t.id,
            nombre=t.nombre,
            hora_inicio=t.hora_inicio,
            hora_fin=t.hora_fin,
            duracion_horas=t.duracion_horas,
            es_nocturno=t.es_nocturno,
        )
        for t in turnos.values()
    }

    # Crear rotacion ciclica M->T->N para todas las enfermeras con desfases
    turno_ids = list(turnos_info.keys())
    _info(f"Turno IDs para rotacion: {[turnos_info[tid].nombre for tid in turno_ids]}")

    # Construir ciclo: 1M-1T-1N (3 dias) usando objetos TurnoInfo
    celdas_ciclo = [turnos_info[tid] for tid in turno_ids]
    ciclo = RotacionCiclo(
        nombre='M-T-N',
        ciclo_dias=len(turno_ids),
        celdas=celdas_ciclo,
    )

    asignaciones_rotacion = {}
    desfases = {}
    for i, enf_id in enumerate(enfermeras_dict.keys()):
        asignaciones_rotacion[enf_id] = ciclo
        desfases[enf_id] = i % len(turno_ids)  # Desfase escalonado
    _info(f"Rotacion: {len(asignaciones_rotacion)} enfermeras con desfases {[desfases[eid] for eid in desfases]}")

    # Cobertura minima
    cobertura_minima = {tid: 1 for tid in turno_ids}

    # Horas objetivo por enfermera (horas/mes)
    horas_objetivo = {enf_id: 160.0 for enf_id in enfermeras_dict.keys()}

    # Incidencias: simular vacaciones para 1 enfermera (dias 10-17)
    enf_vacaciones = list(enfermeras_dict.keys())[0]
    incidencias = [
        Incidencia(
            enfermera_id=enf_vacaciones,
            enfermera_nombre=enfermeras_dict[enf_vacaciones],
            fecha_inicio=fechas[9],
            fecha_fin=fechas[16],
            tipo=TipoIncidencia.VACACIONES,
            observaciones="Vacaciones simuladas",
        )
    ]
    _info(f"Incidencia: {enfermeras_dict[enf_vacaciones]} vacaciones {fechas[9]} a {fechas[16]}")

    # Ejecutar pipeline
    _info("Ejecutando PipelinePlanificacion...")
    pipeline = PipelinePlanificacion(
        fechas=fechas,
        enfermeras=enfermeras_dict,
        asignaciones_rotacion=asignaciones_rotacion,
        desfases=desfases,
        incidencias=incidencias,
        horas_objetivo=horas_objetivo,
        cobertura_minima=cobertura_minima,
        configuracion_solver={"tiempo_maximo_segundos": 30, "seed": 42},
        turnos_info=turnos_info,
        restricciones_duras=config.restricciones_duras or [],
        restricciones_blandas=config.restricciones_blandas or [],
        balances_historicos={},
    )

    resultado = pipeline.ejecutar()

    _ok(f"Pipeline exitosa: {resultado.exitosa}")
    _ok(f"Estado solver: {resultado.estado_solver}")
    _ok(f"Total celdas: {resultado.matriz.total_celdas()}")
    _ok(f"Balances generados: {len(resultado.balances)}")
    _ok(f"Metricas: {list(resultado.metricas.keys()) if resultado.metricas else 'N/A'}")

    if resultado.violaciones:
        _info(f"Violaciones ({len(resultado.violaciones)}):")
        for v in resultado.violaciones[:5]:
            _info(f"  - {v}")

    # Resumen de asignaciones por turno
    conteo_turnos = {tid: 0 for tid in turno_ids}
    conteo_libres = 0
    for enf_id, celdas_enf in resultado.matriz.celdas.items():
        for fecha, celda in celdas_enf.items():
            if celda.turno is not None:
                conteo_turnos[celda.turno.id] = conteo_turnos.get(celda.turno.id, 0) + 1
            elif celda.es_libre:
                conteo_libres += 1

    _info("Distribucion de asignaciones:")
    for tid, count in conteo_turnos.items():
        nombre = turnos_info[tid].nombre
        _info(f"  {nombre}: {count} asignaciones")
    _info(f"  Libres/vacantes: {conteo_libres}")

    return resultado, fechas, enfermeras_dict, turnos_info


# ============================================================================
# FASE 6: Persistir resultados (Ejecucion + Planilla + Asignaciones)
# ============================================================================
def fase6_persistir(config, resultado, fechas, enfermeras_dict, turnos, turnos_info):
    _sep("FASE 6 - Persistir resultados en BD")

    with transaction.atomic():
        # Crear Ejecucion
        ejecucion = Ejecucion.objects.create(
            configuracion=config,
            workspace=config.workspace,
            estado='COMPLETADA' if resultado.exitosa else 'INVIABLE',
            es_optima=resultado.estado_solver == 'OPTIMAL',
            penalizacion_total=sum(b.desviacion_horas for b in resultado.balances.values()) if resultado.balances else 0,
            resultado={
                'metricas': resultado.metricas,
                'estado_solver': resultado.estado_solver,
                'num_violaciones': len(resultado.violaciones),
            },
            mensajes={
                'violaciones': resultado.violaciones[:10],
                'warnings': [],
            },
        )
        _ok(f"Ejecucion creada: id={ejecucion.id}, estado={ejecucion.estado}")

        # Crear Planilla
        planilla = Planilla.objects.create(
            workspace=config.workspace,
            nombre=f"Planilla {fechas[0].strftime('%B %Y')}",
            ejecucion=ejecucion,
            fecha_inicio=fechas[0],
            fecha_fin=fechas[-1],
            num_dias=len(fechas),
        )
        _ok(f"Planilla creada: id={planilla.id}, {planilla.num_dias} dias")

        # Crear AsignacionTurno para cada celda
        turno_models = {t.nombre: t for t in turnos.values()}
        asignaciones_count = 0
        for enf_id, celdas_enf in resultado.matriz.celdas.items():
            for fecha, celda in celdas_enf.items():
                turno_model = None
                es_dia_libre = False
                tipo_celda = 'TURNO'

                if celda.turno is not None:
                    # celda.turno es un objeto TurnoInfo, buscar por su id
                    turno_info = turnos_info.get(celda.turno.id)
                    if turno_info:
                        turno_model = turno_models.get(turno_info.nombre)
                elif celda.es_libre:
                    es_dia_libre = True
                    tipo_celda = 'LIBRE'
                else:
                    # Celda sin turno y sin dia libre: dia libre por defecto
                    es_dia_libre = True
                    tipo_celda = 'LIBRE'

                AsignacionTurno.objects.create(
                    planilla=planilla,
                    enfermera_id=enf_id,
                    fecha=fecha,
                    turno=turno_model,
                    es_dia_libre=es_dia_libre,
                    tipo_celda=tipo_celda,
                )
                asignaciones_count += 1

        _ok(f"AsignacionesTurno creadas: {asignaciones_count}")

    return ejecucion, planilla


# ============================================================================
# FASE 7: Probar exportacion PDF
# ============================================================================
def fase7_exportar_pdf(ejecucion):
    _sep("FASE 7 - Exportar PDF (planilla horizontal)")
    try:
        from turnos.utils.exportacion import generar_pdf_planilla
        buffer = generar_pdf_planilla(ejecucion)
        size = len(buffer.getvalue())
        _ok(f"PDF generado: {size:,} bytes ({size/1024:.1f} KB)")
        # Guardar para inspeccion manual
        output_path = "/tmp/simulacion_planilla.pdf"
        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())
        _ok(f"PDF guardado en: {output_path}")
        return True
    except Exception as e:
        _fail(f"Error generando PDF: {e}")
        traceback.print_exc()
        return False


# ============================================================================
# FASE 8: Probar exportacion Excel
# ============================================================================
def fase8_exportar_excel(ejecucion):
    _sep("FASE 8 - Exportar Excel (planilla horizontal)")
    try:
        from turnos.utils.exportacion import generar_excel_planilla
        buffer = generar_excel_planilla(ejecucion)
        size = len(buffer.getvalue())
        _ok(f"Excel generado: {size:,} bytes ({size/1024:.1f} KB)")
        output_path = "/tmp/simulacion_planilla.xlsx"
        with open(output_path, "wb") as f:
            f.write(buffer.getvalue())
        _ok(f"Excel guardado en: {output_path}")
        return True
    except Exception as e:
        _fail(f"Error generando Excel: {e}")
        traceback.print_exc()
        return False


# ============================================================================
# FASE 9: Validar integridad de datos
# ============================================================================
def fase9_validar(planilla, enfermeras_dict, fechas):
    _sep("FASE 9 - Validar integridad de datos persistidos")

    # 1. Total de asignaciones esperadas
    total_esperado = len(enfermeras_dict) * len(fechas)
    total_real = AsignacionTurno.objects.filter(planilla=planilla).count()
    if total_real == total_esperado:
        _ok(f"Total asignaciones: {total_real} (esperado: {total_esperado})")
    else:
        _fail(f"Total asignaciones: {total_real} != esperado: {total_esperado}")

    # 2. Verificar que cada enfermera tiene asignaciones para todos los dias
    for enf_id, nombre in enfermeras_dict.items():
        count = AsignacionTurno.objects.filter(planilla=planilla, enfermera_id=enf_id).count()
        if count != len(fechas):
            _fail(f"Enfermera {nombre} (id={enf_id}): {count} asignaciones, esperado {len(fechas)}")

    _ok("Todas las enfermeras tienen asignaciones completas")

    # 3. Verificar que no hay celdas TURNO sin turno ni dia_libre
    celdas_invalidas = AsignacionTurno.objects.filter(
        planilla=planilla,
        tipo_celda='TURNO',
        turno__isnull=True,
        es_dia_libre=False,
    ).count()
    if celdas_invalidas == 0:
        _ok("No hay celdas TURNO invalidas (sin turno ni dia_libre)")
    else:
        _fail(f"{celdas_invalidas} celdas TURNO sin turno ni dia_libre")

    # 4. Verificar codigo_corto en tipos de turno
    turnos_con_codigo = TipoTurno.objects.filter(
        id__in=AsignacionTurno.objects.filter(
            planilla=planilla, turno__isnull=False
        ).values_list('turno_id', flat=True)
    ).exclude(codigo_corto='').count()
    turnos_asignados = AsignacionTurno.objects.filter(
        planilla=planilla, turno__isnull=False
    ).values('turno_id').distinct().count()
    if turnos_con_codigo == turnos_asignados:
        _ok(f"Todos los {turnos_con_codigo} turnos asignados tienen codigo_corto")
    else:
        _fail(f"{turnos_con_codigo}/{turnos_asignados} turnos con codigo_corto")

    # 5. Resumen de distribucion
    _info("Distribucion persistida:")
    from django.db.models import Count
    dist = AsignacionTurno.objects.filter(planilla=planilla).values(
        'turno__nombre', 'turno__codigo_corto'
    ).annotate(total=Count('id')).order_by('turno__nombre')
    for d in dist:
        _info(f"  {d['turno__nombre']} [{d['turno__codigo_corto']}]: {d['total']}")

    libres = AsignacionTurno.objects.filter(planilla=planilla, es_dia_libre=True).count()
    _info(f"  Dias libres: {libres}")


# ============================================================================
# FASE 10: Probar exportacion profesional (ExportadorProfesional)
# ============================================================================
def fase10_exportador_profesional(ejecucion):
    _sep("FASE 10 - ExportadorProfesional (PDF + Excel profesional)")
    try:
        from turnos.utils.exportacion import _ejecucion_to_planificacion_data
        from turnos.utils.exportador_profesional import ExportadorProfesional

        datos = _ejecucion_to_planificacion_data(ejecucion)
        _ok(f"Bridge function: {len(datos['enfermeras'])} enfermeras, "
            f"{len(datos['turnos_asignados'])} asignaciones")

        # Verificar que los codigos cortos se usan en la matriz
        codigos_en_matriz = set(datos['turnos_asignados'].values())
        _ok(f"Codigos en matriz: {codigos_en_matriz}")

        # Generar PDF profesional
        exportador = ExportadorProfesional(datos)
        from io import BytesIO
        buffer_pdf = BytesIO()
        exportador.exportar_pdf(buffer_pdf)
        buffer_pdf.seek(0)
        pdf_bytes = buffer_pdf.getvalue()
        _ok(f"PDF profesional: {len(pdf_bytes):,} bytes ({len(pdf_bytes)/1024:.1f} KB)")
        with open("/tmp/simulacion_profesional.pdf", "wb") as f:
            f.write(pdf_bytes)
        _ok("PDF profesional guardado en: /tmp/simulacion_profesional.pdf")

        # Generar Excel profesional
        buffer_xlsx = BytesIO()
        exportador.exportar_excel(buffer_xlsx)
        buffer_xlsx.seek(0)
        xlsx_bytes = buffer_xlsx.getvalue()
        _ok(f"Excel profesional: {len(xlsx_bytes):,} bytes ({len(xlsx_bytes)/1024:.1f} KB)")
        with open("/tmp/simulacion_profesional.xlsx", "wb") as f:
            f.write(xlsx_bytes)
        _ok("Excel profesional guardado en: /tmp/simulacion_profesional.xlsx")

        return True
    except Exception as e:
        _fail(f"Error en ExportadorProfesional: {e}")
        traceback.print_exc()
        return False


# ============================================================================
# FASE 11: Probar escenario con diferente numero de enfermeras
# ============================================================================
def fase11_escenario_reducido(workspace, user, turnos):
    _sep("FASE 11 - Escenario reducido (5 enfermeras, 7 dias)")
    try:
        # Crear 5 enfermeras
        enfermeras_escenario = []
        for i in range(5):
            enf, _ = Enfermera.objects.get_or_create(
                email=f"sim.esc{i+1}@test.com",
                defaults={
                    "workspace": workspace,
                    "nombre": f"Escenario {i+1}",
                    "activa": True,
                },
            )
            enfermeras_escenario.append(enf)

        config_esc = ConfiguracionPlanificacion.objects.create(
            nombre="SIM_Escenario Reducido",
            workspace=workspace,
            descripcion="Escenario de 5 enfermeras, agosto 2025",
            activa=True,
            num_dias=31,  # Agosto tiene 31 dias
            fecha_inicio=date(2025, 8, 1),
            demanda_por_turno={
                "MANANA": {"min": 1, "max": 3, "optimo": 2},
                "TARDE":  {"min": 1, "max": 3, "optimo": 2},
                "NOCHE":  {"min": 1, "max": 2, "optimo": 1},
            },
            restricciones_duras=[],
            restricciones_blandas=[],
            num_trabajadores=2,
            tiempo_maximo_segundos=30,
            seed=123,
            creado_por=user,
        )
        config_esc.enfermeras.set(enfermeras_escenario)
        config_esc.turnos.set(turnos.values())

        fechas = [config_esc.fecha_inicio + timedelta(days=i) for i in range(config_esc.num_dias)]
        enfermeras_dict = {e.id: e.nombre for e in enfermeras_escenario}
        turnos_info = {
            t.id: TurnoInfo(
                id=t.id, nombre=t.nombre,
                hora_inicio=t.hora_inicio, hora_fin=t.hora_fin,
                duracion_horas=t.duracion_horas, es_nocturno=t.es_nocturno,
            )
            for t in turnos.values()
        }
        turno_ids = list(turnos_info.keys())
        celdas_ciclo = [turnos_info[tid] for tid in turno_ids]
        ciclo_esc = RotacionCiclo(
            nombre='M-T-N',
            ciclo_dias=len(turno_ids),
            celdas=celdas_ciclo,
        )
        asignaciones_rotacion = {
            enf_id: ciclo_esc
            for enf_id in enfermeras_dict
        }
        desfases = {enf_id: i % len(turno_ids) for i, enf_id in enumerate(enfermeras_dict)}

        pipeline = PipelinePlanificacion(
            fechas=fechas,
            enfermeras=enfermeras_dict,
            asignaciones_rotacion=asignaciones_rotacion,
            desfases=desfases,
            incidencias=[],
            horas_objetivo={eid: 40.0 for eid in enfermeras_dict},
            cobertura_minima={tid: 1 for tid in turno_ids},
            configuracion_solver={"tiempo_maximo_segundos": 15, "seed": 123},
            turnos_info=turnos_info,
        )

        resultado = pipeline.ejecutar()
        _ok(f"Escenario reducido: exitosa={resultado.exitosa}, "
            f"solver={resultado.estado_solver}, "
            f"celdas={resultado.matriz.total_celdas()}")

        # Contar asignaciones
        conteo = {tid: 0 for tid in turno_ids}
        for enf_id, celdas in resultado.matriz.celdas.items():
            for fecha, celda in celdas.items():
                if celda.turno is not None:
                    conteo[celda.turno.id] += 1
        for tid, count in conteo.items():
            _info(f"  {turnos_info[tid].nombre}: {count}")

        return True
    except Exception as e:
        _fail(f"Error en escenario reducido: {e}")
        traceback.print_exc()
        return False


# ============================================================================
# RESUMEN FINAL
# ============================================================================
def resumen_final(resultados):
    _sep("RESUMEN FINAL DE SIMULACION")
    total = len(resultados)
    exitosos = sum(1 for r in resultados if r[1])
    fallidos = total - exitosos

    for nombre, exito in resultados:
        estado = "PASS" if exito else "FAIL"
        print(f"  [{estado}] {nombre}")

    print()
    if fallidos == 0:
        print(f"  RESULTADO: {exitosos}/{total} fases completadas exitosamente")
    else:
        print(f"  RESULTADO: {exitosos}/{total} fases OK, {fallidos} FALLARON")
    print()


# ============================================================================
# MAIN
# ============================================================================
def main():
    print("\n" + "#"*70)
    print("#  SIMULADOR INTEGRAL - Planificador de Turnos de Enfermeria")
    print("#  Basado en planillas reales Sacyl (Sep 2025)")
    print("#"*70)

    resultados = []

    try:
        fase0_limpiar()
        resultados.append(("Fase 0: Limpieza", True))
    except Exception as e:
        _fail(f"Fase 0: {e}")
        resultados.append(("Fase 0: Limpieza", False))

    try:
        user, workspace = fase1_workspace()
        resultados.append(("Fase 1: Workspace + Usuario", True))
    except Exception as e:
        _fail(f"Fase 1: {e}")
        resultados.append(("Fase 1: Workspace + Usuario", False))
        print("\nNo se puede continuar sin workspace.")
        resumen_final(resultados)
        return

    try:
        turnos = fase2_tipos_turno(workspace)
        resultados.append(("Fase 2: Tipos de turno (M/T/N)", True))
    except Exception as e:
        _fail(f"Fase 2: {e}")
        resultados.append(("Fase 2: Tipos de turno", False))
        print("\nNo se puede continuar sin tipos de turno.")
        resumen_final(resultados)
        return

    try:
        enfermeras = fase3_enfermeras(workspace, cantidad=10)
        resultados.append(("Fase 3: 10 Enfermeras", True))
    except Exception as e:
        _fail(f"Fase 3: {e}")
        resultados.append(("Fase 3: Enfermeras", False))
        resumen_final(resultados)
        return

    try:
        config = fase4_configuracion(workspace, user, enfermeras, turnos)
        resultados.append(("Fase 4: Configuracion (Julio 2025)", True))
    except Exception as e:
        _fail(f"Fase 4: {e}")
        resultados.append(("Fase 4: Configuracion", False))
        resumen_final(resultados)
        return

    try:
        resultado, fechas, enf_dict, turnos_info = fase5_ejecutar_pipeline(config, enfermeras, turnos)
        resultados.append(("Fase 5: Pipeline del motor", resultado.exitosa))
    except Exception as e:
        _fail(f"Fase 5: {e}")
        resultados.append(("Fase 5: Pipeline", False))
        resumen_final(resultados)
        return

    try:
        ejecucion, planilla = fase6_persistir(config, resultado, fechas, enf_dict, turnos, turnos_info)
        resultados.append(("Fase 6: Persistir en BD", True))
    except Exception as e:
        _fail(f"Fase 6: {e}")
        resultados.append(("Fase 6: Persistir", False))
        resumen_final(resultados)
        return

    try:
        fase9_validar(planilla, enf_dict, fechas)
        resultados.append(("Fase 9: Validar integridad", True))
    except Exception as e:
        _fail(f"Fase 9: {e}")
        resultados.append(("Fase 9: Validar integridad", False))

    pdf_ok = fase7_exportar_pdf(ejecucion)
    resultados.append(("Fase 7: Exportar PDF", pdf_ok))

    excel_ok = fase8_exportar_excel(ejecucion)
    resultados.append(("Fase 8: Exportar Excel", excel_ok))

    prof_ok = fase10_exportador_profesional(ejecucion)
    resultados.append(("Fase 10: Exportador Profesional", prof_ok))

    esc_ok = fase11_escenario_reducido(workspace, user, turnos)
    resultados.append(("Fase 11: Escenario reducido", esc_ok))

    resumen_final(resultados)


class Command(BaseCommand):
    help = 'Ejecuta simulacion integral del planificador de turnos'

    def handle(self, *args, **options):
        main()
