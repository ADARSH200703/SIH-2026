import React from 'react';
import { 
  X, 
  Crosshair, 
  ShieldAlert, 
  Eye, 
  MapPin, 
  Compass, 
  CheckCircle2, 
  Zap, 
  Radio 
} from 'lucide-react';
import { ATRTarget } from '../types/uav';
import { playTacticalClick, playLockTone, playLaserPulse } from '../utils/tacticalAudio';

interface TargetIntelModalProps {
  target: ATRTarget | null;
  onClose: () => void;
  onSlaveGimbal: (targetId: string) => void;
  onFireLaser: () => void;
}

export const TargetIntelModal: React.FC<TargetIntelModalProps> = ({
  target,
  onClose,
  onSlaveGimbal,
  onFireLaser,
}) => {
  if (!target) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 select-none">
      <div className="bg-[#0B111A] border border-[#EF4444]/60 rounded-lg w-full max-w-2xl flex flex-col shadow-2xl overflow-hidden font-mono text-xs">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#070A0F] border-b border-[#1E2C3D]">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-[#EF4444]" />
            <span className="text-white font-bold text-sm">MIL-STD-2525 TARGET INTELLIGENCE DOSSIER</span>
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

        {/* Content Body */}
        <div className="p-4 flex flex-col gap-3">
          {/* Target Title Ribbon */}
          <div className="flex items-center justify-between bg-[#111A26] p-2.5 rounded border border-[#1E2C3D]">
            <div>
              <div className="text-sm font-bold text-white">{target.name}</div>
              <div className="text-[10px] text-[#EF4444] font-semibold">{target.classification}</div>
            </div>
            <div className="text-right">
              <span className="text-[9px] px-2 py-0.5 bg-[#EF4444]/20 border border-[#EF4444] text-[#EF4444] rounded font-bold">
                {target.threatLevel} THREAT
              </span>
              <div className="text-[9px] text-slate-400 mt-1 font-mono">
                MIL-STD: {target.milStdCode}
              </div>
            </div>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-3 gap-2 text-[10px]">
            <div className="bg-[#070A0F] p-2 rounded border border-[#1E2C3D]">
              <div className="text-slate-400">ATR NEURAL CONFIDENCE</div>
              <div className="text-sm font-bold text-[#00F2FF] mt-0.5">{target.confidencePct.toFixed(1)}%</div>
            </div>
            <div className="bg-[#070A0F] p-2 rounded border border-[#1E2C3D]">
              <div className="text-slate-400">SLANT RANGE</div>
              <div className="text-sm font-bold text-white mt-0.5">{(target.slantRangeM / 1000).toFixed(2)} km</div>
            </div>
            <div className="bg-[#070A0F] p-2 rounded border border-[#1E2C3D]">
              <div className="text-slate-400">TARGET ELEVATION</div>
              <div className="text-sm font-bold text-[#10B981] mt-0.5">{target.altMslFt.toLocaleString()} FT MSL</div>
            </div>
          </div>

          {/* Coordinates & Track Info */}
          <div className="bg-[#070A0F] p-2.5 rounded border border-[#1E2C3D] space-y-1 text-[10px]">
            <div className="flex justify-between">
              <span className="text-slate-400">GEO COORDINATES:</span>
              <span className="text-white font-bold">{target.lat.toFixed(6)}°N, {target.lng.toFixed(6)}°E</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">ESTIMATED VELOCITY &amp; HEADING:</span>
              <span className="text-white">{target.speedKts} KT @ {target.headingDeg}°</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">GCS SENSOR SLAVE STATUS:</span>
              <span className={`font-bold ${target.slaved ? 'text-[#EF4444]' : 'text-slate-400'}`}>
                {target.slaved ? 'SLAVED TO MWIR GIMBAL' : 'UNSLAVED'}
              </span>
            </div>
          </div>

          {/* Intelligence Notes */}
          <div className="bg-[#070A0F] p-2.5 rounded border border-[#1E2C3D]">
            <div className="text-[9px] text-slate-400 uppercase mb-1">Tactical Intelligence Assessment:</div>
            <div className="text-slate-300 text-[10px] leading-relaxed">{target.notes}</div>
          </div>
        </div>

        {/* Modal Footer Controls */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#070A0F] border-t border-[#1E2C3D]">
          <button
            onClick={() => {
              playLockTone();
              onSlaveGimbal(target.id);
              onClose();
            }}
            className="px-3 py-1.5 bg-[#00F2FF]/20 hover:bg-[#00F2FF]/30 border border-[#00F2FF] text-[#00F2FF] rounded text-xs font-bold flex items-center gap-1.5"
          >
            <Crosshair className="w-3.5 h-3.5" />
            <span>SLAVE GIMBAL TO TARGET</span>
          </button>

          <button
            onClick={() => {
              playLaserPulse();
              onFireLaser();
              onClose();
            }}
            className="px-4 py-1.5 bg-[#EF4444] hover:bg-[#DC2626] text-white rounded text-xs font-bold shadow-[0_0_12px_rgba(239,68,68,0.5)] flex items-center gap-1.5"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>FIRE STANAG 3733 LASER</span>
          </button>
        </div>
      </div>
    </div>
  );
};
