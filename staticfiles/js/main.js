/**
 * MAIN.JS - JavaScript Global del Sistema
 * Funciones y utilidades compartidas
 */

(function() {
    'use strict';

    // ============================================
    // CONFIGURACIÓN GLOBAL
    // ============================================
    const Config = {
        apiBaseUrl: '/api/',
        csrfToken: document.querySelector('meta[name="csrf-token"]')?.content || '',
        debug: false
    };

    // ============================================
    // UTILIDADES GENERALES
    // ============================================
    const Utils = {
        /**
         * Obtiene cookie por nombre (para CSRF)
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
         * Formatea fecha a español
         */
        formatDate: function(date, format = 'short') {
            const d = new Date(date);
            if (format === 'short') {
                return d.toLocaleDateString('es-ES', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit'
                });
            } else if (format === 'long') {
                return d.toLocaleDateString('es-ES', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });
            } else if (format === 'datetime') {
                return d.toLocaleString('es-ES', {
                    year: 'numeric',
                    month: '2-digit',
                    day: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit'
                });
            }
            return d.toLocaleDateString('es-ES');
        },

        /**
         * Formatea números con separadores
         */
        formatNumber: function(num, decimals = 0) {
            return new Intl.NumberFormat('es-ES', {
                minimumFractionDigits: decimals,
                maximumFractionDigits: decimals
            }).format(num);
        },

        /**
         * Debounce para optimizar eventos
         */
        debounce: function(func, wait) {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func(...args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },

        /**
         * Muestra notificación toast
         */
        showToast: function(message, type = 'info') {
            const toastContainer = document.getElementById('toast-container') || this.createToastContainer();
            const toast = document.createElement('div');
            toast.className = `alert alert-${type} alert-dismissible fade show toast-notification`;
            toast.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            toastContainer.appendChild(toast);

            // Auto-remove después de 5 segundos
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.classList.remove('show');
                    setTimeout(() => toast.remove(), 150);
                }
            }, 5000);
        },

        createToastContainer: function() {
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText = `
                position: fixed;
                top: 90px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
            `;
            document.body.appendChild(container);
            return container;
        },

        /**
         * Confirma acción con modal
         */
        confirm: function(message, callback) {
            if (window.confirm(message)) {
                callback();
            }
        },

        /**
         * Genera color aleatorio
         */
        randomColor: function() {
            return '#' + Math.floor(Math.random()*16777215).toString(16);
        },

        /**
         * Valida email
         */
        validateEmail: function(email) {
            const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return re.test(email);
        },

        /**
         * Copia al portapapeles
         */
        copyToClipboard: function(text) {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(text).then(() => {
                    this.showToast('Copiado al portapapeles', 'success');
                });
            } else {
                // Fallback para navegadores antiguos
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.style.position = 'fixed';
                textarea.style.opacity = '0';
                document.body.appendChild(textarea);
                textarea.select();
                document.execCommand('copy');
                document.body.removeChild(textarea);
                this.showToast('Copiado al portapapeles', 'success');
            }
        }
    };

    // ============================================
    // LOADER / SPINNER
    // ============================================
    const Loader = {
        spinner: null,

        init: function() {
            this.spinner = document.getElementById('loadingSpinner');
            if (!this.spinner) {
                this.createSpinner();
            }
        },

        createSpinner: function() {
            this.spinner = document.createElement('div');
            this.spinner.id = 'loadingSpinner';
            this.spinner.className = 'spinner-overlay';
            this.spinner.innerHTML = `
                <div class="spinner-border text-light" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Cargando...</span>
                </div>
            `;
            document.body.appendChild(this.spinner);
        },

        show: function() {
            if (this.spinner) {
                this.spinner.classList.add('active');
            }
        },

        hide: function() {
            if (this.spinner) {
                this.spinner.classList.remove('active');
            }
        }
    };

    // ============================================
    // VALIDACIÓN DE FORMULARIOS
    // ============================================
    const FormValidator = {
        /**
         * Valida formulario completo
         */
        validate: function(form) {
            let isValid = true;
            const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');

            inputs.forEach(input => {
                if (!this.validateField(input)) {
                    isValid = false;
                }
            });

            return isValid;
        },

        /**
         * Valida campo individual
         */
        validateField: function(field) {
            const value = field.value.trim();
            let isValid = true;
            let errorMessage = '';

            // Validación de campo requerido
            if (field.hasAttribute('required') && !value) {
                isValid = false;
                errorMessage = 'Este campo es obligatorio';
            }

            // Validación de email
            if (field.type === 'email' && value && !Utils.validateEmail(value)) {
                isValid = false;
                errorMessage = 'Email inválido';
            }

            // Validación de número
            if (field.type === 'number') {
                const min = field.getAttribute('min');
                const max = field.getAttribute('max');
                const numValue = parseFloat(value);

                if (min && numValue < parseFloat(min)) {
                    isValid = false;
                    errorMessage = `El valor mínimo es ${min}`;
                }
                if (max && numValue > parseFloat(max)) {
                    isValid = false;
                    errorMessage = `El valor máximo es ${max}`;
                }
            }

            // Mostrar/ocultar error
            this.toggleError(field, isValid, errorMessage);
            return isValid;
        },

        /**
         * Muestra u oculta mensaje de error
         */
        toggleError: function(field, isValid, message) {
            let errorDiv = field.parentElement.querySelector('.invalid-feedback');

            if (!isValid) {
                field.classList.add('is-invalid');
                field.classList.remove('is-valid');

                if (!errorDiv) {
                    errorDiv = document.createElement('div');
                    errorDiv.className = 'invalid-feedback';
                    field.parentElement.appendChild(errorDiv);
                }
                errorDiv.textContent = message;
            } else {
                field.classList.remove('is-invalid');
                field.classList.add('is-valid');

                if (errorDiv) {
                    errorDiv.remove();
                }
            }
        },

        /**
         * Limpia validación de formulario
         */
        clearValidation: function(form) {
            form.querySelectorAll('.is-invalid, .is-valid').forEach(field => {
                field.classList.remove('is-invalid', 'is-valid');
            });
            form.querySelectorAll('.invalid-feedback').forEach(error => {
                error.remove();
            });
        }
    };

    // ============================================
    // SIDEBAR
    // ============================================
    const Sidebar = {
        init: function() {
            const sidebarToggle = document.getElementById('sidebarToggle');
            const sidebar = document.getElementById('sidebar');

            if (sidebarToggle && sidebar) {
                sidebarToggle.addEventListener('click', () => {
                    sidebar.classList.toggle('collapsed');
                    this.saveState(sidebar.classList.contains('collapsed'));
                });

                // Restaurar estado guardado
                this.restoreState();
            }

            // Cerrar sidebar en móvil al hacer clic fuera
            this.setupMobileClose();
        },

        saveState: function(collapsed) {
            localStorage.setItem('sidebarCollapsed', collapsed);
        },

        restoreState: function() {
            const collapsed = localStorage.getItem('sidebarCollapsed') === 'true';
            const sidebar = document.getElementById('sidebar');
            if (sidebar && collapsed) {
                sidebar.classList.add('collapsed');
            }
        },

        setupMobileClose: function() {
            if (window.innerWidth <= 768) {
                document.addEventListener('click', (e) => {
                    const sidebar = document.getElementById('sidebar');
                    const sidebarToggle = document.getElementById('sidebarToggle');

                    if (sidebar && !sidebar.contains(e.target) && e.target !== sidebarToggle) {
                        sidebar.classList.add('collapsed');
                    }
                });
            }
        }
    };

    // ============================================
    // TABLAS
    // ============================================
    const TableHelper = {
        /**
         * Ordena tabla por columna
         */
        sortTable: function(table, columnIndex, ascending = true) {
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));

            rows.sort((a, b) => {
                const aValue = a.cells[columnIndex].textContent.trim();
                const bValue = b.cells[columnIndex].textContent.trim();

                if (!isNaN(aValue) && !isNaN(bValue)) {
                    return ascending ? aValue - bValue : bValue - aValue;
                }

                return ascending
                    ? aValue.localeCompare(bValue)
                    : bValue.localeCompare(aValue);
            });

            rows.forEach(row => tbody.appendChild(row));
        },

        /**
         * Filtra tabla por búsqueda
         */
        filterTable: function(table, searchTerm) {
            const rows = table.querySelectorAll('tbody tr');
            const term = searchTerm.toLowerCase();

            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(term) ? '' : 'none';
            });
        },

        /**
         * Exporta tabla a CSV
         */
        exportToCSV: function(table, filename = 'tabla.csv') {
            const rows = table.querySelectorAll('tr');
            const csv = [];

            rows.forEach(row => {
                const cols = row.querySelectorAll('td, th');
                const rowData = Array.from(cols).map(col => {
                    let data = col.textContent.trim();
                    // Escapar comillas
                    data = data.replace(/"/g, '""');
                    // Envolver en comillas si contiene comas
                    return data.includes(',') ? `"${data}"` : data;
                });
                csv.push(rowData.join(','));
            });

            const csvContent = csv.join('\n');
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);

            link.setAttribute('href', url);
            link.setAttribute('download', filename);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    };

    // ============================================
    // CONFIRMACIONES DE ELIMINACIÓN
    // ============================================
    const DeleteConfirm = {
        init: function() {
            document.querySelectorAll('[data-confirm-delete]').forEach(element => {
                element.addEventListener('click', (e) => {
                    e.preventDefault();
                    const message = element.dataset.confirmDelete || '¿Estás seguro de que deseas eliminar este elemento?';

                    if (confirm(message)) {
                        if (element.tagName === 'FORM') {
                            element.submit();
                        } else if (element.tagName === 'A') {
                            window.location.href = element.href;
                        }
                    }
                });
            });
        }
    };

    // ============================================
    // AUTO-SAVE
    // ============================================
    const AutoSave = {
        init: function(formId, saveCallback, interval = 30000) {
            const form = document.getElementById(formId);
            if (!form) return;

            let timer;
            const inputs = form.querySelectorAll('input, textarea, select');

            inputs.forEach(input => {
                input.addEventListener('input', () => {
                    clearTimeout(timer);
                    timer = setTimeout(() => {
                        this.save(form, saveCallback);
                    }, interval);
                });
            });
        },

        save: function(form, callback) {
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            console.log('Auto-guardando...', data);
            if (callback && typeof callback === 'function') {
                callback(data);
            }

            Utils.showToast('Borrador guardado automáticamente', 'info');
        }
    };

    // ============================================
    // BÚSQUEDA EN VIVO
    // ============================================
    const LiveSearch = {
        init: function(inputId, targetSelector, minChars = 2) {
            const input = document.getElementById(inputId);
            if (!input) return;

            input.addEventListener('input', Utils.debounce((e) => {
                const searchTerm = e.target.value.trim();

                if (searchTerm.length >= minChars) {
                    this.search(searchTerm, targetSelector);
                } else {
                    this.clearSearch(targetSelector);
                }
            }, 300));
        },

        search: function(term, targetSelector) {
            const elements = document.querySelectorAll(targetSelector);
            const searchLower = term.toLowerCase();

            elements.forEach(element => {
                const text = element.textContent.toLowerCase();
                element.style.display = text.includes(searchLower) ? '' : 'none';
            });
        },

        clearSearch: function(targetSelector) {
            const elements = document.querySelectorAll(targetSelector);
            elements.forEach(element => {
                element.style.display = '';
            });
        }
    };

    // ============================================
    // INICIALIZACIÓN
    // ============================================
    document.addEventListener('DOMContentLoaded', function() {
        // Inicializar módulos
        Loader.init();
        Sidebar.init();
        DeleteConfirm.init();

        // Configurar tooltips de Bootstrap
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Configurar popovers de Bootstrap
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });

        // Auto-cerrar alertas
        setTimeout(() => {
            document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            });
        }, 5000);

        // Validación en tiempo real
        document.querySelectorAll('form.needs-validation').forEach(form => {
            form.querySelectorAll('input, select, textarea').forEach(field => {
                field.addEventListener('blur', () => {
                    FormValidator.validateField(field);
                });
            });

            form.addEventListener('submit', (e) => {
                if (!FormValidator.validate(form)) {
                    e.preventDefault();
                    e.stopPropagation();
                    Utils.showToast('Por favor completa todos los campos requeridos', 'danger');
                }
            });
        });

        console.log('✓ Sistema inicializado correctamente');
    });

    // ============================================
    // EXPORTAR A GLOBAL
    // ============================================
    window.AppUtils = Utils;
    window.Loader = Loader;
    window.FormValidator = FormValidator;
    window.TableHelper = TableHelper;
    window.AutoSave = AutoSave;
    window.LiveSearch = LiveSearch;

})();
