/**
 * AJAX-HELPERS.JS - Funciones de Ayuda para AJAX
 */

(function() {
    'use strict';

    const AjaxHelper = {
        /**
         * Obtiene CSRF token
         */
        getCSRFToken: function() {
            return document.querySelector('[name=csrfmiddlewaretoken]')?.value
                || document.querySelector('meta[name="csrf-token"]')?.content
                || this.getCookie('csrftoken');
        },

        /**
         * Obtiene cookie
         */
        getCookie: function(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        },

        /**
         * Petición GET genérica
         */
        get: async function(url, params = {}) {
            try {
                const urlParams = new URLSearchParams(params);
                const fullUrl = params ? `${url}?${urlParams.toString()}` : url;

                const response = await fetch(fullUrl, {
                    method: 'GET',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                console.error('Error en petición GET:', error);
                throw error;
            }
        },

        /**
         * Petición POST genérica
         */
        post: async function(url, data = {}) {
            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify(data)
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                console.error('Error en petición POST:', error);
                throw error;
            }
        },

        /**
         * Petición PUT genérica
         */
        put: async function(url, data = {}) {
            try {
                const response = await fetch(url, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify(data)
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                console.error('Error en petición PUT:', error);
                throw error;
            }
        },

        /**
         * Petición DELETE genérica
         */
        delete: async function(url) {
            try {
                const response = await fetch(url, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': this.getCSRFToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin'
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                console.error('Error en petición DELETE:', error);
                throw error;
            }
        },

        /**
         * Envío de formulario con FormData
         */
        submitForm: async function(form, url = null) {
            try {
                const formData = new FormData(form);
                const submitUrl = url || form.action;

                const response = await fetch(submitUrl, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': this.getCSRFToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    credentials: 'same-origin',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                return await response.json();
            } catch (error) {
                console.error('Error en envío de formulario:', error);
                throw error;
            }
        },

        /**
         * Carga una URL en un contenedor
         */
        loadContent: async function(url, containerId) {
            try {
                const response = await fetch(url, {
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const html = await response.text();
                const container = document.getElementById(containerId);

                if (container) {
                    container.innerHTML = html;
                }

                return html;
            } catch (error) {
                console.error('Error al cargar contenido:', error);
                throw error;
            }
        },

        /**
         * Polling (consulta periódica)
         */
        poll: function(url, callback, interval = 5000, maxAttempts = 60) {
            let attempts = 0;

            const pollInterval = setInterval(async () => {
                attempts++;

                try {
                    const data = await this.get(url);
                    const shouldContinue = callback(data, attempts);

                    if (!shouldContinue || attempts >= maxAttempts) {
                        clearInterval(pollInterval);
                    }
                } catch (error) {
                    console.error('Error en polling:', error);
                    clearInterval(pollInterval);
                }
            }, interval);

            return pollInterval;
        }
    };

    // ============================================
    // FUNCIONES ESPECÍFICAS DE LA APP
    // ============================================

    /**
     * Obtiene estado de ejecución
     */
    async function obtenerEstadoEjecucion(ejecucionId) {
        return await AjaxHelper.get(`/turnos/ajax/ejecucion/${ejecucionId}/estado/`);
    }

    /**
     * Consulta estado de ejecución periódicamente
     */
    function monitorizarEjecucion(ejecucionId, onUpdate, onComplete) {
        return AjaxHelper.poll(
            `/turnos/ajax/ejecucion/${ejecucionId}/estado/`,
            (data, attempts) => {
                onUpdate(data);

                if (data.estado === 'COMPLETADA' || data.estado === 'ERROR') {
                    onComplete(data);
                    return false; // Detener polling
                }

                return true; // Continuar polling
            },
            5000, // Cada 5 segundos
            120   // Máximo 10 minutos
        );
    }

    /**
     * Busca enfermeras
     */
    async function buscarEnfermeras(termino) {
        return await AjaxHelper.get('/turnos/ajax/enfermeras/buscar/', { q: termino });
    }

    /**
     * Valida configuración
     */
    async function validarConfiguracion(configuracionId) {
        return await AjaxHelper.post(`/turnos/ajax/configuracion/${configuracionId}/validar/`);
    }

    /**
     * Duplica configuración
     */
    async function duplicarConfiguracion(configuracionId) {
        return await AjaxHelper.post(`/turnos/ajax/configuracion/${configuracionId}/duplicar/`);
    }

    /**
     * Exporta ejecución
     */
    function exportarEjecucion(ejecucionId, formato) {
        const url = `/turnos/ejecuciones/${ejecucionId}/exportar/${formato}/`;
        window.location.href = url;
    }

    /**
     * Obtiene estadísticas del dashboard
     */
    async function obtenerEstadisticasDashboard() {
        return await AjaxHelper.get('/turnos/ajax/dashboard/estadisticas/');
    }

    /**
     * Guarda preferencias de usuario
     */
    async function guardarPreferencias(preferencias) {
        return await AjaxHelper.post('/turnos/ajax/usuario/preferencias/', preferencias);
    }

    // ============================================
    // EXPORTAR A GLOBAL
    // ============================================
    window.AjaxHelper = AjaxHelper;
    window.obtenerEstadoEjecucion = obtenerEstadoEjecucion;
    window.monitorizarEjecucion = monitorizarEjecucion;
    window.buscarEnfermeras = buscarEnfermeras;
    window.validarConfiguracion = validarConfiguracion;
    window.duplicarConfiguracion = duplicarConfiguracion;
    window.exportarEjecucion = exportarEjecucion;
    window.obtenerEstadisticasDashboard = obtenerEstadisticasDashboard;
    window.guardarPreferencias = guardarPreferencias;

})();
