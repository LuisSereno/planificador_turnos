/**
 * RESTRICCIONES.JS - Gestión Dinámica de Restricciones
 */

(function() {
    'use strict';

    // Estado global de restricciones
    const restriccionesState = {
        duras: [],
        blandas: []
    };

    // ============================================
    // DEFINICIONES DE RESTRICCIONES DURAS
    // ============================================
    const restriccionesDurasDefiniciones = {
        'cobertura_minima': {
            nombre: 'Cobertura Mínima',
            descripcion: 'Cada turno debe tener un número mínimo de enfermeras',
            icono: 'fa-users',
            parametros: {
                'incremento_fines_semana': {
                    tipo: 'number',
                    label: 'Incremento fines de semana',
                    default: 1,
                    min: 0,
                    max: 5,
                    help: 'Enfermeras adicionales requeridas en fines de semana'
                }
            }
        },
        'cobertura_maxima': {
            nombre: 'Cobertura Máxima',
            descripcion: 'Cada turno no debe exceder el número máximo de enfermeras',
            icono: 'fa-user-minus',
            parametros: {}
        },
        'un_turno_por_dia': {
            nombre: 'Un Turno por Día',
            descripcion: 'Una enfermera no puede trabajar más de un turno al día',
            icono: 'fa-clock',
            parametros: {}
        },
        'descanso_minimo': {
            nombre: 'Descanso Mínimo',
            descripcion: 'Tiempo mínimo de descanso entre turnos',
            icono: 'fa-bed',
            parametros: {
                'horas_descanso': {
                    tipo: 'number',
                    label: 'Horas de descanso',
                    default: 12,
                    min: 8,
                    max: 24,
                    help: 'Horas mínimas entre el fin de un turno y el inicio del siguiente'
                }
            }
        },
        'horas_semanales_max': {
            nombre: 'Máximo Horas Semanales',
            descripcion: 'Máximo de turnos que una enfermera puede trabajar por semana',
            icono: 'fa-calendar-week',
            parametros: {
                'max_turnos_semana': {
                    tipo: 'number',
                    label: 'Máximo turnos por semana',
                    default: 5,
                    min: 1,
                    max: 7,
                    help: 'Número máximo de turnos por semana'
                }
            }
        },
        'horas_semanales_min': {
            nombre: 'Mínimo Horas Semanales',
            descripcion: 'Mínimo de turnos que una enfermera debe trabajar por semana',
            icono: 'fa-calendar-check',
            parametros: {
                'min_turnos_semana': {
                    tipo: 'number',
                    label: 'Mínimo turnos por semana',
                    default: 3,
                    min: 0,
                    max: 7,
                    help: 'Número mínimo de turnos por semana'
                }
            }
        },
        'turnos_consecutivos_max': {
            nombre: 'Máximo Turnos Consecutivos',
            descripcion: 'Máximo de días consecutivos trabajando',
            icono: 'fa-calendar-days',
            parametros: {
                'max_dias_consecutivos': {
                    tipo: 'number',
                    label: 'Máximo días consecutivos',
                    default: 4,
                    min: 1,
                    max: 10,
                    help: 'Días máximos trabajando seguidos'
                }
            }
        },
        'incompatibilidades': {
            nombre: 'Incompatibilidades',
            descripcion: 'Enfermeras que no pueden trabajar juntas',
            icono: 'fa-user-slash',
            parametros: {}
        },
        'disponibilidad_parcial': {
            nombre: 'Disponibilidad Parcial',
            descripcion: 'Enfermeras disponibles solo en ciertos turnos',
            icono: 'fa-user-clock',
            parametros: {}
        },
        'dias_libres_obligatorios': {
            nombre: 'Días Libres Obligatorios',
            descripcion: 'Días específicos que deben estar libres',
            icono: 'fa-calendar-xmark',
            parametros: {}
        },
        'dias_libres_minimos_semana': {
            nombre: 'Días Libres Mínimos por Semana',
            descripcion: 'Mínimo de días libres por semana',
            icono: 'fa-umbrella-beach',
            parametros: {
                'min_dias_libres_semana': {
                    tipo: 'number',
                    label: 'Mínimo días libres',
                    default: 2,
                    min: 0,
                    max: 4,
                    help: 'Días libres mínimos por semana'
                }
            }
        },
        'turnos_nocturnos_consecutivos_max': {
            nombre: 'Máximo Noches Consecutivas',
            descripcion: 'Máximo de turnos nocturnos consecutivos',
            icono: 'fa-moon',
            parametros: {
                'max_noches_consecutivas': {
                    tipo: 'number',
                    label: 'Máximo noches consecutivas',
                    default: 3,
                    min: 1,
                    max: 7,
                    help: 'Noches máximas trabajando seguidas'
                }
            }
        },
        'fines_semana_max': {
            nombre: 'Máximo Fines de Semana',
            descripcion: 'Máximo de fines de semana trabajados',
            icono: 'fa-calendar-plus',
            parametros: {
                'max_fines_semana': {
                    tipo: 'number',
                    label: 'Máximo fines de semana',
                    default: 1,
                    min: 0,
                    max: 4,
                    help: 'Fines de semana máximos trabajando en el período'
                }
            }
        }
    };

    // ============================================
    // DEFINICIONES DE RESTRICCIONES BLANDAS
    // ============================================
    const restriccionesBlandasDefiniciones = {
        'preferencias_turno': {
            nombre: 'Preferencias de Turno',
            descripcion: 'Respetar preferencias de turno de enfermeras',
            icono: 'fa-heart',
            peso_default: 3.0
        },
        'preferencias_dias_libres': {
            nombre: 'Preferencias de Días Libres',
            descripcion: 'Respetar preferencias de días libres',
            icono: 'fa-calendar-heart',
            peso_default: 2.0
        },
        'distribucion_equitativa_noches': {
            nombre: 'Distribución Equitativa de Noches',
            descripcion: 'Distribuir turnos nocturnos equitativamente',
            icono: 'fa-balance-scale',
            peso_default: 5.0
        },
        'minimizar_cambios_turno': {
            nombre: 'Minimizar Cambios de Turno',
            descripcion: 'Evitar cambios frecuentes de turno',
            icono: 'fa-arrows-rotate',
            peso_default: 1.5
        },
        'evitar_turnos_aislados': {
            nombre: 'Evitar Turnos Aislados',
            descripcion: 'Preferir bloques de turnos consecutivos',
            icono: 'fa-object-group',
            peso_default: 2.0
        },
        'cumplir_demanda_optima': {
            nombre: 'Cumplir Demanda Óptima',
            descripcion: 'Ajustarse a la demanda óptima, no solo mínima',
            icono: 'fa-bullseye',
            peso_default: 1.0
        },
        'balanceo_carga_total': {
            nombre: 'Balanceo de Carga Total',
            descripcion: 'Distribuir carga de trabajo equitativamente',
            icono: 'fa-chart-pie',
            peso_default: 4.0
        }
    };

    // ============================================
    // FUNCIONES DE RESTRICCIONES DURAS
    // ============================================
    const RestriccionesDuras = {
        agregarRestriccion: function() {
            const contenedor = document.getElementById('restricciones-duras-contenedor');
            if (!contenedor) return;

            const index = restriccionesState.duras.length;

            const html = `
                <div class="card mb-3 restriccion-dura restriccion-card" data-index="${index}">
                    <div class="card-header d-flex justify-content-between align-items-center bg-danger bg-opacity-10">
                        <h6 class="mb-0">
                            <i class="fas fa-exclamation-triangle text-danger me-2"></i>
                            Restricción Dura #${index + 1}
                        </h6>
                        <button type="button" class="btn btn-sm btn-danger" onclick="RestriccionesDuras.eliminarRestriccion(${index})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-8">
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Tipo de Restricción</label>
                                    <select class="form-select restriccion-tipo-select" 
                                            data-index="${index}" 
                                            onchange="RestriccionesDuras.actualizarParametros(${index})"
                                            required>
                                        <option value="">Seleccionar...</option>
                                        ${Object.keys(restriccionesDurasDefiniciones).map(key => {
                                            const def = restriccionesDurasDefiniciones[key];
                                            return `<option value="${key}">
                                                <i class="fas ${def.icono}"></i> ${def.nombre}
                                            </option>`;
                                        }).join('')}
                                    </select>
                                    <small class="form-text text-muted restriccion-descripcion"></small>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Activa</label>
                                    <div class="form-check form-switch">
                                        <input class="form-check-input" type="checkbox" checked 
                                               data-index="${index}" name="restriccion_dura_activa_${index}">
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="parametros-contenedor" data-index="${index}">
                            <!-- Parámetros dinámicos -->
                        </div>
                    </div>
                </div>
            `;

            contenedor.insertAdjacentHTML('beforeend', html);
            restriccionesState.duras.push({});

            this.actualizarContador();
        },

        actualizarParametros: function(index) {
            const select = document.querySelector(`.restriccion-tipo-select[data-index="${index}"]`);
            if (!select) return;

            const tipo = select.value;
            if (!tipo) return;

            const definicion = restriccionesDurasDefiniciones[tipo];
            const descripcionEl = select.closest('.card-body').querySelector('.restriccion-descripcion');
            descripcionEl.textContent = definicion.descripcion;

            const parametrosContenedor = document.querySelector(`.parametros-contenedor[data-index="${index}"]`);
            parametrosContenedor.innerHTML = '';

            if (Object.keys(definicion.parametros).length > 0) {
                let html = '<div class="mt-3 p-3 bg-light rounded"><h6 class="mb-3">Parámetros</h6><div class="row">';

                for (const [key, param] of Object.entries(definicion.parametros)) {
                    html += `
                        <div class="col-md-6 mb-3">
                            <label class="form-label fw-bold">${param.label}</label>
                            <input type="${param.tipo}" 
                                   class="form-control" 
                                   name="restriccion_dura_param_${index}_${key}"
                                   value="${param.default}"
                                   min="${param.min || ''}"
                                   max="${param.max || ''}"
                                   step="${param.step || ''}">
                            ${param.help ? `<small class="form-text text-muted">${param.help}</small>` : ''}
                        </div>
                    `;
                }

                html += '</div></div>';
                parametrosContenedor.innerHTML = html;
            }

            restriccionesState.duras[index] = {
                tipo: tipo,
                activa: true,
                parametros: {}
            };
        },

        eliminarRestriccion: function(index) {
            const elemento = document.querySelector(`.restriccion-dura[data-index="${index}"]`);
            if (elemento && confirm('¿Eliminar esta restricción dura?')) {
                elemento.remove();
                restriccionesState.duras.splice(index, 1);
                this.actualizarContador();
            }
        },

        actualizarContador: function() {
            const contador = document.getElementById('contador-restricciones-duras');
            if (contador) {
                contador.textContent = restriccionesState.duras.length;
            }
        }
    };

    // ============================================
    // FUNCIONES DE RESTRICCIONES BLANDAS
    // ============================================
    const RestriccionesBlandas = {
        agregarRestriccion: function() {
            const contenedor = document.getElementById('restricciones-blandas-contenedor');
            if (!contenedor) return;

            const index = restriccionesState.blandas.length;

            const html = `
                <div class="card mb-3 restriccion-blanda restriccion-card" data-index="${index}">
                    <div class="card-header d-flex justify-content-between align-items-center bg-warning bg-opacity-10">
                        <h6 class="mb-0">
                            <i class="fas fa-balance-scale text-warning me-2"></i>
                            Restricción Blanda #${index + 1}
                        </h6>
                        <button type="button" class="btn btn-sm btn-warning" onclick="RestriccionesBlandas.eliminarRestriccion(${index})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Tipo de Restricción</label>
                                    <select class="form-select restriccion-blanda-tipo-select" 
                                            data-index="${index}" 
                                            onchange="RestriccionesBlandas.actualizar(${index})"
                                            required>
                                        <option value="">Seleccionar...</option>
                                        ${Object.keys(restriccionesBlandasDefiniciones).map(key => {
                                            const def = restriccionesBlandasDefiniciones[key];
                                            return `<option value="${key}">${def.nombre}</option>`;
                                        }).join('')}
                                    </select>
                                    <small class="form-text text-muted restriccion-blanda-descripcion"></small>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Peso (Importancia)</label>
                                    <input type="range" class="form-range restriccion-blanda-peso-range" 
                                           data-index="${index}" 
                                           min="0" max="10" step="0.5" value="1.0"
                                           oninput="RestriccionesBlandas.actualizarPeso(${index}, this.value)">
                                    <input type="number" class="form-control form-control-sm mt-2 restriccion-blanda-peso" 
                                           data-index="${index}" 
                                           min="0" max="10" step="0.5" value="1.0"
                                           name="restriccion_blanda_peso_${index}"
                                           onchange="RestriccionesBlandas.sincronizarPeso(${index}, this.value)">
                                    <small class="form-text text-muted">0 = Baja, 10 = Alta</small>
                                </div>
                            </div>
                            <div class="col-md-3">
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Activa</label>
                                    <div class="form-check form-switch">
                                        <input class="form-check-input" type="checkbox" checked 
                                               data-index="${index}" name="restriccion_blanda_activa_${index}">
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            contenedor.insertAdjacentHTML('beforeend', html);
            restriccionesState.blandas.push({});

            this.actualizarContador();
        },

        actualizar: function(index) {
            const select = document.querySelector(`.restriccion-blanda-tipo-select[data-index="${index}"]`);
            if (!select) return;

            const tipo = select.value;
            if (!tipo) return;

            const definicion = restriccionesBlandasDefiniciones[tipo];
            const descripcionEl = select.closest('.card-body').querySelector('.restriccion-blanda-descripcion');
            descripcionEl.textContent = definicion.descripcion;

            const pesoInput = document.querySelector(`.restriccion-blanda-peso[data-index="${index}"]`);
            const pesoRange = document.querySelector(`.restriccion-blanda-peso-range[data-index="${index}"]`);
            pesoInput.value = definicion.peso_default;
            pesoRange.value = definicion.peso_default;

            restriccionesState.blandas[index] = {
                tipo: tipo,
                activa: true,
                peso: definicion.peso_default
            };
        },

        actualizarPeso: function(index, valor) {
            const pesoInput = document.querySelector(`.restriccion-blanda-peso[data-index="${index}"]`);
            if (pesoInput) {
                pesoInput.value = valor;
            }
        },

        sincronizarPeso: function(index, valor) {
            const pesoRange = document.querySelector(`.restriccion-blanda-peso-range[data-index="${index}"]`);
            if (pesoRange) {
                pesoRange.value = valor;
            }
        },

        eliminarRestriccion: function(index) {
            const elemento = document.querySelector(`.restriccion-blanda[data-index="${index}"]`);
            if (elemento && confirm('¿Eliminar esta restricción blanda?')) {
                elemento.remove();
                restriccionesState.blandas.splice(index, 1);
                this.actualizarContador();
            }
        },

        actualizarContador: function() {
            const contador = document.getElementById('contador-restricciones-blandas');
            if (contador) {
                contador.textContent = restriccionesState.blandas.length;
            }
        }
    };

    // ============================================
    // SERIALIZACIÓN
    // ============================================
    function serializarRestricciones() {
        // Serializar restricciones duras
        const duras = [];
        document.querySelectorAll('.restriccion-dura').forEach(card => {
            const index = card.dataset.index;
            const tipoSelect = card.querySelector('.restriccion-tipo-select');
            const activaCheck = card.querySelector('input[type="checkbox"]');

            if (!tipoSelect || !tipoSelect.value) return;

            const restriccion = {
                nombre: tipoSelect.value,
                activa: activaCheck.checked,
                parametros: {}
            };

            // Recoger parámetros
            card.querySelectorAll('[name^="restriccion_dura_param_"]').forEach(input => {
                const paramName = input.name.split('_').pop();
                restriccion.parametros[paramName] = input.type === 'number' ? parseFloat(input.value) : input.value;
            });

            duras.push(restriccion);
        });

        // Serializar restricciones blandas
        const blandas = [];
        document.querySelectorAll('.restriccion-blanda').forEach(card => {
            const index = card.dataset.index;
            const tipoSelect = card.querySelector('.restriccion-blanda-tipo-select');
            const pesoInput = card.querySelector('.restriccion-blanda-peso');
            const activaCheck = card.querySelector('input[type="checkbox"]');

            if (!tipoSelect || !tipoSelect.value) return;

            blandas.push({
                nombre: tipoSelect.value,
                activa: activaCheck.checked,
                peso: parseFloat(pesoInput.value),
                parametros: {}
            });
        });

        return { duras, blandas };
    }

    // ============================================
    // VALIDACIÓN
    // ============================================
    function validarRestriccionesFormulario() {
        const { duras, blandas } = serializarRestricciones();

        if (duras.length === 0) {
            alert('Debes añadir al menos una restricción dura');
            return false;
        }

        // Guardar en campos hidden
        const durasInput = document.getElementById('restricciones_duras_json');
        const blandasInput = document.getElementById('restricciones_blandas_json');

        if (durasInput) durasInput.value = JSON.stringify(duras);
        if (blandasInput) blandasInput.value = JSON.stringify(blandas);

        return true;
    }

    // ============================================
    // EXPORTAR A GLOBAL
    // ============================================
    window.RestriccionesDuras = RestriccionesDuras;
    window.RestriccionesBlandas = RestriccionesBlandas;
    window.validarRestriccionesFormulario = validarRestriccionesFormulario;
    window.serializarRestricciones = serializarRestricciones;

    // ============================================
    // INICIALIZACIÓN
    // ============================================
    document.addEventListener('DOMContentLoaded', function() {
        // Configurar botones de agregar restricción
        const btnAgregarDura = document.getElementById('btn-agregar-restriccion-dura');
        if (btnAgregarDura) {
            btnAgregarDura.addEventListener('click', () => RestriccionesDuras.agregarRestriccion());
        }

        const btnAgregarBlanda = document.getElementById('btn-agregar-restriccion-blanda');
        if (btnAgregarBlanda) {
            btnAgregarBlanda.addEventListener('click', () => RestriccionesBlandas.agregarRestriccion());
        }

        console.log('✓ Sistema de restricciones inicializado');
    });

})();
