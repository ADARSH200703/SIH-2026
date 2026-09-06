import { Chart, registerables } from "chart.js";
Chart.register(...registerables);

const SENSOR_CONFIGS = [
  { key: "rpm",         id: "rt-chart-rpm",  label: "Engine RPM",            color: "#2DD4BF", unit: "RPM",    warn: 5000, crit: 5500, min: 0,   max: 6000 },
  { key: "temperature", id: "rt-chart-temp", label: "Cylinder Head Temp",    color: "#EF4444", unit: "°C",     warn: 84,   crit: 92,   min: 0,   max: 130  },
  { key: "oilPressure", id: "rt-chart-oil",  label: "Oil Pressure",          color: "#38BDF8", unit: "Bar",    warn: 3.6,  crit: 2.8,  min: 0,   max: 7.0  },
  { key: "vibration",   id: "rt-chart-vib",  label: "Casing Vibration",      color: "#F59E0B", unit: "mm/s",   warn: 2.4,  crit: 3.8,  min: 0,   max: 8.0  },
  { key: "fuelFlow",    id: "rt-chart-fuel", label: "Fuel Flow Rate",        color: "#38BDF8", unit: "L/h",    warn: 7.5,  crit: 9.0,  min: 0,   max: 12.0 },
  { key: "engineLoad",  id: "rt-chart-load", label: "Engine Load Demand",    color: "#2DD4BF", unit: "%",      warn: 85,   crit: 95,   min: 0,   max: 100  },
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
            title: items => items[0]?.label ? "T: " + items[0].label : "--",
            label: ctx => " " + cfg.label + ": " + (typeof ctx.raw === "number" ? (+ctx.raw).toFixed(2) : "--") + " " + cfg.unit,
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

  renderDisconnected(options = {}) {
    const el = id => document.getElementById(id);
    const mode = options.mode || "LIVE";
    const statusText = options.status || "NO LIVE DATA";
    const sourceText = options.source || "DISCONNECTED";

    // Sensor card readouts -> N/A
    SENSOR_CONFIGS.forEach(cfg => {
      const valEl = el("rt-val-" + cfg.key);
      if (valEl) valEl.textContent = "N/A";
      const badge = el("rt-badge-" + cfg.key);
      if (badge) {
        badge.textContent = "NO DATA";
        badge.className = "rt-status-badge offline";
      }
      const bar = el("rt-bar-" + cfg.key);
      if (bar) {
        bar.style.width = "0%";
        bar.style.background = "var(--border-light)";
      }
    });

    // Summary strip -> N/A
    if (el("rt-summary-rpm"))  el("rt-summary-rpm").textContent  = "N/A";
    if (el("rt-summary-temp")) el("rt-summary-temp").textContent = "N/A";
    if (el("rt-summary-oil"))  el("rt-summary-oil").textContent  = "N/A";
    if (el("rt-summary-vib"))  el("rt-summary-vib").textContent  = "N/A";
    if (el("rt-health-val"))   el("rt-health-val").textContent   = "N/A";

    if (el("rt-data-rate")) {
      el("rt-data-rate").textContent = `SOURCE: ${sourceText} · DATA AGE: --`;
    }
    if (el("rt-summary-status")) {
      el("rt-summary-status").textContent = statusText;
      el("rt-summary-status").className = "rt-overall-badge offline";
    }
  }

  update(state, history, options = {}) {
    this.init();
    if (!this._initialized) return;

    const isConnected = options.isConnected !== undefined ? options.isConnected : true;
    const mode = options.mode || "LIVE";
    const status = options.status || (mode === "LIVE" ? "LIVE" : "SIMULATION");
    const source = options.source || (mode === "LIVE" ? "LIVE STREAM" : "SIMULATOR");
    const dataAgeMs = options.dataAgeMs !== undefined ? options.dataAgeMs : null;

    if (!isConnected && mode === "LIVE") {
      this.renderDisconnected({ mode, status: "NO LIVE DATA", source: "DISCONNECTED" });
      return;
    }

    const limit = this.maxPoints;
    const labels = (history && history.labels ? history.labels : []).slice(-limit);

    // Update charts with actual received history
    SENSOR_CONFIGS.forEach(cfg => {
      const chart = this.charts[cfg.key];
      if (!chart) return;
      const rawData = (history && history[cfg.key]) ? history[cfg.key] : [];
      const data = rawData.slice(-limit);

      chart.data.labels           = labels;
      chart.data.datasets[0].data = data;
      chart.data.datasets[1].data = Array(labels.length).fill(cfg.warn);
      chart.data.datasets[2].data = Array(labels.length).fill(cfg.crit);
      
      const v = state[cfg.key];
      if (typeof v === "number") {
        const isOil = cfg.key === "oilPressure";
        const isCrit = isOil ? v < cfg.crit : v > cfg.crit;
        const isWarn = isOil ? v < cfg.warn : v > cfg.warn;
        chart.data.datasets[0].borderColor = isCrit ? "#EF4444" : isWarn ? "#F59E0B" : cfg.color;
      }
      chart.update("none");
    });

    // Live Readouts with real telemetry values
    const el = id => document.getElementById(id);
    SENSOR_CONFIGS.forEach(cfg => {
      const v = state[cfg.key];
      const valEl = el("rt-val-" + cfg.key);
      const badge = el("rt-badge-" + cfg.key);
      const bar = el("rt-bar-" + cfg.key);

      if (typeof v === "number" && !isNaN(v)) {
        if (valEl) {
          valEl.textContent = cfg.key === "rpm" 
            ? Math.round(v).toLocaleString() 
            : v.toFixed(cfg.key === "engineLoad" ? 0 : (cfg.key === "oilPressure" || cfg.key === "vibration" || cfg.key === "fuelFlow" ? 2 : 1));
        }

        const isOil = cfg.key === "oilPressure";
        const isCrit = isOil ? v < cfg.crit : v > cfg.crit;
        const isWarn = isOil ? v < cfg.warn : v > cfg.warn;

        if (badge) {
          badge.textContent = isCrit ? "CRITICAL" : isWarn ? "WARNING" : "NORMAL";
          badge.className = "rt-status-badge " + (isCrit ? "crit" : isWarn ? "warn" : "ok");
        }

        if (bar) {
          const pct = Math.round(((v - cfg.min) / (cfg.max - cfg.min)) * 100);
          bar.style.width = Math.max(0, Math.min(100, pct)) + "%";
          bar.style.background = isCrit ? "#EF4444" : isWarn ? "#F59E0B" : cfg.color;
        }
      } else {
        if (valEl) valEl.textContent = "N/A";
        if (badge) { badge.textContent = "NO DATA"; badge.className = "rt-status-badge offline"; }
        if (bar) { bar.style.width = "0%"; }
      }
    });

    // Summary Strip
    if (el("rt-summary-rpm")) {
      el("rt-summary-rpm").textContent = typeof state.rpm === "number" ? `${Math.round(state.rpm).toLocaleString()} RPM` : "N/A";
    }
    if (el("rt-summary-temp")) {
      el("rt-summary-temp").textContent = typeof state.temperature === "number" ? `${state.temperature.toFixed(1)} °C` : "N/A";
    }
    if (el("rt-summary-oil")) {
      el("rt-summary-oil").textContent = typeof state.oilPressure === "number" ? `${state.oilPressure.toFixed(2)} Bar` : "N/A";
    }
    if (el("rt-summary-vib")) {
      el("rt-summary-vib").textContent = typeof state.vibration === "number" ? `${state.vibration.toFixed(2)} mm/s` : "N/A";
    }
    if (el("rt-health-val")) {
      el("rt-health-val").textContent = typeof state.engineHealth === "number" ? `${state.engineHealth}%` : "--";
    }

    // Rate & Status
    const ageStr = dataAgeMs !== null ? `${Math.round(dataAgeMs)} ms` : "--";
    const nowTime = new Date().toTimeString().slice(0, 8);
    if (el("rt-data-rate")) {
      el("rt-data-rate").textContent = `${nowTime} · ${source} · AGE: ${ageStr}`;
    }

    if (el("rt-summary-status")) {
      const overall = status.toUpperCase();
      el("rt-summary-status").textContent = overall;
      const stClass = (overall === "NORMAL" || overall === "LIVE" || overall === "CONNECTED") ? "normal"
                    : (overall === "WARNING" || overall === "STALE" || overall === "SIMULATION" || overall === "SIMULATED") ? "warning"
                    : (overall === "CRITICAL" || overall === "FAULT") ? "critical"
                    : "offline";
      el("rt-summary-status").className = "rt-overall-badge " + stClass;
    }
  }
}

export { SENSOR_CONFIGS };
