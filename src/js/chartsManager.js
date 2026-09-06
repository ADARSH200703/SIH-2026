import { Chart, registerables } from 'chart.js';
Chart.register(...registerables);

/**
 * Real-Time Telemetry & Digital Twin Comparison Chart
 * Displays measured channels and physics twin predictions with configurable rolling window (30s, 60s, 120s).
 */

const DATASETS = [
  { label: 'RPM',          color: '#2DD4BF', yAxis: 'yRPM',  min: 2000, max: 6000  },
  { label: 'Temperature',  color: '#EF4444', yAxis: 'yTemp', min: 50,   max: 120   },
  { label: 'Oil Pressure', color: '#38BDF8', yAxis: 'yOil',  min: 1.0,  max: 6.5   },
  { label: 'Vibration',    color: '#F59E0B', yAxis: 'yVib',  min: 0.5,  max: 6.0   },
];

function makeGradient(ctx, color) {
  const g = ctx.createLinearGradient(0, 0, 0, 250);
  g.addColorStop(0, color + '30');   // soft glow opacity at top
  g.addColorStop(1, color + '00');   // transparent at bottom
  return g;
}

export class ChartsManager {
  constructor(canvas) {
    const ctx = canvas.getContext('2d');
    this.windowSeconds = 30; // default 30s rolling window
    this.maxPoints = 300;     // bounded memory limit for 30s @ 10Hz

    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: DATASETS.map(d => ({
          label: d.label,
          data: [],
          borderColor: d.color,
          backgroundColor: makeGradient(ctx, d.color),
          borderWidth: 2,
          tension: 0.35,
          pointRadius: 0,
          pointHoverRadius: 4,
          yAxisID: d.yAxis,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: 'rgba(23, 32, 51, 0.96)',
            titleColor: '#38BDF8',
            bodyColor: '#E5E7EB',
            borderColor: '#263449',
            borderWidth: 1,
            padding: 10,
            cornerRadius: 6,
            titleFont: { family: 'JetBrains Mono', size: 11 },
            bodyFont:  { family: 'Inter', size: 12 },
            callbacks: {
              title: items => `T: ${items[0]?.label || ''} min`,
              label: ctx => {
                const units = ['RPM', '°C', 'Bar', 'mm/s'];
                return ` ${ctx.dataset.label}: ${(+ctx.raw).toFixed(1)} ${units[ctx.datasetIndex] || ''}`;
              },
            },
          },
        },
        scales: {
          x: {
            grid:  { color: 'rgba(38, 52, 73, 0.6)' },
            ticks: { color: '#94A3B8', font: { family: 'JetBrains Mono', size: 10 }, maxTicksLimit: 6 },
            title: { display: true, text: 'Mission Flight Time (min)', color: '#94A3B8', font: { family: 'Inter', size: 11 } },
          },
          ...Object.fromEntries(DATASETS.map(d => [
            d.yAxis, { type: 'linear', display: false, min: d.min, max: d.max }
          ])),
        },
      },
    });
  }

  setWindow(seconds) {
    this.windowSeconds = seconds || 30;
    // For 10Hz target, max points = seconds * 10
    this.maxPoints = Math.max(30, this.windowSeconds * 10);
  }

  // Key mapping: same order as DATASETS
  update({ labels = [], rpm = [], temperature = [], oilPressure = [], vibration = [] }) {
    const limit = this.maxPoints;
    const sliceLabels = labels.length > limit ? labels.slice(-limit) : labels;
    const sliceRpm = rpm.length > limit ? rpm.slice(-limit) : rpm;
    const sliceTemp = temperature.length > limit ? temperature.slice(-limit) : temperature;
    const sliceOil = oilPressure.length > limit ? oilPressure.slice(-limit) : oilPressure;
    const sliceVib = vibration.length > limit ? vibration.slice(-limit) : vibration;

    this.chart.data.labels = sliceLabels;
    [sliceRpm, sliceTemp, sliceOil, sliceVib].forEach((data, i) => {
      this.chart.data.datasets[i].data = data;
    });
    this.chart.update('none');
  }
}
