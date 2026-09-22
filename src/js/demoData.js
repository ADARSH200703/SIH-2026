export function startDemoData(updateFn) {
  console.log("Starting AERIS-TWIN Realistic Demonstration Telemetry");

  // Physical State Variables
  let state = {
    rpm: 4200,
    load: 65,
    cht: 78.0,
    oilPress: 4.3,
    vib: 1.5,
    health: 96.0,
    fuel: 100.0,
  };

  // Base Targets for Nominal
  const nominal = {
    rpm: 4200,
    load: 65,
    cht: 78.0,
    oilPress: 4.3,
    vib: 1.5
  };

  // Scenarios
  const SCENARIOS = ['NORMAL', 'HIGH_LOAD', 'NORMAL', 'THERMAL_EVENT', 'NORMAL', 'VIB_EVENT', 'NORMAL'];
  let currentScenarioIdx = 0;
  let scenarioTicks = 0;
  
  // A "tick" is 100ms. 
  // NORMAL: 450 - 900 ticks (45-90s)
  // EVENT: 150 - 250 ticks (15-25s)
  let targetTicksForScenario = 600;

  function getNextScenario() {
    currentScenarioIdx = (currentScenarioIdx + 1) % SCENARIOS.length;
    scenarioTicks = 0;
    const s = SCENARIOS[currentScenarioIdx];
    if (s === 'NORMAL') {
      targetTicksForScenario = 450 + Math.floor(Math.random() * 450);
    } else {
      targetTicksForScenario = 150 + Math.floor(Math.random() * 100);
    }
    console.log(`[DemoData] Transitioned to ${s} for ${targetTicksForScenario / 10} seconds`);
  }

  setInterval(() => {
    scenarioTicks++;
    if (scenarioTicks > targetTicksForScenario) {
      getNextScenario();
    }

    const currentScenario = SCENARIOS[currentScenarioIdx];

    // Determine target values based on scenario
    let targetRpm = nominal.rpm;
    let targetLoad = nominal.load;
    let targetCht = nominal.cht;
    let targetVib = nominal.vib;
    let targetOil = nominal.oilPress;
    let targetHealth = 96.0;
    let alertStatus = 'NORMAL';

    // Fuel always decreases slowly
    state.fuel = Math.max(0, state.fuel - 0.005);

    // Apply Scenario Targets
    if (currentScenario === 'HIGH_LOAD') {
      targetLoad = 92;
      targetRpm = 5800;
      targetCht = 86.0; 
      targetVib = 2.0; // Higher RPM means slightly more vib naturally
      targetHealth = 92.0; // Health is still OK, just stressed
    } else if (currentScenario === 'THERMAL_EVENT') {
      targetCht = 105.0; // Overheat
      targetOil = 3.6;   // Oil pressure drops due to heat/viscosity loss
      targetHealth = 78.0; 
      alertStatus = 'WARNING';
    } else if (currentScenario === 'VIB_EVENT') {
      targetVib = 3.8;   // Heavy bearing wear vibration
      targetHealth = 74.0;
      alertStatus = 'CRITICAL';
    }

    // Add noise and physical correlation
    // RPM hunts slightly
    const rpmNoise = Math.sin(scenarioTicks * 0.1) * 20 + (Math.random() * 10 - 5);
    // Smooth transition towards targets (Inertia)
    state.rpm += (targetRpm - state.rpm) * 0.05; 
    state.load += (targetLoad - state.load) * 0.1;
    state.cht += (targetCht - state.cht) * 0.02; // Temperature changes slowly
    state.vib += (targetVib - state.vib) * 0.1;
    state.oilPress += (targetOil - state.oilPress) * 0.05;
    state.health += (targetHealth - state.health) * 0.05;

    // Construct final frame with sensor noise
    const finalRpm = state.rpm + rpmNoise;
    // Load correlates to RPM
    const finalLoad = state.load + (Math.random() * 2 - 1);
    const finalCht = state.cht + Math.sin(scenarioTicks * 0.05) * 0.5 + (Math.random() * 0.2 - 0.1);
    // Vibration correlates to RPM slightly
    const vibRpmFactor = (finalRpm - 4000) / 2000 * 0.2; 
    const finalVib = state.vib + vibRpmFactor + Math.sin(scenarioTicks * 0.2) * 0.1 + (Math.random() * 0.05);
    const finalOil = state.oilPress + (Math.random() * 0.02 - 0.01);
    const finalHealth = state.health + (Math.random() * 0.4 - 0.2);
    
    // RUL decreases linearly but takes a hit on health drops
    const baseRul = 1200 - (100 - state.fuel) * 2; // Simple baseline
    const healthPenalty = (100 - finalHealth) * 5;
    const currentRul = Math.max(0, baseRul - healthPenalty);

    const frame = {
      rpm: Math.floor(finalRpm),
      temperature: Number(finalCht.toFixed(1)),
      vibration: Number(finalVib.toFixed(2)),
      engine_health: Number(finalHealth.toFixed(1)),
      fuel_flow: Number((12.4 + (finalLoad / 100) * 8).toFixed(1)), // Fuel flow correlates to load
      engine_load: Math.floor(finalLoad),
      oil_pressure: Number(finalOil.toFixed(2)),
      rul_estimate: Number(currentRul.toFixed(1)),
      status: alertStatus,
      scenario: currentScenario // Expose scenario for potential frontend logic
    };

    if (typeof updateFn === 'function') {
      // Feed data as if it were LIVE to trigger normal UI rendering
      updateFn(frame, 'LIVE', alertStatus);
    }
  }, 100);
}
