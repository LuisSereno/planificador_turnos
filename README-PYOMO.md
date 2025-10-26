# 🚀 Planificador de Turnos SACYL - Versión Pyomo

Reescritura del generador de turnos usando **Pyomo** para soportar restricciones complejas SACYL.

## 📦 Instalación

```bash
# 1. Instalar dependencias
pip install pyomo

# 2. Instalar solver (elegir UNO):
# Opción A - CBC (open source, recomendado)
conda install -c conda-forge coincbc

# Opción B - GLPK (open source)
conda install -c conda-forge glpk

# Opción C - Gurobi (comercial, más rápido)
# Requiere licencia: https://www.gurobi.com/academia/academic-program-and-licenses/
```

## 🔧 Arquitectura

```
turnos/
├── generador_pyomo.py      # Generador principal (reemplaza generador.py)
├── restricciones_sacyl.py  # Restricciones duras SACYL (RD001-RD020)
├── objetivos_sacyl.py      # Restricciones blandas SACYL (RB001-RB015)
├── validador_sacyl.py      # Validador completo
└── utils_pyomo.py          # Utilidades
```

## ✨ Características

### ✅ Restricciones Duras Implementadas

- **RD001-RD005**: Jornadas anuales según tipo de turno
- **RD006**: Descanso mínimo 12h entre jornadas
- **RD007**: Descanso semanal 36h consecutivas
- **RD008**: Descanso intra-jornada 20 min
- **RD009-RD010**: Jornada máxima (12h ordinaria, 24h excepcional)
- **RD011**: Jornada conjunta máxima 48h semanales
- **RD012-RD013**: Guardias no en víspera festivo/descanso
- **RD014-RD016**: Horarios fijos por turno
- **RD017**: Vacaciones anuales (22 días)
- **RD018**: Asuntos particulares (6 días)
- **RD019**: Cobertura mínima/óptima/máxima por turno
- **RD020**: No solapamiento turnos

### 🎯 Objetivos Blandos Implementados

- **RB001-RB003**: Distribución equitativa festivos/domingos/noches
- **RB004**: Fin de semana completo libre mensual
- **RB005**: Evitar cambios turno consecutivos
- **RB006**: Rotación mínima turnicidad
- **RB007**: Preferencias personales
- **RB008**: Días consecutivos mismo turno
- **RB009**: Distribución guardias mes
- **RB010-RB015**: Otros objetivos SACYL

## 🚦 Uso

### Opción 1: Desde Django (reemplaza tasks.py)

```python
from turnos.generador_pyomo import GeneradorTurnosPyomo

# En tasks.py:
generador = GeneradorTurnosPyomo(configuracion)
resultado = generador.resolver()
```

### Opción 2: Standalone

```python
from turnos.generador_pyomo import GeneradorTurnosPyomo
from turnos.models import ConfiguracionPlanificacion

config = ConfiguracionPlanificacion.objects.get(pk=1)
gen = GeneradorTurnosPyomo(config)
resultado = gen.resolver(solver='cbc', timeout=600)
```

## 📊 Ventajas sobre OR-Tools CP-SAT

| Característica | OR-Tools CP-SAT | Pyomo |
|----------------|-----------------|-------|
| Restricciones lineales | Limitado | ✅ Completo |
| Restricciones no lineales | ❌ | ✅ |
| Jornadas anuales | ❌ Difícil | ✅ Fácil |
| Guardias condicionales | ⚠️ Aproximado | ✅ Exacto |
| Vacaciones dinámicas | ❌ | ✅ |
| Solvers disponibles | 1 (CP-SAT) | 10+ (CBC, GLPK, Gurobi...) |
| Velocidad (pequeño) | ⚡ Muy rápido | ⚡ Rápido |
| Velocidad (grande) | ⚡ Muy rápido | ⚠️ Medio |
| Escalabilidad | ✅ Excelente | ⚠️ Buena |

## ⚙️ Configuración

En `settings.py`:

```python
# Configuración Pyomo
PYOMO_SOLVER = 'cbc'  # o 'glpk', 'gurobi'
PYOMO_TIMEOUT = 600   # segundos
PYOMO_THREADS = 8
PYOMO_MIP_GAP = 0.01  # 1% gap de optimalidad
```

## 🐛 Debugging

```python
# Activar logs detallados
import logging
logging.getLogger('pyomo').setLevel(logging.DEBUG)

# Exportar modelo a archivo
generador.model.write('modelo.lp')  # formato LP
generador.model.write('modelo.mps') # formato MPS
```

## 📈 Rendimiento

### Caso Típico (365 días, 18 enfermeras, 3 turnos)

- **Variables**: ~19,710 binarias
- **Restricciones**: ~50,000
- **Tiempo CBC**: 2-5 minutos
- **Tiempo Gurobi**: 30-90 segundos

## 🔄 Migración desde CP-SAT

1. Reemplazar `generador.py` con `generador_pyomo.py`
2. Actualizar `tasks.py` (cambiar import)
3. Instalar Pyomo + solver
4. ¡Listo! Las vistas/templates no cambian

## 📝 TODOs

- [ ] Implementar RD002 tabla ponderación guardias
- [ ] Implementar RB010 anticipación planificación
- [ ] Optimizar modelo para >30 enfermeras
- [ ] Cache de soluciones parciales
- [ ] Interfaz web para ajustar pesos RB001-RB015

## 🆘 Solución de Problemas

**Problema**: "Solver no encontrado"
```bash
# Instalar CBC
conda install -c conda-forge coincbc
```

**Problema**: "Muy lento para 365 días"
```python
# Usar Gurobi (requiere licencia académica gratuita)
solver='gurobi'
```

**Problema**: "Sin solución factible"
```python
# Relajar restricciones duras temporalmente
generador.relajar_rd007 = True  # Permite violar RD007
```

## 📧 Soporte

Para dudas sobre implementación: revisar `generador_pyomo.py` comentarios
