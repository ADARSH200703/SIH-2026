import React from 'react';
import { 
  Gauge, 
  Flame, 
  Droplet, 
  Zap, 
  Fuel, 
  Activity, 
  CheckCircle2, 
  AlertTriangle, 
  Thermometer, 
  Compass, 
  Cpu 
} from 'lucide-react';
import { TelemetryState } from '../types/uav';

interface AvionicsHealthPanelProps {
  telemetry: TelemetryState;
}

export const AvionicsHealthPanel: React.FC<AvionicsHealthPanelProps> = ({ telemetry }) => {
  const {
    rpm,
    chtC,
    egtC,
    oilPressureBar,
    oilTempC,
    mapInHg,
    engineHealthPct,
    engineLoadPct,
    generatorVoltageV,
    batteryVoltageV,
    busCurrentA,
    batterySoCPct,
    fuelRemainingLiters,
    fuelCapacityLiters,
    fuelFlowLitersHr,
    bingoFuelThresholdLiters,
    aileronLeftDeg,
    aileronRightDeg,
    elevatorDeg,
    rudderDeg,
    flapsDeg,
    gearState,
    pitotHeatActive,
    avionicsBayTempC,
    oatC,
  } = telemetry;

  const fuelPct = (fuelRemainingLiters / fuelCapacityLiters) * 100;
  const hoursToEmpty = fuelRemainingLiters / (fuelFlowLitersHr || 1);

  const isChtOverheat = chtC >= 140;
  const isEgtCaution = egtC >= 780;
  const isOilWarning = oilPressureBar < 2.2 || oilTempC > 115;

  return (
    <div className="w-full h-full bg-[#070A0F] border border-[#1E2C3D] rounded-md p-3 flex flex-col gap-3 select-none overflow-y-auto font-mono text-xs shadow-inner">
      {/* Top Banner: Digital Twin Engine State */}
      <div className="flex items-center justify-between bg-[#0B111A] border border-[#1E2C3D] px-3 py-1.5 rounded">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#00F2FF] animate-pulse" />
          <div>
            <div className="text-white font-bold text-[11px]">
              ROTAX 914-F TURBOCHARGED DIGITAL TWIN
            </div>
            <div className="text-[9px] text-slate-400">
              PHYSICS-INFORMED PROGNOSTICS & TELEMETRY ENGINE
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-[9px] text-slate-400">PROPULSION HEALTH:</div>
            <div className="text-sm font-bold text-[#10B981]">{engineHealthPct.toFixed(1)}% NOMINAL</div>
          </div>
          <div className="w-2.5 h-2.5 rounded-full bg-[#10B981] animate-ping" />
        </div>
      </div>

      {/* 1. TURBOCHARGED ENGINE PROPULSION GAUGES */}
      <div className="grid grid-cols-4 gap-2">
        {/* RPM & Load Gauge */}
        <div className="bg-[#0B111A] border border-[#1E2C3D] p-2 rounded flex flex-col justify-between">
          <div className="flex items-center justify-between text-[9px] text-slate-400">
            <span>ENGINE TACH:</span>
            <Gauge className="w-3.5 h-3.5 text-[#00F2FF]" />
          </div>
          <div className="text-center my-1">
            <div className="text-lg font-bold text-white tracking-wider">{Math.round(rpm)}</div>
            <div className="text-[9px] text-[#00F2FF] font-semibold">RPM ({engineLoadPct.toFixed(0)}% LOAD)</div>
          </div>
          <div className="w-full bg-[#1E2C3D] h-1.5 rounded-full overflow-hidden">
            <div className="h-full bg-[#00F2FF]" style={{ width: `${(rpm / 5800) * 100}%` }} />
          </div>
        </div>

        {/* Cylinder Head Temp (CHT) */}
        <div className={`p-2 rounded border flex flex-col justify-between ${
          isChtOverheat ? 'bg-[#EF4444]/15 border-[#EF4444]' : 'bg-[#0B111A] border-[#1E2C3D]'
        }`}>
          <div className="flex items-center justify-between text-[9px] text-slate-400">
            <span>CYLINDER HEAD (CHT):</span>
            <Thermometer className={`w-3.5 h-3.5 ${isChtOverheat ? 'text-[#EF4444]' : 'text-[#38BDF8]'}`} />
          </div>
          <div className="text-center my-1">
            <div className={`text-lg font-bold ${isChtOverheat ? 'text-[#EF4444]' : 'text-white'}`}>
              {chtC.toFixed(1)}°C
            </div>
            <div className="text-[9px] text-slate-400">NOMINAL &lt;135°C (RED 150°)</div>
          </div>
          <div className="w-full bg-[#1E2C3D] h-1.5 rounded-full overflow-hidden">
            <div
              className={`h-full ${isChtOverheat ? 'bg-[#EF4444]' : 'bg-[#38BDF8]'}`}
              style={{ width: `${Math.min(100, (chtC / 160) * 100)}%` }}
            />
          </div>
        </div>

        {/* Exhaust Gas Temp (EGT) */}
        <div className={`p-2 rounded border flex flex-col justify-between ${
          isEgtCaution ? 'bg-[#F59E0B]/15 border-[#F59E0B]' : 'bg-[#0B111A] border-[#1E2C3D]'
        }`}>
          <div className="flex items-center justify-between text-[9px] text-slate-400">
            <span>EXHAUST GAS (EGT):</span>
            <Flame className="w-3.5 h-3.5 text-[#F59E0B]" />
          </div>
          <div className="text-center my-1">
            <div className="text-lg font-bold text-white">{egtC.toFixed(0)}°C</div>
            <div className="text-[9px] text-slate-400">TURBO EXHAUST (MAX 850°)</div>
          </div>
          <div className="w-full bg-[#1E2C3D] h-1.5 rounded-full overflow-hidden">
            <div className="h-full bg-[#F59E0B]" style={{ width: `${(egtC / 900) * 100}%` }} />
          </div>
        </div>

        {/* Manifold Absolute Pressure (MAP Turbo Boost) */}
        <div className="bg-[#0B111A] border border-[#1E2C3D] p-2 rounded flex flex-col justify-between">
          <div className="flex items-center justify-between text-[9px] text-slate-400">
            <span>TURBO BOOST (MAP):</span>
            <Droplet className="w-3.5 h-3.5 text-[#10B981]" />
          </div>
          <div className="text-center my-1">
            <div className="text-lg font-bold text-white">{mapInHg.toFixed(1)} <span className="text-xs text-slate-400">inHg</span></div>
            <div className="text-[9px] text-[#10B981]">WASTEGATE REGULATED</div>
          </div>
          <div className="w-full bg-[#1E2C3D] h-1.5 rounded-full overflow-hidden">
            <div className="h-full bg-[#10B981]" style={{ width: `${(mapInHg / 45) * 100}%` }} />
          </div>
        </div>
      </div>

      {/* 2. ELECTRICAL POWER FLOW & FUEL SUBSYSTEM */}
      <div className="grid grid-cols-2 gap-2">
        {/* Dual Power Flow Bus */}
        <div className="bg-[#0B111A] border border-[#1E2C3D] p-2.5 rounded">
          <div className="flex items-center justify-between border-b border-[#1E2C3D] pb-1 mb-2 text-[10px]">
            <div className="flex items-center gap-1.5 text-white font-bold">
              <Zap className="w-3.5 h-3.5 text-[#F59E0B]" />
              <span>28V DUAL DC ELECTRICAL POWER BUS</span>
            </div>
            <span className="text-[#10B981] font-bold">BUS_HEALTHY</span>
          </div>

          <div className="grid grid-cols-4 gap-1.5 text-center">
            <div className="bg-[#070A0F] p-1 rounded border border-[#1E2C3D]">
              <div className="text-[8px] text-slate-400">GEN 1 VOLTS</div>
              <div className="text-xs font-bold text-white">{generatorVoltageV.toFixed(1)} V</div>
            </div>
            <div className="bg-[#070A0F] p-1 rounded border border-[#1E2C3D]">
              <div className="text-[8px] text-slate-400">BATT BACKUP</div>
              <div className="text-xs font-bold text-white">{batteryVoltageV.toFixed(1)} V</div>
            </div>
            <div className="bg-[#070A0F] p-1 rounded border border-[#1E2C3D]">
              <div className="text-[8px] text-slate-400">TOTAL LOAD</div>
              <div className="text-xs font-bold text-[#38BDF8]">{busCurrentA.toFixed(1)} A</div>
            </div>
            <div className="bg-[#070A0F] p-1 rounded border border-[#1E2C3D]">
              <div className="text-[8px] text-slate-400">BATT SOC</div>
              <div className="text-xs font-bold text-[#10B981]">{batterySoCPct.toFixed(0)}%</div>
            </div>
          </div>
        </div>

        {/* Fuel Capacity & Burn Rate */}
        <div className="bg-[#0B111A] border border-[#1E2C3D] p-2.5 rounded">
          <div className="flex items-center justify-between border-b border-[#1E2C3D] pb-1 mb-2 text-[10px]">
            <div className="flex items-center gap-1.5 text-white font-bold">
              <Fuel className="w-3.5 h-3.5 text-[#00F2FF]" />
              <span>AVGAS 100LL FUEL SYSTEM</span>
            </div>
            <span className={`font-bold ${fuelRemainingLiters < bingoFuelThresholdLiters ? 'text-[#EF4444]' : 'text-[#00F2FF]'}`}>
              {fuelRemainingLiters < bingoFuelThresholdLiters ? 'BINGO FUEL REACHED' : 'SAFE ENDURANCE'}
            </span>
          </div>

          <div className="flex items-center justify-between gap-3">
            <div className="flex-1">
              <div className="flex justify-between text-[9px] mb-1">
                <span className="text-slate-400">REMAINING: {fuelRemainingLiters.toFixed(1)} / {fuelCapacityLiters} L</span>
                <span className="text-white font-bold">{fuelPct.toFixed(0)}%</span>
              </div>
              <div className="w-full bg-[#1E2C3D] h-2 rounded-full overflow-hidden">
                <div
                  className={`h-full ${fuelPct > 35 ? 'bg-[#10B981]' : fuelPct > 20 ? 'bg-[#F59E0B]' : 'bg-[#EF4444]'}`}
                  style={{ width: `${fuelPct}%` }}
                />
              </div>
            </div>
            <div className="text-right pl-2 border-l border-[#1E2C3D]">
              <div className="text-[8px] text-slate-400">BURN: {fuelFlowLitersHr.toFixed(1)} L/h</div>
              <div className="text-xs font-bold text-white">{hoursToEmpty.toFixed(1)}h ETE</div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. FLIGHT CONTROL SURFACES & LANDING GEAR / PITOT */}
      <div className="grid grid-cols-2 gap-2">
        {/* Actuator Surface Deflection Wireframe */}
        <div className="bg-[#0B111A] border border-[#1E2C3D] p-2.5 rounded">
          <div className="text-[10px] text-white font-bold border-b border-[#1E2C3D] pb-1 mb-2 flex items-center justify-between">
            <span>FLY-BY-WIRE ACTUATOR DEFLECTIONS</span>
            <span className="text-[9px] text-[#00F2FF]">QUAD-REDUNDANT</span>
          </div>

          <div className="grid grid-cols-5 gap-1 text-center font-mono text-[9px]">
            <div className="bg-[#070A0F] p-1.5 rounded border border-[#1E2C3D]">
              <div className="text-slate-400 text-[8px]">L AIL</div>
              <div className="text-white font-bold">{aileronLeftDeg > 0 ? `+${aileronLeftDeg}°` : `${aileronLeftDeg}°`}</div>
            </div>
            <div className="bg-[#070A0F] p-1.5 rounded border border-[#1E2C3D]">
              <div className="text-slate-400 text-[8px]">R AIL</div>
              <div className="text-white font-bold">{aileronRightDeg > 0 ? `+${aileronRightDeg}°` : `${aileronRightDeg}°`}</div>
            </div>
            <div className="bg-[#070A0F] p-1.5 rounded border border-[#1E2C3D]">
              <div className="text-slate-400 text-[8px]">ELEV</div>
              <div className="text-white font-bold">{elevatorDeg > 0 ? `+${elevatorDeg}°` : `${elevatorDeg}°`}</div>
            </div>
            <div className="bg-[#070A0F] p-1.5 rounded border border-[#1E2C3D]">
              <div className="text-slate-400 text-[8px]">RUDD</div>
              <div className="text-white font-bold">{rudderDeg > 0 ? `+${rudderDeg}°` : `${rudderDeg}°`}</div>
            </div>
            <div className="bg-[#070A0F] p-1.5 rounded border border-[#1E2C3D]">
              <div className="text-slate-400 text-[8px]">FLAP</div>
              <div className="text-white font-bold">{flapsDeg.toFixed(0)}°</div>
            </div>
          </div>
        </div>

        {/* 3-Green Landing Gear & Environmental */}
        <div className="bg-[#0B111A] border border-[#1E2C3D] p-2.5 rounded flex flex-col justify-between">
          <div className="text-[10px] text-white font-bold border-b border-[#1E2C3D] pb-1 mb-2 flex items-center justify-between">
            <span>LANDING GEAR & ENVIRONMENTAL</span>
            <span className="text-[9px] text-[#10B981]">BAY: {avionicsBayTempC.toFixed(1)}°C | OAT: {oatC.toFixed(1)}°C</span>
          </div>

          <div className="flex items-center justify-around">
            {/* 3-Green Lights */}
            <div className="flex items-center gap-2">
              <div className="flex flex-col items-center gap-1">
                <div className={`w-3 h-3 rounded-full ${gearState === 'LOCKED_DOWN' ? 'bg-[#10B981] shadow-[0_0_8px_#10B981]' : 'bg-[#1E2C3D]'}`} />
                <span className="text-[8px] text-slate-400">NOSE</span>
              </div>
              <div className="flex flex-col items-center gap-1">
                <div className={`w-3 h-3 rounded-full ${gearState === 'LOCKED_DOWN' ? 'bg-[#10B981] shadow-[0_0_8px_#10B981]' : 'bg-[#1E2C3D]'}`} />
                <span className="text-[8px] text-slate-400">L MAIN</span>
              </div>
              <div className="flex flex-col items-center gap-1">
                <div className={`w-3 h-3 rounded-full ${gearState === 'LOCKED_DOWN' ? 'bg-[#10B981] shadow-[0_0_8px_#10B981]' : 'bg-[#1E2C3D]'}`} />
                <span className="text-[8px] text-slate-400">R MAIN</span>
              </div>
            </div>

            {/* Pitot Heat */}
            <div className="pl-3 border-l border-[#1E2C3D] text-right">
              <div className="text-[8px] text-slate-400">PITOT ANTI-ICE:</div>
              <div className={`text-[10px] font-bold ${pitotHeatActive ? 'text-[#10B981]' : 'text-[#EF4444]'}`}>
                {pitotHeatActive ? 'HEATER ACTIVE' : 'HEATER OFF'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
