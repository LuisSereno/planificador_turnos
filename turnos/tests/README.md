# Tests Unitarios Generados

## InstalaciÃ³n

1. Copiar archivos de _mejoras/tests/ a turnos/tests/
2. Copiar pytest.ini a la raiz del proyecto
3. Instalar dependencias:

```bash
pip install pytest pytest-django pytest-cov factory-boy
```

## Ejecutar

```bash
# Todos los tests
python -m pytest

# Con cobertura
python -m pytest --cov=turnos --cov-report=html

# Test especifico
python -m pytest turnos/tests/test_models.py
```

## Archivos generados

- conftest.py: Fixtures compartidas
- test_models.py: Tests de modelos
- test_generador.py: Tests del solver
- pytest.ini: Configuracion de pytest
