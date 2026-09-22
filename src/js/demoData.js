export function startDemoData(updateFn) {
  console.log("Starting AERIS-TWIN Demo Data Generator");

  let baseRpm = 4150;
  let baseTemp = 78.0;
  let baseVibration = 1.2;
  let baseHealth = 94.0;
  let baseOilPressure = 4.2;
  let baseLoad = 62;
  let baseFuelFlow = 21.4;

  let tick = 0;
  let inAlertPhase = false;
  let alertTimer = 0;

  setInterval(() => {
    tick += 0.05;
    alertTimer++;

    // Occasional Demo Alert every ~45 seconds (450 ticks at 100ms)
    if (alertTimer > 450 && !inAlertPhase) {
      inAlertPhase = true;
      alertTimer = 0;
    } else if (inAlertPhase && alertTimer > 150) {
      // Recover after 15 seconds
      inAlertPhase = false;
      alertTimer = 0;
    }

    if (inAlertPhase) {
      // Simulate degrading conditions
      baseTemp = Math.min(baseTemp + 0.1, 88.0);
      baseVibration = Math.min(baseVibration + 0.02, 2.4);
      baseHealth = Math.max(baseHealth - 0.1, 82.0);
    } else {
      // Recover baseline
      baseTemp = Math.max(baseTemp - 0.05, 78.0);
      baseVibration = Math.max(baseVibration - 0.01, 1.2);
      baseHealth = Math.min(baseHealth + 0.05, 94.0);
    }

    // Add some sine wave + small random noise
    const rpm = Math.floor(baseRpm + Math.sin(tick * 2) * 150 + (Math.random() * 40 - 20));
    const temperature = baseTemp + Math.sin(tick * 0.5) * 2 + (Math.random() * 1 - 0.5);
    const vibration = baseVibration + Math.sin(tick * 0.8) * 0.2 + (Math.random() * 0.1);
    const engineHealth = baseHealth + Math.sin(tick * 0.2) * 1 + (Math.random() * 0.5);
    const fuelFlow = baseFuelFlow + Math.sin(tick * 0.3) * 1.5 + (Math.random() * 0.5);
    const engineLoad = baseLoad + Math.sin(tick * 0.4) * 5 + (Math.random() * 3);
    const oilPressure = baseOilPressure + Math.sin(tick * 0.6) * 0.2 + (Math.random() * 0.05);

    // Create a realistic telemetry frame matching what the frontend expects
    const frame = {
      rpm: rpm,
      temperature: Number(temperature.toFixed(1)),
      vibration: Number(vibration.toFixed(2)),
      engine_health: Number(engineHealth.toFixed(1)),
      fuel_flow: Number(fuelFlow.toFixed(1)),
      engine_load: Math.floor(engineLoad),
      oil_pressure: Number(oilPressure.toFixed(2)),
      status: inAlertPhase ? 'WARNING' : 'NORMAL'
    };

    // Trigger demo alert popup via synthetic packet if needed
    // (the frontend will pick this up automatically via the health value and vibration)

    // Feed it to the dashboard
    if (typeof updateFn === 'function') {
      // Pass as SIMULATION/LIVE based on existing architecture expecting LIVE to show graphs normally
      updateFn(frame, 'SIMULATION', inAlertPhase ? 'WARNING' : 'LIVE');
    }
  }, 100); // update every 100ms
}
