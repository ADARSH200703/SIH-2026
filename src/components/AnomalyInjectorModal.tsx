import React from 'react';
import { 
  X, 
  ShieldAlert, 
  Radio, 
  Flame, 
  WifiOff, 
  Snowflake, 
  RotateCcw, 
  CheckCircle2, 
  AlertTriangle 
} from 'lucide-react';
import { TelemetryState } from '../types/uav';
import { playTacticalClick, playWarningAlarm } from '../utils/tacticalAudio';

interface AnomalyInjectorModalProps {
  telemetry: TelemetryState;
  onUpdateTelemetry: (updates: Partial<TelemetryState>) => void;
  onClose: () => void;
}

export const AnomalyInjectorModal: React.FC<AnomalyInjectorModalProps> = ({
  telemetry,
  onUpdateTelemetry,
  onClose,
}) => {
  const isGpsJammed = telemetry.gpsQuality === 'JAMMED';
  const isEngineOverheat = telemetry.chtC >= 148;
  const isLinkLoss = telemetry.dliLatencyMs >= 150 || telemetry.datalinkStrengthPct <= 10;
  const isPitotIcing = !telemetry.pitotHeatActive || telemetry.activeAnomalies.includes('PITOT_ICING');

  const toggleGpsDenial = () => {
    playWarningAlarm();
    if (isGpsJammed) {
      onUpdateTelemetry({
        gpsQuality: 'RTK',
        ewJammingDetected: false,
        activeAnomalies: telemetry.activeAnomalies.filter((a) => a !== 'GPS_JAMMING'),
      });
    } else {
      onUpdateTelemetry({
        gpsQuality: 'JAMMED',
        ewJammingDetected: true,
        activeAnomalies: [...telemetry.activeAnomalies, 'GPS_JAMMING'],
      });
    }
  };

  const toggleEngineOverheat = () => {
    playWarningAlarm();
    if (isEngineOverheat) {
      onUpdateTelemetry({
        chtC: 118.4,
        egtC: 685.2,
        activeAnomalies: telemetry.activeAnomalies.filter((a) => a !== 'ENGINE_OVERHEAT'),
      });
    } else {
      onUpdateTelemetry({
        chtC: 152.8,
        egtC: 842.0,
        activeAnomalies: [...telemetry.activeAnomalies, 'ENGINE_OVERHEAT'],
      });
    }
  };

  const toggleLinkLoss = () => {
    playWarningAlarm();
    if (isLinkLoss) {
      onUpdateTelemetry({
        datalinkStrengthPct: 98.4,
        dliLatencyMs: 24.2,
        activeAnomalies: telemetry.activeAnomalies.filter((a) => a !== 'LINK_LOSS'),
      });
    } else {
      onUpdateTelemetry({
        datalinkStrengthPct: 4.2,
        dliLatencyMs: 185.0,
        activeAnomalies: [...telemetry.activeAnomalies, 'LINK_LOSS'],
      });
    }
  };

  const togglePitotIcing = () => {
    playWarningAlarm();
    if (isPitotIcing) {
      onUpdateTelemetry({
        pitotHeatActive: true,
        activeAnomalies: telemetry.activeAnomalies.filter((a) => a !== 'PITOT_ICING'),
      });
    } else {
      onUpdateTelemetry({
        pitotHeatActive: false,
        activeAnomalies: [...telemetry.activeAnomalies, 'PITOT_ICING'],
      });
    }
  };

  const handleResetAll = () => {
    playTacticalClick();
    onUpdateTelemetry({
      gpsQuality: 'RTK',
      ewJammingDetected: false,
      chtC: 118.4,
      egtC: 685.2,
      datalinkStrengthPct: 98.4,
      dliLatencyMs: 24.2,
      pitotHeatActive: true,
      activeAnomalies: [],
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 select-none">
      <div className="bg-[#0B111A] border border-[#EF4444]/60 rounded-lg w-full max-w-xl flex flex-col shadow-2xl overflow-hidden font-mono text-xs">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#070A0F] border-b border-[#1E2C3D]">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-[#EF4444]" />
            <span className="text-white font-bold text-sm">ELECTRONIC WARFARE &amp; ANOMALY INJECTOR</span>
          </div>
          <button
            onClick={() => {
              playTacticalClick();
              onClose();
            }}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-[#1E2C3D]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Anomaly Injections List */}
        <div className="p-4 flex flex-col gap-3">
          <div className="text-[10px] text-slate-400 uppercase">
            Red-Team Electronic Warfare &amp; Flight Fault Scenarios:
          </div>

          {/* 1. GPS Denial */}
          <div className="bg-[#070A0F] p-3 rounded border border-[#1E2C3D] flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Radio className={`w-5 h-5 ${isGpsJammed ? 'text-[#EF4444]' : 'text-slate-400'}`} />
              <div>
                <div className="text-white font-bold">EW GPS Spoofing &amp; Denial</div>
                <div className="text-[9px] text-slate-400">Forces INS/Kalman Dead-Reckoning failsafe</div>
              </div>
            </div>
            <button
              onClick={toggleGpsDenial}
              className={`px-3 py-1.5 rounded font-bold transition-all ${
                isGpsJammed
                  ? 'bg-[#EF4444] text-white shadow-[0_0_10px_#EF4444]'
                  : 'bg-[#111A26] border border-[#1E2C3D] text-slate-300 hover:text-white'
              }`}
            >
              {isGpsJammed ? 'JAMMING ACTIVE' : 'INJECT GPS DENIAL'}
            </button>
          </div>

          {/* 2. Engine Overheat */}
          <div className="bg-[#070A0F] p-3 rounded border border-[#1E2C3D] flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Flame className={`w-5 h-5 ${isEngineOverheat ? 'text-[#EF4444]' : 'text-slate-400'}`} />
              <div>
                <div className="text-white font-bold">Rotax 914 Turbo CHT Overheat</div>
                <div className="text-[9px] text-slate-400">CHT climbs past 150°C redline limit</div>
              </div>
            </div>
            <button
              onClick={toggleEngineOverheat}
              className={`px-3 py-1.5 rounded font-bold transition-all ${
                isEngineOverheat
                  ? 'bg-[#EF4444] text-white shadow-[0_0_10px_#EF4444]'
                  : 'bg-[#111A26] border border-[#1E2C3D] text-slate-300 hover:text-white'
              }`}
            >
              {isEngineOverheat ? 'OVERHEAT ACTIVE' : 'INJECT OVERHEAT'}
            </button>
          </div>

          {/* 3. Datalink Loss */}
          <div className="bg-[#070A0F] p-3 rounded border border-[#1E2C3D] flex items-center justify-between">
            <div className="flex items-center gap-3">
              <WifiOff className={`w-5 h-5 ${isLinkLoss ? 'text-[#EF4444]' : 'text-slate-400'}`} />
              <div>
                <div className="text-white font-bold">C-Band DLI Telemetry Drop</div>
                <div className="text-[9px] text-slate-400">Latency spike &gt; 150ms &amp; packet loss</div>
              </div>
            </div>
            <button
              onClick={toggleLinkLoss}
              className={`px-3 py-1.5 rounded font-bold transition-all ${
                isLinkLoss
                  ? 'bg-[#EF4444] text-white shadow-[0_0_10px_#EF4444]'
                  : 'bg-[#111A26] border border-[#1E2C3D] text-slate-300 hover:text-white'
              }`}
            >
              {isLinkLoss ? 'LINK DROP ACTIVE' : 'INJECT LINK LOSS'}
            </button>
          </div>

          {/* 4. Pitot Icing */}
          <div className="bg-[#070A0F] p-3 rounded border border-[#1E2C3D] flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Snowflake className={`w-5 h-5 ${isPitotIcing ? 'text-[#EF4444]' : 'text-slate-400'}`} />
              <div>
                <div className="text-white font-bold">Sub-Zero Pitot Tube Icing</div>
                <div className="text-[9px] text-slate-400">Pitot heater offline at high altitude (-18°C)</div>
              </div>
            </div>
            <button
              onClick={togglePitotIcing}
              className={`px-3 py-1.5 rounded font-bold transition-all ${
                isPitotIcing
                  ? 'bg-[#EF4444] text-white shadow-[0_0_10px_#EF4444]'
                  : 'bg-[#111A26] border border-[#1E2C3D] text-slate-300 hover:text-white'
              }`}
            >
              {isPitotIcing ? 'ICING ACTIVE' : 'INJECT PITOT ICING'}
            </button>
          </div>
        </div>

        {/* Modal Footer Controls */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#070A0F] border-t border-[#1E2C3D]">
          <button
            onClick={handleResetAll}
            className="px-3 py-1.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#10B981]/50 text-[#10B981] rounded text-xs font-bold flex items-center gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>RESTORE NOMINAL AVIONICS</span>
          </button>

          <button
            onClick={() => {
              playTacticalClick();
              onClose();
            }}
            className="px-4 py-1.5 bg-[#00F2FF] hover:bg-[#00D8E6] text-black font-bold rounded text-xs"
          >
            APPLY &amp; CLOSE
          </button>
        </div>
      </div>
    </div>
  );
};
