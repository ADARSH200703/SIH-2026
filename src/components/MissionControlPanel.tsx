import React, { useState } from 'react';
import { 
  Compass, 
  Gauge, 
  Navigation, 
  RotateCw, 
  ShieldAlert, 
  ArrowUp, 
  ArrowDown, 
  Sliders, 
  CheckCircle2, 
  Lock, 
  Unlock 
} from 'lucide-react';
import { FlightMode, TelemetryState } from '../types/uav';
import { playTacticalClick, playWarningAlarm } from '../utils/tacticalAudio';

interface MissionControlPanelProps {
  telemetry: TelemetryState;
  onUpdateTelemetry: (updates: Partial<TelemetryState>) => void;
}

export const MissionControlPanel: React.FC<MissionControlPanelProps> = ({
  telemetry,
  onUpdateTelemetry,
}) => {
  const [rthGuardUnlocked, setRthGuardUnlocked] = useState(false);

  const {
    flightMode,
    commandedAltitudeFt,
    commandedAirspeedKts,
    commandedHeadingDeg,
  } = telemetry;

  const handleFlightModeChange = (mode: FlightMode) => {
    playTacticalClick();
    onUpdateTelemetry({ flightMode: mode });
  };

  const handleAltChange = (delta: number) => {
    playTacticalClick();
    const newAlt = Math.max(5000, Math.min(32000, commandedAltitudeFt + delta));
    onUpdateTelemetry({ commandedAltitudeFt: newAlt });
  };

  const handleSpeedChange = (delta: number) => {
    playTacticalClick();
    const newSpd = Math.max(70, Math.min(180, commandedAirspeedKts + delta));
    onUpdateTelemetry({ commandedAirspeedKts: newSpd });
  };

  const handleHeadingChange = (delta: number) => {
    playTacticalClick();
    const newHdg = (commandedHeadingDeg + delta + 360) % 360;
    onUpdateTelemetry({ commandedHeadingDeg: newHdg });
  };

  const handleEmergencyRth = () => {
    playWarningAlarm();
    onUpdateTelemetry({ flightMode: 'RTH_FAILSAFE' });
  };

  return (
    <div className="w-full bg-[#0B111A] border border-[#1E2C3D] rounded-md p-2.5 flex flex-col gap-2.5 select-none shadow-md font-mono">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-[#1E2C3D] pb-1.5 text-[10px]">
        <div className="flex items-center gap-1.5">
          <Sliders className="w-3.5 h-3.5 text-[#00F2FF]" />
          <span className="text-white font-bold tracking-wider">STANAG 4586 AUTOPILOT C2</span>
        </div>
        <div className="flex items-center gap-1">
          <CheckCircle2 className="w-3 h-3 text-[#10B981]" />
          <span className="text-[#10B981] font-bold">FCS_NOMINAL</span>
        </div>
      </div>

      {/* Flight Mode Push-Button Matrix */}
      <div>
        <div className="text-[9px] uppercase tracking-wider text-slate-400 mb-1">
          Flight Regime Engagement:
        </div>
        <div className="grid grid-cols-5 gap-1.5">
          {(['MANUAL', 'AUTO_NAV', 'LOITER_HOLD', 'TERRAIN_FOLLOW', 'RTH_FAILSAFE'] as FlightMode[]).map((mode) => {
            const isActive = flightMode === mode;
            const isRth = mode === 'RTH_FAILSAFE';

            return (
              <button
                key={mode}
                onClick={() => handleFlightModeChange(mode)}
                className={`py-1.5 px-1 rounded text-[9px] font-bold transition-all text-center flex flex-col items-center justify-center gap-0.5 ${
                  isActive
                    ? isRth
                      ? 'bg-[#EF4444] text-white border border-red-300 shadow-[0_0_12px_rgba(239,68,68,0.6)]'
                      : 'bg-[#111A26] text-[#00F2FF] border border-[#00F2FF] shadow-[0_0_10px_rgba(0,242,255,0.4)]'
                    : 'bg-[#070A0F] border border-[#1E2C3D] text-slate-400 hover:text-white hover:bg-[#111A26]/60'
                }`}
              >
                <span>{mode.replace('_', ' ')}</span>
                <span className={`text-[7px] ${isActive ? 'text-white' : 'text-slate-500'}`}>
                  {isActive ? 'ENGAGED' : 'STANDBY'}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Primary Autopilot Setpoints (Altitude, Airspeed, Heading) */}
      <div className="grid grid-cols-3 gap-2 border-y border-[#1E2C3D] py-2">
        {/* Commanded Altitude Setpoint */}
        <div className="bg-[#070A0F] p-2 rounded border border-[#1E2C3D] flex flex-col justify-between">
          <div className="flex items-center justify-between text-[9px] text-slate-400">
            <span>TARGET ALTITUDE:</span>
            <Navigation className="w-3 h-3 text-[#38BDF8]" />
          </div>
          <div className="text-sm font-bold text-white my-1 text-center">
            {commandedAltitudeFt.toLocaleString()} <span className="text-[9px] text-[#38BDF8]">FT</span>
          </div>
          <div className="grid grid-cols-4 gap-1">
            <button
              onClick={() => handleAltChange(-1000)}
              className="py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#1E2C3D] text-slate-300 rounded text-[8px]"
            >
              -1k
            </button>
            <button
              onClick={() => handleAltChange(-500)}
              className="py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#1E2C3D] text-slate-300 rounded text-[8px]"
            >
              -500
            </button>
            <button
              onClick={() => handleAltChange(500)}
              className="py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#1E2C3D] text-slate-300 rounded text-[8px]"
            >
              +500
            </button>
            <button
              onClick={() => handleAltChange(1000)}
              className="py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#1E2C3D] text-slate-300 rounded text-[8px]"
            >
              +1k
            </button>
          </div>
        </div>

        {/* Commanded Airspeed Setpoint */}
        <div className="bg-[#070A0F] p-2 rounded border border-[#1E2C3D] flex flex-col justify-between">
          <div className="flex items-center justify-between text-[9px] text-slate-400">
            <span>TARGET AIRSPEED:</span>
            <Gauge className="w-3 h-3 text-[#10B981]" />
          </div>
          <div className="text-sm font-bold text-white my-1 text-center">
            {commandedAirspeedKts} <span className="text-[9px] text-[#10B981]">KT IAS</span>
          </div>
          <div className="grid grid-cols-4 gap-1">
            <button
              onClick={() => handleSpeedChange(-10)}
              className="py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#1E2C3D] text-slate-300 rounded text-[8px]"
            >
              -10
            </button>
            <button
              onClick={() => handleSpeedChange(-5)}
              className="py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#1E2C3D] text-slate-300 rounded text-[8px]"
            >
              -5
            </button>
            <button
              onClick={() => handleSpeedChange(5)}
              className="py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#1E2C3D] text-slate-300 rounded text-[8px]"
            >
              +5
            </button>
            <button
              onClick={() => handleSpeedChange(10)}
              className="py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#1E2C3D] text-slate-300 rounded text-[8px]"
            >
              +10
            </button>
          </div>
        </div>

        {/* Commanded Heading Setpoint */}
        <div className="bg-[#070A0F] p-2 rounded border border-[#1E2C3D] flex flex-col justify-between">
          <div className="flex items-center justify-between text-[9px] text-slate-400">
            <span>HEADING BUG:</span>
            <Compass className="w-3 h-3 text-[#F59E0B]" />
          </div>
          <div className="text-sm font-bold text-white my-1 text-center">
            {commandedHeadingDeg.toFixed(0)}° <span className="text-[9px] text-[#F59E0B]">MAG</span>
          </div>
          <div className="grid grid-cols-4 gap-1">
            <button
              onClick={() => handleHeadingChange(-15)}
              className="py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#1E2C3D] text-slate-300 rounded text-[8px]"
            >
              -15°
            </button>
            <button
              onClick={() => handleHeadingChange(-5)}
              className="py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#1E2C3D] text-slate-300 rounded text-[8px]"
            >
              -5°
            </button>
            <button
              onClick={() => handleHeadingChange(5)}
              className="py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#1E2C3D] text-slate-300 rounded text-[8px]"
            >
              +5°
            </button>
            <button
              onClick={() => handleHeadingChange(15)}
              className="py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#1E2C3D] text-slate-300 rounded text-[8px]"
            >
              +15°
            </button>
          </div>
        </div>
      </div>

      {/* Guarded Emergency Return to Home (RTH) Switch */}
      <div className="flex items-center justify-between bg-[#070A0F] border border-[#EF4444]/40 p-2 rounded">
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              playTacticalClick();
              setRthGuardUnlocked(!rthGuardUnlocked);
            }}
            className={`p-1.5 rounded text-[10px] flex items-center gap-1 border transition-all ${
              rthGuardUnlocked
                ? 'bg-[#EF4444]/20 border-[#EF4444] text-[#EF4444]'
                : 'bg-[#111A26] border-[#1E2C3D] text-slate-400'
            }`}
          >
            {rthGuardUnlocked ? <Unlock className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
            <span>{rthGuardUnlocked ? 'SAFETY GUARD RAISED' : 'GUARD LOCKED'}</span>
          </button>
          <div className="text-[9px] text-slate-400">
            AUTONOMOUS GPS-DENIED RETURN CORRIDOR
          </div>
        </div>

        <button
          disabled={!rthGuardUnlocked}
          onClick={handleEmergencyRth}
          className={`px-4 py-1.5 rounded text-[10px] font-bold flex items-center gap-1.5 transition-all shadow ${
            rthGuardUnlocked
              ? 'bg-[#EF4444] hover:bg-[#DC2626] text-white animate-pulse shadow-[0_0_15px_rgba(239,68,68,0.7)] cursor-pointer'
              : 'bg-[#1E2C3D] text-slate-500 cursor-not-allowed border border-[#1E2C3D]'
          }`}
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>EXECUTE EMERGENCY RTH</span>
        </button>
      </div>
    </div>
  );
};
