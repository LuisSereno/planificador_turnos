/**
 * CALENDARIO.JS - Vista de Calendario de Turnos
 */

(function() {
    'use strict';

    const CalendarioHelper = {
        /**
         * Inicializa el calendario
         */
        init: function(containerId, data) {
            this.container = document.getElementById(containerId);
            if (!this.container) return;

            this.data = data;
            this.currentDate = new Date();
            this.render();
        },

        /**
         * Renderiza el calendario
         */
        render: function() {
            const year = this.currentDate.getFullYear();
            const month = this.currentDate.getMonth();

            const firstDay = new Date(year, month, 1);
            const lastDay = new Date(year, month + 1, 0);
            const daysInMonth = lastDay.getDate();
            const startingDayOfWeek = firstDay.getDay();

            let html = '<div class="calendario-grid">';

            // Headers de días
            const dayNames = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
            dayNames.forEach(day => {
                html += `<div class="calendario-day-header">${day}</div>`;
            });

            // Días del mes anterior (espacios vacíos)
            for (let i = 0; i < startingDayOfWeek; i++) {
                html += '<div class="calendario-day other-month"></div>';
            }

            // Días del mes actual
            for (let day = 1; day <= daysInMonth; day++) {
                const date = new Date(year, month, day);
                const isToday = this.isToday(date);
                const isWeekend = date.getDay() === 0 || date.getDay() === 6;

                let classes = 'calendario-day';
                if (isToday) classes += ' today';
                if (isWeekend) classes += ' weekend';

                html += `<div class="${classes}" data-date="${this.formatDate(date)}">`;
                html += `<div class="day-number">${day}</div>`;
                html += this.renderTurnos(date);
                html += '</div>';
            }

            html += '</div>';
            this.container.innerHTML = html;

            this.attachEvents();
        },

        /**
         * Renderiza los turnos de un día
         */
        renderTurnos: function(date) {
            const dateStr = this.formatDate(date);
            const turnos = this.data[dateStr] || {};

            let html = '<div class="turnos-container">';

            ['MAÑANA', 'TARDE', 'NOCHE'].forEach(turno => {
                const enfermeras = turnos[turno] || [];
                if (enfermeras.length > 0) {
                    const turnoClass = turno.toLowerCase();
                    html += `
                        <div class="turno-item ${turnoClass}">
                            <i class="fas fa-clock turno-icon"></i>
                            <span class="turno-nombre">${turno}</span>
                            <span class="turno-count">${enfermeras.length}</span>
                        </div>
                    `;
                }
            });

            html += '</div>';
            return html;
        },

        /**
         * Adjunta eventos
         */
        attachEvents: function() {
            this.container.querySelectorAll('.calendario-day:not(.other-month)').forEach(day => {
                day.addEventListener('click', (e) => {
                    const date = day.dataset.date;
                    this.showDayDetail(date);
                });
            });
        },

        /**
         * Muestra detalle del día
         */
        showDayDetail: function(dateStr) {
            const turnos = this.data[dateStr] || {};

            let html = `
                <div class="modal fade" id="dayDetailModal" tabindex="-1">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h5 class="modal-title">Turnos del ${this.formatDateLong(dateStr)}</h5>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body">
            `;

            ['MAÑANA', 'TARDE', 'NOCHE'].forEach(turno => {
                const enfermeras = turnos[turno] || [];
                const turnoClass = turno.toLowerCase();

                html += `
                    <div class="turno-detail-card ${turnoClass} mb-3">
                        <div class="turno-detail-header">
                            <i class="fas fa-clock me-2"></i>
                            <span class="turno-detail-title">${turno}</span>
                        </div>
                        <ul class="enfermeras-list">
                `;

                if (enfermeras.length > 0) {
                    enfermeras.forEach(enfermera => {
                        const inicial = enfermera.charAt(0).toUpperCase();
                        html += `
                            <li class="enfermera-item">
                                <div class="enfermera-avatar">${inicial}</div>
                                <span class="enfermera-nombre">${enfermera}</span>
                            </li>
                        `;
                    });
                } else {
                    html += '<li class="text-muted">Sin asignaciones</li>';
                }

                html += `
                        </ul>
                    </div>
                `;
            });

            html += `
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            // Eliminar modal anterior si existe
            const oldModal = document.getElementById('dayDetailModal');
            if (oldModal) oldModal.remove();

            // Añadir nuevo modal
            document.body.insertAdjacentHTML('beforeend', html);

            // Mostrar modal
            const modal = new bootstrap.Modal(document.getElementById('dayDetailModal'));
            modal.show();
        },

        /**
         * Navega al mes anterior
         */
        previousMonth: function() {
            this.currentDate.setMonth(this.currentDate.getMonth() - 1);
            this.render();
        },

        /**
         * Navega al mes siguiente
         */
        nextMonth: function() {
            this.currentDate.setMonth(this.currentDate.getMonth() + 1);
            this.render();
        },

        /**
         * Va al mes actual
         */
        today: function() {
            this.currentDate = new Date();
            this.render();
        },

        /**
         * Verifica si es hoy
         */
        isToday: function(date) {
            const today = new Date();
            return date.getDate() === today.getDate() &&
                   date.getMonth() === today.getMonth() &&
                   date.getFullYear() === today.getFullYear();
        },

        /**
         * Formatea fecha (YYYY-MM-DD)
         */
        formatDate: function(date) {
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        },

        /**
         * Formatea fecha larga
         */
        formatDateLong: function(dateStr) {
            const date = new Date(dateStr + 'T00:00:00');
            return date.toLocaleDateString('es-ES', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
    };

    // ============================================
    // EXPORTAR A GLOBAL
    // ============================================
    window.CalendarioHelper = CalendarioHelper;

})();
