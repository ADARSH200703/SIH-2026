import { Chart, registerables } from "chart.js";
Chart.register(...registerables);

const SENSOR_CONFIGS = [
  { key: "rpm",         id: "rt-chart-rpm",  label: "Engine RPM",            color: "#2DD4BF", unit: "RPM",    warn: 5000, crit: 5500, min: 2000, max: 6000 },
  { key: "temperature", id: "rt-chart-temp", label: "Cylinder Head Temp",    color: "#EF4444", unit: "°C",     warn: 84,   crit: 92,   min: 50,   max: 120  },
  { key: "oilPressure", id: "rt-chart-oil",  label: "Oil Pressure",          color: "#38BDF8", unit: "Bar",    warn: 3.6,  crit: 2.8,  min: 1.0,  max: 6.5  },
  { key: "vibration",   id: "rt-chart-vib",  label: "Casing Vibration",      color: "#F59E0B", unit: "mm/s",   warn: 2.4,  crit: 3.8,  min: 0,    max: 8    },
  { key: "fuelFlow",    id: "rt-chart-fuel", label: "Fuel Flow Rate",        color: "#38BDF8", unit: "L/h",    warn: 7.5,  crit: 9.0,  min: 2,    max: 12   },
  { key: "engineLoad",  id: "rt-chart-load", label: "Engine Load Demand",    color: "#2DD4BF", unit: "%",      warn: 85,   crit: 95,   min: 0,    max: 100  },
];

function makeChart(canvas, cfg) {
  const ctx = canvas.getContext("2d");
  const grad = ctx.createLinearGradient(0, 0, 0, 120);
  grad.addColorStop(0, cfg.color + "35");
  grad.addColorStop(1, cfg.color + "00");
  return new Chart(ctx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: cfg.label, data: [], borderColor: cfg.color, backgroundColor: grad, borderWidth: 2, tension: 0.38, pointRadius: 0, pointHoverRadius: 4, fill: true },
        { label: "Warn", data: [], borderColor: "#F59E0B", borderWidth: 1, borderDash: [4, 4], pointRadius: 0, fill: false, tension: 0 },
        { label: "Crit", data: [], borderColor: "#EF4444", borderWidth: 1, borderDash: [3, 3], pointRadius: 0, fill: false, tension: 0 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(23, 32, 51, 0.96)", titleColor: cfg.color, bodyColor: "#E5E7EB",
          borderColor: "#263449", borderWidth: 1, padding: 8, cornerRadius: 6,
          filter: item => item.datasetIndex === 0,
          callbacks: {
            title: items => "T: " + items[0]?.label + " min",
            label: ctx => " " + cfg.label + ": " + (+ctx.raw).toFixed(2) + " " + cfg.unit,
          },
        },
      },
      scales: {
        x: { grid: { color: "rgba(38, 52, 73, 0.6)" }, ticks: { color: "#94A3B8", font: { family: "JetBrains Mono", size: 9 }, maxTicksLimit: 5 } },
        y: { min: cfg.min, max: cfg.max, grid: { color: "rgba(38, 52, 73, 0.6)" }, ticks: { color: "#94A3B8", font: { family: "JetBrains Mono", size: 9 }, maxTicksLimit: 5 } },
      },
    },
  });
}

export class RealtimeMonitor {
  constructor() {
    this.charts = {};
    this._initialized = false;
    this.windowSeconds = 30;
    this.maxPoints = 300;
  }

  init() {
    if (this._initialized) return;
    SENSOR_CONFIGS.forEach(cfg => {
      const canvas = document.getElementById(cfg.id);
      if (canvas) this.charts[cfg.key] = makeChart(canvas, cfg);
    });
    this._initialized = true;
  }

  setWindow(seconds) {
    this.windowSeconds = seconds || 30;
    this.maxPoints = Math.max(30, this.windowSeconds * 10);
  }

  update(state, history) {
    if (!this._initialized) return;
    const limit = this.maxPoints;
    const labels = (history.labels || []).slice(-limit);

    SENSOR_CONFIGS.forEach(cfg => {
      const chart = this.charts[cfg.key];
      if (!chart) return;
      const rawData = history[cfg.key] || [];
      const data = rawData.slice(-limit);

      chart.data.labels            = labels;
      chart.data.datasets[0].data  = data;
      chart.data.datasets[1].data  = Array(labels.length).fill(cfg.warn);
      chart.data.datasets[2].data  = Array(labels.length).fill(cfg.crit);
      const v = state[cfg.key] ?? 0;
      const isOil = cfg.key === "oilPressure";
      const isCrit = isOil ? v < cfg.crit : v > cfg.crit;
      const isWarn = isOil ? v < cfg.warn : v > cfg.warn;
      chart.data.datasets[0].borderColor = isCrit ? "#EF4444" : isWarn ? "#F59E0B" : cfg.color;
      chart.update("none");
    });

    // Live readouts
    SENSOR_CONFIGS.forEach(cfg => {
      const v = state[cfg.key] ?? 0;
      const isOil = cfg.key === "oilPressure";
      const isCrit = isOil ? v < cfg.crit : v > cfg.crit;
      const isWarn = isOil ? v < cfg.warn : v > cfg.warn;
      const el = id => document.getElementById(id);
      const valEl = el("rt-val-" + cfg.key);
      if (valEl) valEl.textContent = cfg.key === "rpm" ? Math.round(v).toLocaleString() : v.toFixed(cfg.key === "engineLoad" ? 0 : 1);
      const badge = el("rt-badge-" + cfg.key);
      if (badge) { badge.textContent = isCrit ? "CRITICAL" : isWarn ? "WARNING" : "NORMAL"; badge.className = "rt-status-badge " + (isCrit ? "crit" : isWarn ? "warn" : "ok"); }
      const bar = el("rt-bar-" + cfg.key);
      if (bar) { const pct = Math.round(((v - cfg.min) / (cfg.max - cfg.min)) * 100); bar.style.width = Math.max(0, Math.min(100, pct)) + "%"; bar.style.background = isCrit ? "#EF4444" : isWarn ? "#F59E0B" : cfg.color; }
    });
    const el = id => document.getElementById(id);
    if (el("rt-summary-rpm"))    el("rt-summary-rpm").textContent    = Math.round(state.rpm || 0).toLocaleString() + " RPM";
    if (el("rt-summary-temp"))   el("rt-summary-temp").textContent   = (state.temperature || 0).toFixed(1) + " °C";
    if (el("rt-summary-oil"))    el("rt-summary-oil").textContent    = (state.oilPressure || 0).toFixed(1) + " Bar";
    if (el("rt-summary-vib"))    el("rt-summary-vib").textContent    = (state.vibration || 0).toFixed(1) + " mm/s";
    if (el("rt-health-val"))     el("rt-health-val").textContent     = (state.engineHealth || 92) + "%";
    if (el("rt-data-rate"))      el("rt-data-rate").textContent      = new Date().toTimeString().slice(0,8) + " · 10 Hz";
    if (el("rt-summary-status")) { el("rt-summary-status").textContent = state.status || "NORMAL"; el("rt-summary-status").className = "rt-overall-badge " + (state.status || "normal").toLowerCase(); }
  }
}

export { SENSOR_CONFIGS };
