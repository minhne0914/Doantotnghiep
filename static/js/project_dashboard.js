(function () {
    const payloadElement = document.getElementById('project-dashboard-data');
    if (!payloadElement || typeof Chart === 'undefined') return;

    const data = JSON.parse(payloadElement.textContent);

    Chart.defaults.global.defaultFontFamily = 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
    Chart.defaults.global.defaultFontColor = '#697282';

    const gridColor = 'rgba(105, 114, 130, 0.14)';
    const tooltipStyle = {
        backgroundColor: '#111318',
        titleFontColor: '#fff',
        bodyFontColor: '#fff',
        displayColors: false,
        cornerRadius: 8,
        xPadding: 12,
        yPadding: 10,
    };

    const createGradient = (ctx, colorStart, colorEnd) => {
        const gradient = ctx.createLinearGradient(0, 0, 0, 280);
        gradient.addColorStop(0, colorStart);
        gradient.addColorStop(1, colorEnd);
        return gradient;
    };

    const velocityCanvas = document.getElementById('velocityChart');
    if (velocityCanvas) {
        const ctx = velocityCanvas.getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.velocity.labels,
                datasets: [
                    {
                        label: 'Actual',
                        data: data.velocity.actual,
                        borderColor: '#13a69a',
                        backgroundColor: createGradient(ctx, 'rgba(19, 166, 154, 0.22)', 'rgba(19, 166, 154, 0)'),
                        pointBackgroundColor: '#13a69a',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        lineTension: 0.35,
                        fill: true,
                    },
                    {
                        label: 'Planned',
                        data: data.velocity.planned,
                        borderColor: '#3478f6',
                        backgroundColor: 'rgba(52, 120, 246, 0)',
                        borderDash: [6, 6],
                        pointRadius: 0,
                        lineTension: 0.35,
                        fill: false,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } },
                tooltips: tooltipStyle,
                scales: {
                    xAxes: [{ gridLines: { display: false }, ticks: { padding: 10 } }],
                    yAxes: [{
                        gridLines: { color: gridColor, drawBorder: false },
                        ticks: { beginAtZero: true, padding: 10 },
                    }],
                },
            },
        });
    }

    const workloadCanvas = document.getElementById('workloadChart');
    if (workloadCanvas) {
        new Chart(workloadCanvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.workload.labels,
                datasets: [{
                    label: 'Utilization',
                    data: data.workload.values,
                    backgroundColor: ['#3478f6', '#13a69a', '#f6b73c', '#7c5cff', '#35b86b'],
                    borderWidth: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                legend: { display: false },
                tooltips: tooltipStyle,
                scales: {
                    xAxes: [{ gridLines: { display: false }, ticks: { padding: 8 } }],
                    yAxes: [{
                        gridLines: { color: gridColor, drawBorder: false },
                        ticks: { beginAtZero: true, max: 100, padding: 8 },
                    }],
                },
            },
        });
    }

    const portfolioCanvas = document.getElementById('portfolioChart');
    if (portfolioCanvas) {
        new Chart(portfolioCanvas.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: data.portfolio.labels,
                datasets: [{
                    data: data.portfolio.values,
                    backgroundColor: ['#35b86b', '#f6b73c', '#ef5267'],
                    borderWidth: 0,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutoutPercentage: 68,
                legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } },
                tooltips: tooltipStyle,
            },
        });
    }
})();
