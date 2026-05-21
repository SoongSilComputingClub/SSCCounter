// ==========================================
// CHART RENDERING LOGIC
// ==========================================
let miniChartInstance = null;
let statsChartInstance = null;

function getChartColors() {
  const dark = document.documentElement.classList.contains('dark');
  return {
    grid: dark ? '#334155' : '#f1f5f9',
    tick: dark ? '#94a3b8' : '#94a3b8',
    tooltipBg: dark ? '#1e293b' : '#1e1b4b',
    barFill: dark ? 'rgba(129, 140, 248, 0.4)' : 'rgba(99, 102, 241, 0.3)',
    barActive: dark ? 'rgba(129, 140, 248, 0.95)' : 'rgba(99, 102, 241, 0.9)',
    lineColor: dark ? '#818cf8' : '#6366f1',
    pointBg: dark ? '#818cf8' : '#6366f1',
  };
}

function renderMiniChart() {
  if (todayHours.length === 0) return;
  
  const ctx = document.getElementById('miniChart').getContext('2d');
  const labels = todayHours.map(h => h.hour + '시');
  const data = todayHours.map(h => h.count);
  const c = getChartColors();

  if (miniChartInstance) miniChartInstance.destroy();

  miniChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: data.map((_, i) => i === data.length - 1 ? c.barActive : c.barFill),
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: {
        backgroundColor: c.tooltipBg, titleFont: { family: 'Inter' }, bodyFont: { family: 'Inter' },
        callbacks: { label: (ctx) => ctx.parsed.y + '명' }
      }},
      scales: {
        x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 }, color: c.tick } },
        y: { grid: { color: c.grid }, ticks: { font: { family: 'Inter' }, color: c.tick }, beginAtZero: true }
      }
    }
  });
}

function updateStatsChart(day) {
  const data = weeklyStats[day];
  if (!data || data.length === 0) return;

  const ctx = document.getElementById('statsChart').getContext('2d');
  const dayNames = { mon: '월요일', tue: '화요일', wed: '수요일', thu: '목요일', fri: '금요일' };
  const c = getChartColors();
  const dark = document.documentElement.classList.contains('dark');

  document.getElementById('stats-subtitle').textContent = dayNames[day] + ' · 최근 4주 평균 기준';

  if (statsChartInstance) statsChartInstance.destroy();

  const gradient = ctx.createLinearGradient(0, 0, 0, 320);
  gradient.addColorStop(0, dark ? 'rgba(129, 140, 248, 0.25)' : 'rgba(99, 102, 241, 0.3)');
  gradient.addColorStop(1, 'rgba(99, 102, 241, 0.01)');

  statsChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: timeLabels,
      datasets: [{
        label: '평균 인원', data, borderColor: c.lineColor, backgroundColor: gradient,
        fill: true, tension: 0.4, pointBackgroundColor: c.pointBg,
        pointBorderColor: dark ? '#1e293b' : '#fff',
        pointBorderWidth: 2, pointRadius: 5, pointHoverRadius: 8,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: { backgroundColor: c.tooltipBg, titleFont: { family: 'Inter', size: 13 }, bodyFont: { family: 'Inter', size: 13 }, padding: 12, cornerRadius: 10, callbacks: { label: (ctx) => '평균 ' + ctx.parsed.y + '명' } }
      },
      scales: {
        x: { grid: { color: c.grid }, ticks: { font: { family: 'Inter', size: 12 }, color: c.tick } },
        y: { grid: { color: c.grid }, ticks: { font: { family: 'Inter', size: 12 }, color: c.tick }, beginAtZero: true, suggestedMax: 10 }
      }
    }
  });

  // Update stat cards
  const maxAvg = Math.max(...data);
  const dailyAvg = Math.round(data.reduce((a, b) => a + b, 0) / data.length);
  const peakIdx = data.indexOf(maxAvg);
  const quietIdx = data.indexOf(Math.min(...data));

  document.getElementById('stat-peak-avg').textContent = maxAvg + '명';
  document.getElementById('stat-daily-avg').textContent = dailyAvg + '명';
  document.getElementById('stat-peak-hour').textContent = timeLabels[peakIdx];
  document.getElementById('stat-quiet-hour').textContent = timeLabels[quietIdx];
}