/**
 * AI Prognostics Engine
 * Data-driven fault rules replace repetitive if/else chains.
 */

// Each rule: { test(state), issue, risk, confidence(state), rul, actions, alertText, alertLevel }
const FAULT_RULES = [
  {
    test: s => s.oilPressure < 3.2 || s.activeScenario === 'lubrication_degradation',
    issue: 'Lubrication System Degradation',
    risk:  s => s.oilPressure < 2.5 ? 'HIGH' : 'MEDIUM',
    confidence: s => Math.min(99, Math.max(72, Math.round(76 + (3.8 - s.oilPressure) * 15))),
    rul: '01:15:30',
    actions: ['Inspect oil pressure system', 'Check lubrication circuit', 'Limit throttle demand to 65%'],
    alertText: 'Motor Current Drop', alertLevel: 'warning',
    probs: { nominal:0.08, lubrication:0.84, bearing:0.05, thermal:0.02, misfire:0.01 },
  },
  {
    test: s => s.vibration > 3.5 || s.activeScenario === 'vibration_bearing',
    issue: 'Crankshaft Bearing Wear / Imbalance',
    risk:  s => s.vibration > 4.5 ? 'HIGH' : 'MEDIUM',
    confidence: s => Math.min(99, Math.round(82 + (s.vibration - 3.5) * 8)),
    rul: '00:45:12',
    actions: ['Reduce engine RPM below 4000', 'Prepare emergency glide waypoint', 'Schedule bearing inspection'],
    alertText: 'Excessive Engine Vibration', alertLevel: 'critical',
    probs: { nominal:0.05, lubrication:0.04, bearing:0.88, thermal:0.02, misfire:0.01 },
  },
  {
    test: s => s.temperature > 90 || s.activeScenario === 'thermal_overheat',
    issue: 'Cylinder Head Thermal Stress',
    risk:  s => s.temperature > 95 ? 'HIGH' : 'MEDIUM',
    confidence: s => Math.min(99, Math.round(85 + (s.temperature - 90) * 2.5)),
    rul: '00:28:45',
    actions: ['Open cowl cooling flaps 100%', 'Enrich air-fuel mixture', 'Descend for cooler air'],
    alertText: 'Motor Coil Temperature Critical', alertLevel: 'critical',
    probs: { nominal:0.04, lubrication:0.03, bearing:0.03, thermal:0.89, misfire:0.01 },
  },
  {
    test: s => s.activeScenario === 'spark_misfire',
    issue: 'Spark Plug Ignition Misfire',
    risk:  () => 'MEDIUM',
    confidence: () => 88,
    rul: '02:10:00',
    actions: ['Switch to secondary magneto', 'Verify injection rail pressure', 'Avoid high climb power'],
    alertText: 'Phase Desync Detected', alertLevel: 'warning',
    probs: { nominal:0.06, lubrication:0.02, bearing:0.04, thermal:0.03, misfire:0.85 },
  },
  {
    test: s => s.activeScenario === 'high_altitude_climb',
    issue: 'High Load Thermal Accumulation',
    risk:  () => 'LOW',
    confidence: () => 92,
    rul: '04:30:00',
    actions: ['Level off at cruise altitude', 'Trim throttle for optimal SFC'],
    alertText: null,
    probs: { nominal:0.88, lubrication:0.03, bearing:0.03, thermal:0.05, misfire:0.01 },
  },
];

const NOMINAL = {
  issue: 'All Systems Nominal', risk: 'LOW', confidence: 96,
  rul: 'N/A (Nominal)',
  actions: ['Continue standard flight plan', 'Monitor 50Hz telemetry'],
  probs: { nominal:0.96, lubrication:0.01, bearing:0.01, thermal:0.01, misfire:0.01 },
};

export class AIPredictor {
  constructor() {
    this.alerts = [
      { id: 1, text: 'Motor Current Drop', level: 'warning', time: '10:24:15' },
      { id: 2, text: 'Vibration Increasing',       level: 'warning', time: '10:23:50' },
    ];
    this.events = [
      { id: 1, text: 'Data Updated',              time: '10:25:00', type: 'info' },
      { id: 2, text: 'Warning: Current Drop', time: '10:24:15', type: 'warning' },
      { id: 3, text: 'Vibration Rising',           time: '10:23:50', type: 'warning' },
      { id: 4, text: 'System Check OK',            time: '10:20:00', type: 'info' },
    ];
    this.lastInference = null;
  }

  _now() { return new Date().toTimeString().slice(0, 8); }

  analyze(state) {
    const rule = FAULT_RULES.find(r => r.test(state)) ?? null;
    const src  = rule ?? NOMINAL;

    if (rule?.alertText) this._upsertAlert(rule.alertText, rule.alertLevel);

    this.lastInference = {
      possibleIssue:       src.issue,
      riskLevel:           typeof src.risk === 'function' ? src.risk(state) : src.risk,
      confidence:          typeof src.confidence === 'function' ? src.confidence(state) : src.confidence,
      estimatedTimeToFault:src.rul,
      recommendedAction:   src.actions,
      probabilities:       src.probs,
      anomalyScore:        this._anomalyScore(state),
    };
    return this.lastInference;
  }

  _anomalyScore(s) {
    const baseline = { rpm:4215, temperature:78.4, oilPressure:4.3, vibration:1.6, fuelFlow:5.2, engineLoad:62 };
    const scales   = { rpm:800,  temperature:12,   oilPressure:1.2, vibration:1.5, fuelFlow:2.0, engineLoad:20 };
    const sq = Object.keys(baseline).reduce((acc, k) => acc + ((s[k] - baseline[k]) / scales[k]) ** 2, 0);
    return Math.min(1, Math.sqrt(sq) / 3).toFixed(4);
  }

  _upsertAlert(text, level) {
    if (this.alerts.some(a => a.text === text)) return;
    const t = this._now();
    this.alerts.unshift({ id: Date.now(), text, level, time: t });
    if (this.alerts.length > 8) this.alerts.pop();
    this.addEvent(`${level === 'critical' ? 'CRITICAL' : 'Warning'}: ${text}`, level);
  }

  addEvent(text, type = 'info') {
    this.events.unshift({ id: Date.now(), text, time: this._now(), type });
    if (this.events.length > 20) this.events.pop();
  }
}
