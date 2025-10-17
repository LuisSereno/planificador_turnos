/**
 * CHARTS.JS - Configuración y Creación de Gráficos con Chart.js
 */

(function() {
    'use strict';

    const ChartHelper = {
        /**
         * Colores del tema
         */
        colors: {
            primary: '#667eea',
            secondary: '#764ba2',
            success: '#28a745',
            danger: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8',
            manana: '#ffc107',
            tarde: '#17a2b8',
            noche: '#6f42c1'
        },

        /**
         * Configuración por defecto
         */
        defaultConfig: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        font: {
                            size: 12,
                            family: "'Inter', sans-serif"
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    padding: 12,
                    titleFont: {
                        size: 14,
                        weight: '600'
                    },
                    bodyFont: {
                        size: 13
                    },
                    cornerRadius: 6
                }
            }
        },

        /**
         * Crea gráfico de barras
         */
        crearGraficoBarras: function(canvasId, labels, datasets, options = {}) {
            const ctx = document.getElementById(canvasId);
            if (!ctx) return null;

            const config = {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: datasets.map(dataset => ({
                        ...dataset,
                        backgroundColor: dataset.backgroundColor || this.colors.primary,
                        borderColor: dataset.borderColor || this.colors.primary,
                        borderWidth: 2,
                        borderRadius: 6
                    }))
                },
                options: {
                    ...this.defaultConfig,
                    ...options,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                stepSize: 1
                            },
                            grid: {
                                display: true,
                                drawBorder: false
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            };

            return new Chart(ctx, config);
        },

        /**
         * Crea gráfico de líneas
         */
        crearGraficoLineas: function(canvasId, labels, datasets, options = {}) {
            const ctx = document.getElementById(canvasId);
            if (!ctx) return null;

            const config = {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: datasets.map(dataset => ({
                        ...dataset,
                        borderColor: dataset.borderColor || this.colors.primary,
                        backgroundColor: dataset.backgroundColor || this.hexToRgba(this.colors.primary, 0.1),
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }))
                },
                options: {
                    ...this.defaultConfig,
                    ...options,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                display: true,
                                drawBorder: false
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            };

            return new Chart(ctx, config);
        },

        /**
         * Crea gráfico circular (pie/donut)
         */
        crearGraficoCircular: function(canvasId, labels, data, options = {}) {
            const ctx = document.getElementById(canvasId);
            if (!ctx) return null;

            const config = {
                type: options.type || 'pie',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
                        backgroundColor: options.colors || [
                            this.colors.primary,
                            this.colors.success,
                            this.colors.warning,
                            this.colors.danger,
                            this.colors.info,
                            this.colors.secondary
                        ],
                        borderWidth: 2,
                        borderColor: '#fff'
                    }]
                },
                options: {
                    ...this.defaultConfig,
                    ...options
                }
            };

            return new Chart(ctx, config);
        },

        /**
         * Gráfico de distribución de turnos por enfermera
         */
        crearGraficoDistribucionEnfermeras: function(canvasId, enfermeras, turnos) {
            const labels = enfermeras.map(e => e.nombre);
            const data = enfermeras.map(e => e.total_turnos || 0);

            return this.crearGraficoBarras(canvasId, labels, [{
                label: 'Turnos Asignados',
                data: data,
                backgroundColor: this.generateGradient(this.colors.primary, this.colors.secondary)
            }]);
        },

        /**
         * Gráfico de cobertura por tipo de turno
         */
        crearGraficoCoberturaTurnos: function(canvasId, turnos) {
            const labels = turnos.map(t => t.nombre);
            const data = turnos.map(t => t.count || 0);
            const colors = [this.colors.manana, this.colors.tarde, this.colors.noche];

            return this.crearGraficoCircular(canvasId, labels, data, {
                type: 'doughnut',
                colors: colors
            });
        },

        /**
         * Gráfico de evolución temporal
         */
        crearGraficoEvolucion: function(canvasId, fechas, series) {
            const datasets = series.map((serie, index) => ({
                label: serie.label,
                data: serie.data,
                borderColor: Object.values(this.colors)[index],
                backgroundColor: this.hexToRgba(Object.values(this.colors)[index], 0.1)
            }));

            return this.crearGraficoLineas(canvasId, fechas, datasets);
        },

        /**
         * Gráfico de tasa de éxito
         */
        crearGraficoTasaExito: function(canvasId, stats) {
            const labels = ['Completadas', 'Fallidas', 'Pendientes'];
            const data = [
                stats.completadas || 0,
                stats.fallidas || 0,
                stats.pendientes || 0
            ];
            const colors = [this.colors.success, this.colors.danger, this.colors.warning];

            return this.crearGraficoCircular(canvasId, labels, data, {
                type: 'doughnut',
                colors: colors
            });
        },

        /**
         * Convierte hex a rgba
         */
        hexToRgba: function(hex, alpha = 1) {
            const r = parseInt(hex.slice(1, 3), 16);
            const g = parseInt(hex.slice(3, 5), 16);
            const b = parseInt(hex.slice(5, 7), 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        },

        /**
         * Genera gradiente entre dos colores
         */
        generateGradient: function(color1, color2) {
            // Simplificación: devuelve el primer color
            // Para gradientes reales se necesitaría el contexto del canvas
            return color1;
        },

        /**
         * Destruye todos los gráficos
         */
        destroyAll: function() {
            Chart.helpers.each(Chart.instances, function(instance) {
                instance.destroy();
            });
        }
    };

    // ============================================
    // EXPORTAR A GLOBAL
    // ============================================
    window.ChartHelper = ChartHelper;

})();
