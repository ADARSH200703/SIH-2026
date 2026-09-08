import React, { useState, useEffect } from 'react';
import { 
  Radio, 
  Volume2, 
  VolumeX, 
  AlertTriangle, 
  ShieldAlert, 
  Sliders, 
  FileCode2, 
  Award, 
  Layers, 
  Activity, 
  Crosshair, 
  Cpu, 
  Compass,
  ChevronDown
} from 'lucide-react';
import { SectorConfig, TelemetryState } from '../types/uav';
import { playTacticalClick, playWarningAlarm } from '../utils/tacticalAudio';

interface GcsHeaderProps {
  activeView: 'DASHBOARD' | 'COCKPIT' | 'INTEL' | 'AVIONICS' | 'SIH_BRIEF';
  setActiveView: (view: 'DASHBOARD' | 'COCKPIT' | 'INTEL' | 'AVIONICS' | 'SIH_BRIEF') => void;
  currentSector: SectorConfig;
  allSectors: SectorConfig[];
  onSelectSector: (sectorId: string) => void;
  telemetry: TelemetryState;
  isMuted: boolean;
  onToggleMute: () => void;
  onOpenPacketInspector: () => void;
  onOpenAnomalyInjector: () => void;
  onOpenSihScorecard: () => void;
}

export const GcsHeader: React.FC<GcsHeaderProps> = ({
  activeView,
  setActiveView,
  currentSector,
  allSectors,
  onSelectSector,
  telemetry,
  isMuted,
  onToggleMute,
  onOpenPacketInspector,
  onOpenAnomalyInjector,
  onOpenSihScorecard,
}) => {
  const [utcTime, setUtcTime] = useState<string>('');
  const [sectorDropdownOpen, setSectorDropdownOpen] = useState(false);

  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      setUtcTime(
        now.toISOString().substring(11, 19) + ' UTC'
      );
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const hasMasterWarning = telemetry.ewJammingDetected || telemetry.activeAnomalies.length > 0 || telemetry.chtC > 140;
  const hasMasterCaution = telemetry.fuelRemainingLiters < telemetry.bingoFuelThresholdLiters * 1.5 || telemetry.dliLatencyMs > 60;

  const handleNavClick = (view: 'DASHBOARD' | 'COCKPIT' | 'INTEL' | 'AVIONICS' | 'SIH_BRIEF') => {
    playTacticalClick();
    setActiveView(view);
  };

  const handleMasterAlarmClick = () => {
    playWarningAlarm();
    onOpenAnomalyInjector();
  };

  return (
    <header className="w-full bg-[#070A0F] border-b border-[#1E2C3D] px-3 py-1.5 flex items-center justify-between select-none z-30 relative shadow-md">
      {/* LEFT ZONE: DRDO Emblem & Callsign & Sector */}
      <div className="flex items-center gap-3">
        {/* Tricolor & DRDO Brand */}
        <div className="flex items-center gap-2 pr-3 border-r border-[#1E2C3D]">
          <div className="flex flex-col gap-0.5 h-6 w-1.5 rounded-sm overflow-hidden shadow">
            <div className="bg-[#FF9933] flex-1"></div>
            <div className="bg-[#FFFFFF] flex-1"></div>
            <div className="bg-[#128807] flex-1"></div>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-tech text-xs tracking-wider text-[#00F2FF] font-bold">DRDO ADE</span>
              <span className="text-[9px] px-1 py-0.2 bg-[#1E2C3D] text-slate-300 font-mono rounded">TAPAS-BH-201</span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono tracking-tight flex items-center gap-1">
              <span>CALLSIGN:</span>
              <span className="text-white font-bold tracking-wider">TAPAS-07 [LEAD]</span>
            </div>
          </div>
        </div>

        {/* Sector Quick Selector */}
        <div className="relative">
          <button
            onClick={() => {
              playTacticalClick();
              setSectorDropdownOpen(!sectorDropdownOpen);
            }}
            className="flex items-center gap-2 px-2.5 py-1 bg-[#0B111A] hover:bg-[#111A26] border border-[#1E2C3D] hover:border-[#00F2FF]/50 rounded text-xs transition-all"
          >
            <Compass className="w-3.5 h-3.5 text-[#00F2FF]" />
            <div className="text-left">
              <div className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                <span>SECTOR:</span>
                <span className="text-white font-semibold">{currentSector.name.split(' (')[0]}</span>
              </div>
              <div className="text-[9px] text-[#38BDF8] font-mono">{currentSector.coordinatesBadge}</div>
            </div>
            <ChevronDown className="w-3 h-3 text-slate-400 ml-1" />
          </button>

          {sectorDropdownOpen && (
            <div className="absolute left-0 mt-1 w-64 bg-[#0B111A] border border-[#00F2FF]/40 rounded shadow-xl py-1 z-50">
              <div className="px-2 py-1 text-[9px] font-mono uppercase tracking-wider text-slate-400 border-b border-[#1E2C3D]">
                Operational Sectors
              </div>
              {allSectors.map((s) => (
                <button
                  key={s.id}
                  onClick={() => {
                    playTacticalClick();
                    onSelectSector(s.id);
                    setSectorDropdownOpen(false);
                  }}
                  className={`w-full text-left px-2.5 py-1.5 text-xs flex items-center justify-between hover:bg-[#111A26] transition-all ${
                    s.id === currentSector.id ? 'text-[#00F2FF] bg-[#111A26]/80 font-bold' : 'text-slate-300'
                  }`}
                >
                  <div>
                    <div className="font-semibold text-[11px]">{s.name}</div>
                    <div className="text-[9px] text-slate-400 font-mono">{s.coordinatesBadge}</div>
                  </div>
                  <span className="text-[9px] font-mono px-1 py-0.5 bg-[#1E2C3D] rounded text-slate-300">
                    {s.msaFl}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* CENTER ZONE: Primary View Switcher Navigation Matrix */}
      <div className="flex items-center gap-1 bg-[#0B111A] border border-[#1E2C3D] p-1 rounded-md">
        <button
          onClick={() => handleNavClick('DASHBOARD')}
          className={`px-3 py-1 text-xs font-semibold rounded flex items-center gap-1.5 transition-all ${
            activeView === 'DASHBOARD'
              ? 'bg-[#111A26] text-[#4cd7f6] border border-[#4cd7f6]/50 shadow-[0_0_10px_rgba(76,215,246,0.3)] font-bold'
              : 'text-slate-400 hover:text-white hover:bg-[#111A26]/50'
          }`}
        >
          <Activity className="w-3.5 h-3.5 text-[#4cd7f6]" />
          <span>AERIS GCS MASTER</span>
        </button>

        <button
          onClick={() => handleNavClick('COCKPIT')}
          className={`px-3 py-1 text-xs font-semibold rounded flex items-center gap-1.5 transition-all ${
            activeView === 'COCKPIT'
              ? 'bg-[#111A26] text-[#00F2FF] border border-[#00F2FF]/50 shadow-[0_0_10px_rgba(0,242,255,0.2)] font-bold'
              : 'text-slate-400 hover:text-white hover:bg-[#111A26]/50'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>COCKPIT HUD</span>
        </button>

        <button
          onClick={() => handleNavClick('INTEL')}
          className={`px-3 py-1 text-xs font-semibold rounded flex items-center gap-1.5 transition-all ${
            activeView === 'INTEL'
              ? 'bg-[#111A26] text-[#00F2FF] border border-[#00F2FF]/50 shadow-[0_0_10px_rgba(0,242,255,0.2)] font-bold'
              : 'text-slate-400 hover:text-white hover:bg-[#111A26]/50'
          }`}
        >
          <Crosshair className="w-3.5 h-3.5" />
          <span>INTEL / ATR MATRIX</span>
        </button>

        <button
          onClick={() => handleNavClick('AVIONICS')}
          className={`px-3 py-1 text-xs font-semibold rounded flex items-center gap-1.5 transition-all ${
            activeView === 'AVIONICS'
              ? 'bg-[#111A26] text-[#00F2FF] border border-[#00F2FF]/50 shadow-[0_0_10px_rgba(0,242,255,0.2)] font-bold'
              : 'text-slate-400 hover:text-white hover:bg-[#111A26]/50'
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          <span>AVIONICS TWIN</span>
        </button>

        <button
          onClick={() => handleNavClick('SIH_BRIEF')}
          className={`px-3 py-1 text-xs font-semibold rounded flex items-center gap-1.5 transition-all ${
            activeView === 'SIH_BRIEF'
              ? 'bg-[#111A26] text-[#F59E0B] border border-[#F59E0B]/50 shadow-[0_0_10px_rgba(245,158,11,0.2)] font-bold'
              : 'text-slate-400 hover:text-white hover:bg-[#111A26]/50'
          }`}
        >
          <Award className="w-3.5 h-3.5 text-[#F59E0B]" />
          <span>SIH 2026 BRIEF</span>
        </button>
      </div>

      {/* RIGHT ZONE: Latency, Master Alarms, UTC Time & Tools */}
      <div className="flex items-center gap-2.5">
        {/* DLI Packet Latency */}
        <div className="flex items-center gap-1.5 px-2 py-1 bg-[#0B111A] border border-[#1E2C3D] rounded text-[11px] font-mono">
          <Radio className="w-3 h-3 text-[#10B981] animate-pulse" />
          <span className="text-slate-400 text-[10px]">DLI:</span>
          <span className={`font-bold ${telemetry.dliLatencyMs > 50 ? 'text-[#F59E0B]' : 'text-[#10B981]'}`}>
            {telemetry.dliLatencyMs.toFixed(1)}ms
          </span>
        </div>

        {/* Master Caution / Warning Annunciators */}
        <div className="flex items-center gap-1">
          <button
            onClick={handleMasterAlarmClick}
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold flex items-center gap-1 transition-all border ${
              hasMasterCaution
                ? 'animate-tactical-caution text-[#F59E0B]'
                : 'bg-[#0B111A] border-[#1E2C3D] text-slate-500'
            }`}
          >
            <AlertTriangle className="w-3 h-3" />
            <span>M-CAUTION</span>
          </button>

          <button
            onClick={handleMasterAlarmClick}
            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold flex items-center gap-1 transition-all border ${
              hasMasterWarning
                ? 'animate-tactical-alarm text-white'
                : 'bg-[#0B111A] border-[#1E2C3D] text-slate-500'
            }`}
          >
            <ShieldAlert className="w-3 h-3" />
            <span>M-WARNING</span>
          </button>
        </div>

        {/* Diagnostic Launcher Action Buttons */}
        <div className="flex items-center gap-1 border-l border-[#1E2C3D] pl-2">
          <button
            onClick={() => {
              playTacticalClick();
              onOpenAnomalyInjector();
            }}
            title="Electronic Warfare & Anomaly Injector"
            className="p-1.5 bg-[#0B111A] hover:bg-[#111A26] border border-[#1E2C3D] hover:border-[#EF4444]/60 text-slate-300 hover:text-[#EF4444] rounded transition-all"
          >
            <Sliders className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => {
              playTacticalClick();
              onOpenPacketInspector();
            }}
            title="STANAG 4586 / 4609 KLV Packet Inspector"
            className="p-1.5 bg-[#0B111A] hover:bg-[#111A26] border border-[#1E2C3D] hover:border-[#00F2FF]/60 text-slate-300 hover:text-[#00F2FF] rounded transition-all"
          >
            <FileCode2 className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => {
              playTacticalClick();
              onOpenSihScorecard();
            }}
            title="DRDO SIH 2026 Evaluation Scorecard"
            className="p-1.5 bg-[#0B111A] hover:bg-[#111A26] border border-[#1E2C3D] hover:border-[#F59E0B]/60 text-slate-300 hover:text-[#F59E0B] rounded transition-all"
          >
            <Award className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => {
              playTacticalClick();
              onToggleMute();
            }}
            title={isMuted ? 'Unmute Audio' : 'Mute Tactical Audio'}
            className="p-1.5 bg-[#0B111A] hover:bg-[#111A26] border border-[#1E2C3D] hover:border-[#38BDF8]/60 text-slate-300 hover:text-[#38BDF8] rounded transition-all"
          >
            {isMuted ? <VolumeX className="w-3.5 h-3.5 text-slate-500" /> : <Volume2 className="w-3.5 h-3.5 text-[#00F2FF]" />}
          </button>
        </div>

        {/* UTC Synchronized Zulu Clock */}
        <div className="px-2 py-0.5 bg-[#070A0F] border border-[#1E2C3D] rounded text-[11px] font-mono-num font-bold text-white tracking-widest">
          {utcTime || '14:24:00 UTC'}
        </div>
      </div>
    </header>
  );
};
