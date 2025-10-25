// Dashboard Charts - Chart.js
// Copiar a turnos/static/js/dashboard.js

document.addEventListener('DOMContentLoaded', function() {
    initCharts();
});

function initCharts() {
    initDistribucionTurnosChart();
    initCargaEnfermerasChart();
}

function initDistribucionTurnosChart() {
    const ctx = document.getElementById('chartDistribucionTurnos');
    if (!ctx) return;
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['MaÃ±ana', 'Tarde', 'Noche', 'Libres'],
            datasets: [{
                data: window.distribucionData || [0, 0, 0, 0],
                backgroundColor: ['#ffc107', '#17a2b8', '#343a40', '#6c757d'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'bottom' },
                title: { display: true, text: 'Distribucion de Turnos' }
            }
        }
    });
}

function initCargaEnfermerasChart() {
    const ctx = document.getElementById('chartCargaEnfermeras');
    if (!ctx) return;
    
    const enfermeras = window.enfermerasData || [];
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: enfermeras.map(e => e.nombre),
            datasets: [{
                label: 'Turnos Trabajados',
                data: enfermeras.map(e => e.turnos),
                backgroundColor: '#007bff'
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}
