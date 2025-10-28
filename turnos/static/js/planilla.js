/**
 * planilla.js - Renderizador de planilla de turnos
 * Construye la tabla de turnos dinámicamente desde los datos JSON
 */

class PlanillaRenderer {
    constructor(containerId = 'planilla-table') {
        this.container = document.getElementById(containerId);
        this.data = null;
        this.init();
    }

    /**
     * Inicializar - buscar datos en el DOM
     */
    init() {
        // Buscar datos JSON en el DOM (generado por Django)
        const dataElement = document.querySelector('[data-planilla-json]');
        if (!dataElement) {
            console.warn('No se encontró elemento con data-planilla-json');
            return;
        }

        try {
            this.data = JSON.parse(dataElement.textContent);
            console.log('✓ Datos de planilla cargados:', this.data);
            this.render();
        } catch (error) {
            console.error('✗ Error al parsear JSON de planilla:', error);
        }
    }

    /**
     * Renderizar la tabla completa
     */
    render() {
        if (!this.data || !this.container) return;

        const { dias, enfermeras_turnos } = this.data;

        if (!dias || !enfermeras_turnos) {
            console.error('✗ Faltan datos: dias o enfermeras_turnos');
            return;
        }

        console.log(`Renderizando tabla: ${dias.length} días, ${enfermeras_turnos.length} enfermeras`);

        // Limpiar contenedor
        this.container.innerHTML = '';

        // Crear tabla
        const table = document.createElement('table');
        table.className = 'table table-bordered table-sm';

        // Crear encabezado
        const thead = this.createHeader(dias);
        table.appendChild(thead);

        // Crear cuerpo
        const tbody = this.createBody(dias, enfermeras_turnos);
        table.appendChild(tbody);

        // Agregar tabla al contenedor
        const wrapper = document.createElement('div');
        wrapper.className = 'table-responsive';
        wrapper.appendChild(table);
        this.container.appendChild(wrapper);

        console.log('✓ Tabla renderizada exitosamente');
    }

    /**
     * Crear encabezado de la tabla
     */
    createHeader(dias) {
        const thead = document.createElement('thead');
        thead.className = 'table-light';

        const tr = document.createElement('tr');

        // Columna de enfermeras
        const thEnfermera = document.createElement('th');
        thEnfermera.style.position = 'sticky';
        thEnfermera.style.left = '0';
        thEnfermera.style.background = 'white';
        thEnfermera.style.zIndex = '10';
        thEnfermera.textContent = 'Enfermera';
        tr.appendChild(thEnfermera);

        // Columnas de días
        dias.forEach(dia => {
            const th = document.createElement('th');
            th.className = 'text-center';
            th.style.minWidth = '100px';
            
            const fecha = new Date(dia.fecha + 'T00:00:00'); // Asegurar que se interprete como fecha local
            const dia_mes = fecha.getDate().toString().padStart(2, '0');
            const mes = (fecha.getMonth() + 1).toString().padStart(2, '0');
            const dia_nombre = this.getNombreDia(fecha);

            th.innerHTML = `${dia_mes}/${mes}<br><small>${dia_nombre}</small>`;
            tr.appendChild(th);
        });

        thead.appendChild(tr);
        return thead;
    }

    /**
     * Crear cuerpo de la tabla
     */
    createBody(dias, enfermeras_turnos) {
        const tbody = document.createElement('tbody');

        enfermeras_turnos.forEach(enfermera_data => {
            const tr = document.createElement('tr');

            // Columna de nombre de enfermera
            const tdEnfermera = document.createElement('td');
            tdEnfermera.style.position = 'sticky';
            tdEnfermera.style.left = '0';
            tdEnfermera.style.background = 'white';
            tdEnfermera.style.fontWeight = 'bold';
            tdEnfermera.style.zIndex = '5';
            tdEnfermera.textContent = enfermera_data.enfermera.nombre;
            tr.appendChild(tdEnfermera);

            // Crear un mapa de turnos por fecha para esta enfermera
            const turnosPorFecha = new Map();
            enfermera_data.turnos.forEach(turno => {
                turnosPorFecha.set(turno.fecha, turno);
            });

            // Columnas de turnos, una por cada día en el header
            dias.forEach(dia => {
                const td = document.createElement('td');
                td.className = 'text-center';

                const turno_data = turnosPorFecha.get(dia.fecha);

                if (turno_data) {
                    if (turno_data.es_libre) {
                        // Día libre
                        const badge = document.createElement('span');
                        badge.className = 'badge bg-secondary';
                        badge.textContent = 'LIBRE';
                        td.appendChild(badge);
                    } else if (turno_data.turno) {
                        // Turno asignado
                        const badge = document.createElement('span');
                        badge.className = `badge bg-${turno_data.turno_color}`;
                        badge.textContent = turno_data.turno.nombre;
                        td.appendChild(badge);

                        // Horario
                        const br = document.createElement('br');
                        td.appendChild(br);

                        const horario = document.createElement('small');
                        horario.className = 'text-muted';
                        horario.textContent = `${turno_data.horario}`;
                        td.appendChild(horario);
                    }
                } else {
                    // Si no hay turno para esa fecha, se asume libre
                    const badge = document.createElement('span');
                    badge.className = 'badge bg-light text-dark';
                    badge.textContent = '-';
                    td.appendChild(badge);
                }

                tr.appendChild(td);
            });

            tbody.appendChild(tr);
        });

        return tbody;
    }

    /**
     * Obtener nombre corto del día
     */
    getNombreDia(fecha) {
        const dias = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
        return dias[fecha.getUTCDay()]; // Usar getUTCDay para evitar problemas de zona horaria
    }

    /**
     * Exportar tabla a CSV
     */
    exportarCSV() {
        if (!this.data) return;

        const { dias, enfermeras_turnos } = this.data;
        let csv = 'Enfermera,' + dias.map(d => d.fecha).join(',') + '\n';

        enfermeras_turnos.forEach(enfermera_data => {
            const turnosPorFecha = new Map();
            enfermera_data.turnos.forEach(turno => {
                turnosPorFecha.set(turno.fecha, turno);
            });

            let row = enfermera_data.enfermera.nombre;
            dias.forEach(dia => {
                const turno = turnosPorFecha.get(dia.fecha);
                if (turno) {
                    row += ',' + (turno.es_libre ? 'LIBRE' : (turno.turno ? turno.turno.nombre : '-'));
                } else {
                    row += ',-';
                }
            });
            csv += row + '\n';
        });

        this.descargarArchivo(csv, 'planilla.csv', 'text/csv;charset=utf-8;');
    }

    /**
     * Descargar archivo
     */
    descargarArchivo(contenido, nombre, tipo) {
        const blob = new Blob(['\uFEFF' + contenido], { type: tipo }); // BOM para Excel
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = nombre;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    const renderer = new PlanillaRenderer('planilla-table');

    // Opcional: añadir listeners a botones de exportación
    const exportCsvButton = document.getElementById('export-csv-btn');
    if (exportCsvButton) {
        exportCsvButton.addEventListener('click', () => renderer.exportarCSV());
    }
});
