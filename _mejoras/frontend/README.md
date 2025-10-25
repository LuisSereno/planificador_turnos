# Frontend Mejorado

## Archivos Generados

- static/js/dashboard.js: Graficos Chart.js
- static/css/custom.css: Estilos mejorados

## Instalacion

1. Copiar archivos a:
   - turnos/static/js/dashboard.js
   - turnos/static/css/custom.css

2. Agregar Chart.js al template base:

```html
<script src=\"https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js\"></script>
```

3. Incluir en templates:

```html
{% load static %}
<link rel=\"stylesheet\" href=\"{% static 'css/custom.css' %}\">
<script src=\"{% static 'js/dashboard.js' %}\"></script>
```

## Uso en Templates

Agregar canvas para graficos:

```html
<div class=\"chart-container\">
    <canvas id=\"chartDistribucionTurnos\"></canvas>
</div>
<div class=\"chart-container\">
    <canvas id=\"chartCargaEnfermeras\"></canvas>
</div>

<script>
window.distribucionData = [10, 15, 8, 5];  // Datos desde backend
window.enfermerasData = {{ enfermeras_json|safe }};
</script>
```
