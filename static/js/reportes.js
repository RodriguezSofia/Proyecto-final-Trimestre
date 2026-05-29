async function cargarGraficaVentas() {
    try {
        const response = await fetch('/api/ventas-semanales');
        const data = await response.json();
        const ctx = document
            .getElementById('graficaVentas');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Ventas',
                    data: data.valores,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: true
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    } catch (error) {
        console.error(
            "Error cargando gráfica:",
            error
        );
    }
}

cargarGraficaVentas();