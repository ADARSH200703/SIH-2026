/**
 * Aero Piston Engine Telemetry Simulator
 * Scenario targets are data-driven — no switch/case needed.
 */

// Scenario target parameters lookup table
const SCENARIOS = {
  cruise:                  { rpm: 4215, temperature: 78.4, oilPressure: 4.3, vibration: 1.6, fuelFlow: 5.2, engineLoad: 62 },
  lubrication_degradation: { rpm: 4180, temperature: 86.8, oilPressure: 2.6, vibration: 2.7, fuelFlow: 5.6, engineLoad: 68 },
  vibration_bearing:       { rpm: 4260, temperature: 81.2, oilPressure: 3.9, vibration: 4.6, fuelFlow: 5.4, engineLoad: 65 },
  thermal_overheat:        { rpm: 4450, temperature: 97.5, oilPressure: 3.2, vibration: 3.1, fuelFlow: 6.4, engineLoad: 88 },
  spark_misfire:           { rpm: 3920, temperature: 82.0, oilPressure: 4.1, vibration: 3.5, fuelFlow: 6.9, engineLoad: 74 },
  high_altitude_climb:     { rpm: 4850, temperature: 84.6, oilPressure: 4.5, vibration: 2.2, fuelFlow: 7.6, engineLoad: 94 },
};

// Physical min/max clamps per parameter
const CLAMPS = {
  rpm:        [800,  6500],
  temperature:[20,   130 ],
  oilPressure:[0.5,  8.0 ],
  vibration:  [0.2,  10.0],
  fuelFlow:   [0,    15.0],
  engineLoad: [0,    100 ],
};

const clamp = (v, [min, max]) => Math.max(min, Math.min(max, v));
const noise = (amp) => (Math.random() * 2 - 1) * amp;

export class EngineSimulator {
  constructor() {
    this.state = {
      rpm: 4215, temperature: 78.4, oilPressure: 4.3,
      vibration: 1.6, fuelFlow: 5.2, engineLoad: 62,
      flightTimeSeconds: 9918,
      engineHealth: 87, missionReliability: 92,
      status: 'NORMAL',
      activeScenario: 'cruise',
      manualOverride: false, isRunning: true,
      components: {
        cylinder:          { health: 91, temp: 79.2, wear: 8.5 },
        piston:            { health: 88, temp: 82.1, wear: 11.2 },
        crankshaft:        { health: 94, vibration: 1.4, strain: 12.0 },
        valve:             { health: 89, clearance: 0.25, wear: 9.8 },
        sparkPlug:         { health: 86, gap: 0.65, misfires: 0 },
        fuelSystem:        { health: 93, pressure: 3.2, flow: 5.2 },
        lubricationSystem: { health: 82, pressure: 4.3, temp: 76.5 },
        coolingSystem:     { health: 90, flowRate: 14.2, temp: 74.0 },
      },
    };

    this.history = {
      labels: [], rpm: [], temperature: [], oilPressure: [],
      vibration: [], fuelFlow: [], engineLoad: [],
    };
    this.subscribers = new Set();
    this.eventLog    = [];   // { time, type, message, values }
    this.sessionStats = {};  // min/max/avg per param
    this._statsCounts = {};
    for (const k of ['rpm','temperature','oilPressure','vibration','fuelFlow','engineLoad']) {
      this.sessionStats[k] = { min: Infinity, max: -Infinity, sum: 0, count: 0 };
    }
    this._lastStatus = 'NORMAL';
    this.speedMultiplier = 1;
    this.state.isRunning = false;
    this._initHistory();
  }

  start() {
    this.state.isRunning = true;
    this._startTick();
  }

  stop() {
    this.state.isRunning = false;
    clearInterval(this._interval);
  }

  _initHistory() {
    this.history = {
      labels: [], rpm: [], temperature: [], oilPressure: [],
      vibration: [], fuelFlow: [], engineLoad: [],
    };
  }

  _startTick() {
    clearInterval(this._interval);
    if (!this.state.isRunning) return;
    const intervalMs = Math.max(150, Math.round(1000 / (this.speedMultiplier || 1)));
    this._interval = setInterval(() => this.tick(), intervalMs);
  }

  setSpeed(multiplier = 1) {
    this.speedMultiplier = multiplier;
    if (this.state.isRunning) {
      this._startTick();
    }
  }

  setScenario(name) {
    this.state.activeScenario = name;
    this.state.manualOverride = false;
    this.notify();
  }

  setManualParameter(param, value) {
    this.state.manualOverride = true;
    this.state[param] = parseFloat(value);
    this._updateHealth();
    this.notify();
  }

  executeMitigation() {
    const fixes = {
      lubrication_degradation: { oilPressure: 4.1, temperature: 79.5, vibration: 1.7 },
      thermal_overheat:        { engineLoad: 55, temperature: 80.2 },
      vibration_bearing:       { rpm: 3800, vibration: 2.1 },
      spark_misfire:           { rpm: 4150, fuelFlow: 5.3 },
    };
    Object.assign(this.state, fixes[this.state.activeScenario] ?? {});
    this.state.activeScenario = 'cruise';
    this._updateHealth();
    this.notify();
  }

  resetFlightTime(seconds = 0) {
    this.state.flightTimeSeconds = Math.max(0, seconds);
    this.notify();
  }


  tick() {
    if (!this.state.isRunning) return;
    this.state.flightTimeSeconds++;

    if (!this.state.manualOverride) {
      const target = { ...(SCENARIOS[this.state.activeScenario] ?? SCENARIOS.cruise) };
      // Add misfire jitter to RPM
      if (this.state.activeScenario === 'spark_misfire') target.rpm += noise(150);

      const lerp = { rpm: 0.15, temperature: 0.1, oilPressure: 0.1, vibration: 0.15, fuelFlow: 0.1, engineLoad: 0.1 };
      const noises = { rpm: 7, temperature: 0.15, oilPressure: 0.02, vibration: 0.04, fuelFlow: 0.03, engineLoad: 0.2 };

      for (const param of Object.keys(lerp)) {
        this.state[param] += (target[param] - this.state[param]) * lerp[param] + noise(noises[param]);
      }

      // Component degradation side-effects
      const comp = this.state.components;
      if (this.state.activeScenario === 'lubrication_degradation')
        comp.lubricationSystem.health = Math.max(38, comp.lubricationSystem.health - 0.1);
      if (this.state.activeScenario === 'vibration_bearing')
        comp.crankshaft.health = Math.max(45, comp.crankshaft.health - 0.15);
      if (this.state.activeScenario === 'thermal_overheat')
        comp.coolingSystem.health = Math.max(40, comp.coolingSystem.health - 0.2);
      if (this.state.activeScenario === 'spark_misfire') {
        comp.sparkPlug.health = Math.max(32, comp.sparkPlug.health - 0.2);
        comp.sparkPlug.misfires++;
      }
    } else {
      // Light noise on manual-set values
      this.state.rpm        += noise(3);
      this.state.temperature += noise(0.05);
      this.state.oilPressure += noise(0.01);
      this.state.vibration  += noise(0.02);
    }

    // Clamp all parameters
    for (const [param, range] of Object.entries(CLAMPS)) {
      this.state[param] = clamp(this.state[param], range);
    }

    this._updateHealth();
    this._pushHistory();
    this.notify();
  }

  _pushHistory() {
    const SIZE = 60;
    this.history.labels = Array.from({ length: SIZE }, (_, i) => (-(SIZE - 1 - i) * 5 / 60).toFixed(1));
    for (const key of ['rpm', 'temperature', 'oilPressure', 'vibration', 'fuelFlow', 'engineLoad']) {
      this.history[key].shift();
      this.history[key].push(this.state[key]);
      // Update session stats
      const s = this.sessionStats[key];
      const v = this.state[key];
      s.min = Math.min(s.min, v);
      s.max = Math.max(s.max, v);
      s.sum += v;
      s.count++;
    }
    // Log status transitions as events
    if (this.state.status !== this._lastStatus) {
      this.logEvent(
        this.state.status === 'NORMAL' ? 'info' : this.state.status === 'WARNING' ? 'warning' : 'critical',
        `Engine status changed: ${this._lastStatus} → ${this.state.status}`,
      );
      this._lastStatus = this.state.status;
    }
  }

  logEvent(type, message) {
    const now = new Date();
    this.eventLog.unshift({
      id:   Date.now(),
      time: now.toTimeString().slice(0, 8),
      date: now.toLocaleDateString(),
      type,   // 'info' | 'warning' | 'critical'
      message,
      snapshot: {
        rpm:         +this.state.rpm.toFixed(1),
        temperature: +this.state.temperature.toFixed(1),
        oilPressure: +this.state.oilPressure.toFixed(1),
        vibration:   +this.state.vibration.toFixed(1),
        engineHealth: this.state.engineHealth,
      },
    });
    if (this.eventLog.length > 200) this.eventLog.pop();
  }

  getSessionStats() {
    const result = {};
    for (const [k, s] of Object.entries(this.sessionStats)) {
      result[k] = {
        min: s.min === Infinity ? 0 : +s.min.toFixed(2),
        max: s.max === -Infinity ? 0 : +s.max.toFixed(2),
        avg: s.count > 0 ? +(s.sum / s.count).toFixed(2) : 0,
      };
    }
    return result;
  }

  _updateHealth() {
    const { oilPressure, temperature, vibration, rpm } = this.state;
    let penalty = 0;
    if (oilPressure < 3.0)   penalty += 28; else if (oilPressure < 3.8) penalty += 12;
    if (temperature > 92)    penalty += 32; else if (temperature > 84)   penalty += 14;
    if (vibration > 4.0)     penalty += 35; else if (vibration > 2.4)    penalty += 16;
    if (rpm > 5500)          penalty += 18;

    this.state.engineHealth      = clamp(Math.round(96 - penalty), [15, 99]);
    this.state.missionReliability = clamp(Math.round(this.state.engineHealth * 1.05 - vibration * 2), [20, 99]);

    const h = this.state.engineHealth;
    this.state.status = (h >= 80 && oilPressure >= 3.6 && temperature <= 85 && vibration <= 2.5) ? 'NORMAL'
                      : (h >= 50 && oilPressure >= 2.5 && temperature <= 93 && vibration <= 3.8) ? 'WARNING'
                      : 'CRITICAL';
  }

  getFormattedFlightTime() {
    const d = new Date(this.state.flightTimeSeconds * 1000);
    // toISOString gives HH:MM:SS at the right offset
    return new Date(this.state.flightTimeSeconds * 1000).toISOString().slice(11, 19);
  }

  subscribe(cb) {
    this.subscribers.add(cb);
    return () => this.subscribers.delete(cb);
  }

  notify() { this.subscribers.forEach(cb => cb(this.state, this.history)); }
}
