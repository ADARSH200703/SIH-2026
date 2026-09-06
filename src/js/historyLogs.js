export class HistoryLogs {
  constructor(simRef) {
    this.sim = simRef;
    this._filter = "all";   // all | info | warning | critical
    this._backendEvents = [];
  }

  setFilter(f) { this._filter = f; this.render(); }

  setBackendEvents(events) {
    this._backendEvents = events || [];
    this.render();
  }

  addBackendEvent(event) {
    if (!event) return;
    this._backendEvents.unshift(event);
    if (this._backendEvents.length > 100) this._backendEvents.pop();
    this.render();
  }

  render() {
    this._renderStats();
    this._renderTimeline();
    this._renderComponentTable();
  }

  _renderStats() {
    const stats = this.sim.getSessionStats();
    const PARAMS = [
      { key: "rpm",         label: "Engine RPM",    unit: "RPM",    decimals: 0 },
      { key: "temperature", label: "Temperature",   unit: "°C",     decimals: 1 },
      { key: "oilPressure", label: "Oil Pressure",  unit: "Bar",    decimals: 2 },
      { key: "vibration",   label: "Vibration",     unit: "mm/s",   decimals: 2 },
      { key: "fuelFlow",    label: "Fuel Flow",      unit: "L/h",    decimals: 1 },
      { key: "engineLoad",  label: "Engine Load",   unit: "%",      decimals: 0 },
    ];
    const el = document.getElementById("hist-stats-grid");
    if (!el) return;
    el.innerHTML = PARAMS.map(p => {
      const s = stats[p.key] || { min: 0, max: 0, avg: 0 };
      const fmt = v => p.decimals === 0 ? Math.round(v).toLocaleString() : v.toFixed(p.decimals);
      return `
        <div class='hist-stat-card'>
          <div class='hist-stat-label'>${p.label} <span class='hist-unit'>${p.unit}</span></div>
          <div class='hist-stat-row'>
            <div class='hist-stat-box'><div class='hist-stat-box-label'>MIN</div><div class='hist-stat-box-val cyan'>${fmt(s.min)}</div></div>
            <div class='hist-stat-box'><div class='hist-stat-box-label'>AVG</div><div class='hist-stat-box-val white'>${fmt(s.avg)}</div></div>
            <div class='hist-stat-box'><div class='hist-stat-box-label'>MAX</div><div class='hist-stat-box-val orange'>${fmt(s.max)}</div></div>
          </div>
        </div>`;
    }).join("");
  }

  _renderTimeline() {
    const container = document.getElementById("hist-timeline");
    if (!container) return;

    // Combine local sim events and backend events
    const allEvents = [...(this._backendEvents || []), ...(this.sim.eventLog || [])];
    // Deduplicate by message + time if present
    const seen = new Set();
    const uniqueEvents = allEvents.filter(e => {
      const k = `${e.time}-${e.message || e.text}`;
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });

    const filtered = this._filter === "all"
      ? uniqueEvents
      : uniqueEvents.filter(e => (e.type || e.level) === this._filter);

    if (filtered.length === 0) {
      container.innerHTML = "<div class='hist-empty'>No events recorded yet. Events are logged automatically when engine status changes or faults are detected.</div>";
      return;
    }

    container.innerHTML = filtered.map(e => {
      const type = e.type || e.level || "info";
      const icon = type === "critical" ? "error" : type === "warning" ? "warning" : "info";
      const msg = e.message || e.text || "Status Update";
      const snap = e.snapshot ? `<span class='hist-snap'>RPM ${e.snapshot.rpm} · ${e.snapshot.temperature}°C · Oil ${e.snapshot.oilPressure} Bar · Vib ${e.snapshot.vibration} mm/s · Health ${e.snapshot.engineHealth}%</span>` : "";
      return `
        <div class='hist-event-row ${type}'>
          <div class='hist-event-icon'><span class="material-symbols-outlined" style="font-size:18px;">${icon}</span></div>
          <div class='hist-event-body'>
            <div class='hist-event-msg'>${msg}</div>
            ${snap}
          </div>
          <div class='hist-event-time'>${e.date || ''}<br>${e.time || ''}</div>
        </div>`;
    }).join("");
  }

  _renderComponentTable() {
    const comp = this.sim.state.components;
    const rows = [
      { name: "Cylinder Assembly",        health: comp.cylinder.health,          wear: comp.cylinder.wear,            extra: comp.cylinder.temp.toFixed(1) + " °C" },
      { name: "Piston Assemblies",        health: comp.piston.health,            wear: comp.piston.wear,              extra: comp.piston.temp.toFixed(1) + " °C" },
      { name: "Crankshaft & Bearings",    health: comp.crankshaft.health,        wear: comp.crankshaft.strain,        extra: comp.crankshaft.vibration.toFixed(2) + " mm/s" },
      { name: "Intake/Exhaust Valves",    health: comp.valve.health,             wear: comp.valve.wear,               extra: comp.valve.clearance.toFixed(3) + " mm" },
      { name: "Spark Plugs",              health: comp.sparkPlug.health,         wear: comp.sparkPlug.misfires,       extra: comp.sparkPlug.gap.toFixed(2) + " mm gap" },
      { name: "Fuel Injection System",    health: comp.fuelSystem.health,        wear: comp.fuelSystem.pressure,      extra: comp.fuelSystem.flow.toFixed(1) + " L/h" },
      { name: "Lubrication System",       health: comp.lubricationSystem.health, wear: comp.lubricationSystem.pressure, extra: comp.lubricationSystem.temp.toFixed(1) + " °C" },
      { name: "Cooling System",           health: comp.coolingSystem.health,     wear: comp.coolingSystem.flowRate,   extra: comp.coolingSystem.temp.toFixed(1) + " °C" },
    ];
    const el = document.getElementById("hist-comp-table-body");
    if (!el) return;
    el.innerHTML = rows.map(r => {
      const h = r.health;
      const color = h >= 80 ? "var(--status-normal)" : h >= 55 ? "var(--status-warning)" : "var(--status-critical)";
      const status = h >= 80 ? "Good" : h >= 55 ? "Degraded" : "Critical";
      return `
        <tr class='hist-comp-row'>
          <td>${r.name}</td>
          <td>
            <div class='hist-comp-health-row'>
              <div class='hist-comp-bar-bg'><div class='hist-comp-bar-fill' style='width:${h}%;background:${color};'></div></div>
              <span style='color:${color};font-weight:700;min-width:38px;'>${h.toFixed(1)}%</span>
            </div>
          </td>
          <td style='color:${color};font-weight:600;'>${status}</td>
          <td>${typeof r.wear === "number" ? r.wear.toFixed(1) : r.wear}</td>
          <td style='color:#94a3b8;'>${r.extra}</td>
        </tr>`;
    }).join("");
  }

  exportCSV(state) {
    const stats = this.sim.getSessionStats();
    const headers = ["Parameter","Min","Avg","Max","Current","Unit"];
    const PARAMS = [
      { key:"rpm", label:"Engine RPM", unit:"RPM", cur: Math.round(state.rpm) },
      { key:"temperature", label:"Temperature", unit:"°C", cur: state.temperature.toFixed(1) },
      { key:"oilPressure", label:"Oil Pressure", unit:"Bar", cur: state.oilPressure.toFixed(2) },
      { key:"vibration", label:"Vibration", unit:"mm/s", cur: state.vibration.toFixed(2) },
      { key:"fuelFlow", label:"Fuel Flow", unit:"L/h", cur: state.fuelFlow.toFixed(1) },
      { key:"engineLoad", label:"Engine Load", unit:"%", cur: Math.round(state.engineLoad) },
    ];
    const rows = PARAMS.map(p => {
      const s = stats[p.key] || { min:0, max:0, avg:0 };
      return [p.label, s.min, s.avg, s.max, p.cur, p.unit].join(",");
    });
    // Append event log
    const eventRows = ["\n\nEvent Log","Time","Type","Message"].join(",");
    const events = (this.sim.eventLog || []).map(e => [e.date + " " + e.time, e.type, '"' + e.message + '"'].join(",")).join("\n");
    const csv = [headers.join(","), ...rows, eventRows, events].join("\n");
    const a = Object.assign(document.createElement("a"), {
      href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })),
      download: "uav_engine_logs_" + Date.now() + ".csv",
    });
    document.body.appendChild(a); a.click(); a.remove();
  }
}
