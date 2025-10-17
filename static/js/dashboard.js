/**
 * Dashboard JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard cargado');

    // Animación de números en las tarjetas de estadísticas
    animarContadores();

    // Añadir efecto de clic en las tarjetas estadísticas
    setupStatCards();
});

/**
 * Anima los contadores de las tarjetas
 */
function animarContadores() {
    const contadores = document.querySelectorAll('.stat-value');

    contadores.forEach(contador => {
        const valorFinal = parseInt(contador.textContent) || 0;
        const duracion = 1000; // ms
        const pasos = 50;
        const incremento = valorFinal / pasos;
        let valorActual = 0;
        let paso = 0;

        const intervalo = setInterval(() => {
            valorActual += incremento;
            paso++;

            if (paso >= pasos) {
                contador.textContent = valorFinal;
                clearInterval(intervalo);
            } else {
                contador.textContent = Math.floor(valorActual);
            }
        }, duracion / pasos);
    });
}

/**
 * Configura las tarjetas de estadísticas para que sean clicables
 */
function setupStatCards() {
    const statCards = document.querySelectorAll('.stat-card[data-url]');

    statCards.forEach(card => {
        card.style.cursor = 'pointer';

        card.addEventListener('click', function() {
            const url = this.getAttribute('data-url');
            if (url) {
                window.location.href = url;
            }
        });

        // Efecto visual al hacer hover
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.05)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
        });
    });
}

/**
 * Recarga las estadísticas del dashboard via AJAX (opcional)
 */
function recargarEstadisticas() {
    // Implementar si necesitas actualización en tiempo real
    console.log('Recargando estadísticas...');
}
