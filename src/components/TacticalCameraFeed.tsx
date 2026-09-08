import React from 'react';
import { 
  Crosshair, 
  Target, 
  ZoomIn, 
  Zap, 
  Sliders, 
  Eye, 
  Flame, 
  Sun, 
  Radio, 
  Compass, 
  Maximize2 
} from 'lucide-react';
import { PayloadState, ATRTarget, SensorPalette } from '../types/uav';
import { playTacticalClick, playLockTone, playLaserPulse } from '../utils/tacticalAudio';

interface TacticalCameraFeedProps {
  payload: PayloadState;
  targets: ATRTarget[];
  onUpdatePayload: (updates: Partial<PayloadState>) => void;
  onSelectTarget: (target: ATRTarget) => void;
  onOpenTargetIntel: (target: ATRTarget) => void;
}

export const TacticalCameraFeed: React.FC<TacticalCameraFeedProps> = ({
  payload,
  targets,
  onUpdatePayload,
  onSelectTarget,
  onOpenTargetIntel,
}) => {
  const {
    palette,
    zoomLevel,
    panDeg,
    tiltDeg,
    fovDeg,
    laserDesignatorActive,
    laserCode,
    laserCountdownSec,
    slavedTargetId,
    gyroStabilized,
  } = payload;

  const handlePaletteChange = (newPalette: SensorPalette) => {
    playTacticalClick();
    onUpdatePayload({ palette: newPalette });
  };

  const handleToggleLaser = () => {
    if (!laserDesignatorActive) {
      playLaserPulse();
      onUpdatePayload({
        laserDesignatorActive: true,
        laserCountdownSec: 20,
      });
    } else {
      playTacticalClick();
      onUpdatePayload({
        laserDesignatorActive: false,
        laserCountdownSec: 0,
      });
    }
  };

  const handleTargetClick = (target: ATRTarget, e: React.MouseEvent) => {
    e.stopPropagation();
    playLockTone();
    onSelectTarget(target);
    onUpdatePayload({ slavedTargetId: target.id });
  };

  // Dynamic visual styling based on sensor palette
  const getPaletteFilterClass = () => {
    switch (palette) {
      case 'FLIR_WHITE':
        return 'bg-gradient-to-b from-[#18181B] via-[#27272A] to-[#09090B] brightness-125 contrast-150 grayscale';
      case 'FLIR_BLACK':
        return 'bg-gradient-to-b from-[#E4E4E7] via-[#D4D4D8] to-[#A1A1AA] invert contrast-200';
      case 'FLIR_IRONBOW':
        return 'bg-gradient-to-tr from-[#1E0836] via-[#7B1FA2] via-[#E65100] to-[#FFD54F] contrast-150 saturate-200';
      case 'SAR':
        return 'bg-[#021B0D] contrast-175 hue-rotate-90';
      case 'EO':
      default:
        return 'bg-gradient-to-b from-[#0F1E2E] via-[#1B2F44] to-[#121B22]';
    }
  };

  return (
    <div className="relative w-full h-full bg-[#070A0F] border border-[#1E2C3D] rounded-md overflow-hidden flex flex-col select-none shadow-inner">
      {/* Top Header Bar */}
      <div className="flex items-center justify-between px-2.5 py-1 bg-[#0B111A]/90 border-b border-[#1E2C3D] z-20 font-mono text-[10px]">
        {/* Sensor Designation & Slaving Status */}
        <div className="flex items-center gap-2">
          <span className="px-1.5 py-0.5 bg-[#00F2FF]/20 text-[#00F2FF] border border-[#00F2FF]/40 rounded font-bold">
            GCS-EO/IR-04
          </span>
          <span className="text-slate-400">GIMBAL:</span>
          <span className={`font-bold ${gyroStabilized ? 'text-[#10B981]' : 'text-[#F59E0B]'}`}>
            {gyroStabilized ? '3-AXIS GYRO STAB' : 'UNSTABILIZED'}
          </span>
          {slavedTargetId && (
            <span className="text-[#EF4444] font-bold animate-pulse">
              | SLAVED: {slavedTargetId}
            </span>
          )}
        </div>

        {/* 5 Sensor Palettes Ribbon */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => handlePaletteChange('EO')}
            className={`px-2 py-0.5 rounded text-[9px] flex items-center gap-1 transition-all ${
              palette === 'EO'
                ? 'bg-[#00F2FF]/20 text-[#00F2FF] border border-[#00F2FF]/50 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Sun className="w-2.5 h-2.5" />
            <span>DAY EO</span>
          </button>

          <button
            onClick={() => handlePaletteChange('FLIR_WHITE')}
            className={`px-2 py-0.5 rounded text-[9px] flex items-center gap-1 transition-all ${
              palette === 'FLIR_WHITE'
                ? 'bg-white text-black border border-white font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Flame className="w-2.5 h-2.5" />
            <span>W-HOT</span>
          </button>

          <button
            onClick={() => handlePaletteChange('FLIR_BLACK')}
            className={`px-2 py-0.5 rounded text-[9px] flex items-center gap-1 transition-all ${
              palette === 'FLIR_BLACK'
                ? 'bg-slate-300 text-black border border-slate-300 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Eye className="w-2.5 h-2.5" />
            <span>B-HOT</span>
          </button>

          <button
            onClick={() => handlePaletteChange('FLIR_IRONBOW')}
            className={`px-2 py-0.5 rounded text-[9px] flex items-center gap-1 transition-all ${
              palette === 'FLIR_IRONBOW'
                ? 'bg-gradient-to-r from-purple-500 to-amber-500 text-white border border-amber-400 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Sliders className="w-2.5 h-2.5" />
            <span>IRONBOW</span>
          </button>

          <button
            onClick={() => handlePaletteChange('SAR')}
            className={`px-2 py-0.5 rounded text-[9px] flex items-center gap-1 transition-all ${
              palette === 'SAR'
                ? 'bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/50 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Radio className="w-2.5 h-2.5" />
            <span>SAR GMTI</span>
          </button>
        </div>
      </div>

      {/* Main Viewport Window */}
      <div className="relative flex-1 w-full h-full overflow-hidden flex items-center justify-center">
        {/* Dynamic Simulated Background Environment with Palette Shaders */}
        <div className={`absolute inset-0 transition-all duration-300 ${getPaletteFilterClass()}`}>
          {/* Simulated Geographic Texture / Mountain Ridge Contours */}
          <svg className="w-full h-full opacity-30 pointer-events-none" viewBox="0 0 600 400" preserveAspectRatio="none">
            <path d="M0,280 Q150,220 300,290 T600,270 L600,400 L0,400 Z" fill="#000000" />
            <path d="M0,320 Q200,270 400,330 T600,310 L600,400 L0,400 Z" fill="#000000" opacity="0.6" />
            {/* River / Road Vector */}
            <path d="M120,400 Q280,310 420,240 T580,180" stroke="#38BDF8" strokeWidth="3" fill="none" opacity="0.4" />
          </svg>
        </div>

        {/* Scanline CRT overlay effect */}
        <div className="absolute inset-0 scanline-overlay pointer-events-none z-10 opacity-70" />

        {/* SAR GMTI Radar Sweep effect if active */}
        {palette === 'SAR' && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
            <div className="w-[500px] h-[500px] rounded-full radar-sweep-effect animate-spin" style={{ animationDuration: '6s' }} />
          </div>
        )}

        {/* Tactical Crosshair / Optical Reticle Overlay */}
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
          {/* Center Crosshair */}
          <div className="relative w-48 h-48 flex items-center justify-center">
            {/* Outer Reticle Ring */}
            <div className="w-32 h-32 rounded-full border border-[#00F2FF]/40 border-dashed" />
            {/* Inner Ring */}
            <div className="absolute w-12 h-12 rounded-full border border-[#00F2FF]/60" />
            {/* Cross Lines */}
            <div className="absolute w-44 h-[1px] bg-[#00F2FF]/60" />
            <div className="absolute h-44 w-[1px] bg-[#00F2FF]/60" />
            {/* Center Pip */}
            <div className="absolute w-1.5 h-1.5 bg-[#00F2FF] rounded-full shadow-[0_0_8px_#00F2FF]" />

            {/* Milliradian Range Scale Ticks */}
            <div className="absolute top-2 text-[8px] font-mono text-[#00F2FF]">10</div>
            <div className="absolute bottom-2 text-[8px] font-mono text-[#00F2FF]">10</div>
            <div className="absolute left-2 text-[8px] font-mono text-[#00F2FF]">10</div>
            <div className="absolute right-2 text-[8px] font-mono text-[#00F2FF]">10</div>
          </div>
        </div>

        {/* Laser Target Designator (LTD) Active Crosshair */}
        {laserDesignatorActive && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-20">
            <div className="relative flex items-center justify-center animate-pulse">
              <div className="w-20 h-20 rounded-full border-2 border-[#EF4444] shadow-[0_0_15px_#EF4444]" />
              <div className="absolute w-28 h-[1.5px] bg-[#EF4444] shadow-[0_0_10px_#EF4444]" />
              <div className="absolute h-28 w-[1.5px] bg-[#EF4444] shadow-[0_0_10px_#EF4444]" />
              <div className="absolute -top-7 bg-[#EF4444] text-white font-mono text-[9px] font-bold px-2 py-0.5 rounded shadow">
                LTD BEAM ACTIVE: {laserCountdownSec}s | CODE {laserCode}
              </div>
            </div>
          </div>
        )}

        {/* ==========================================================================
            ATR DETECTED TARGET BOUNDING BOXES (MIL-STD BRACKETS)
            ========================================================================== */}
        {targets.map((tgt) => {
          const isSlaved = tgt.id === slavedTargetId;
          const { x, y, w, h } = tgt.bbox;

          return (
            <div
              key={tgt.id}
              onClick={(e) => handleTargetClick(tgt, e)}
              className="absolute cursor-pointer transition-all duration-150 z-20 group"
              style={{
                left: `${x}%`,
                top: `${y}%`,
                width: `${w}%`,
                height: `${h}%`,
              }}
            >
              {/* Target Corner Bracket Bounding Box */}
              <div
                className={`relative w-full h-full border ${
                  isSlaved
                    ? 'border-[#EF4444] bg-[#EF4444]/10 shadow-[0_0_12px_rgba(239,68,68,0.5)]'
                    : 'border-[#00F2FF]/80 group-hover:border-[#00F2FF] bg-[#00F2FF]/5'
                }`}
              >
                {/* 4 Corner Markers */}
                <div className={`absolute -top-1 -left-1 w-2.5 h-2.5 border-t-2 border-l-2 ${isSlaved ? 'border-[#EF4444]' : 'border-[#00F2FF]'}`} />
                <div className={`absolute -top-1 -right-1 w-2.5 h-2.5 border-t-2 border-r-2 ${isSlaved ? 'border-[#EF4444]' : 'border-[#00F2FF]'}`} />
                <div className={`absolute -bottom-1 -left-1 w-2.5 h-2.5 border-b-2 border-l-2 ${isSlaved ? 'border-[#EF4444]' : 'border-[#00F2FF]'}`} />
                <div className={`absolute -bottom-1 -right-1 w-2.5 h-2.5 border-b-2 border-r-2 ${isSlaved ? 'border-[#EF4444]' : 'border-[#00F2FF]'}`} />

                {/* Pulsing center target cross if slaved */}
                {isSlaved && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Crosshair className="w-5 h-5 text-[#EF4444] animate-spin" style={{ animationDuration: '8s' }} />
                  </div>
                )}
              </div>

              {/* Floating Military Target Tag */}
              <div
                className={`absolute -top-6 left-0 px-1.5 py-0.5 rounded font-mono text-[9px] flex items-center gap-1.5 whitespace-nowrap shadow-md ${
                  isSlaved
                    ? 'bg-[#EF4444] text-white font-bold'
                    : 'bg-[#0B111A]/90 text-[#00F2FF] border border-[#00F2FF]/40'
                }`}
              >
                <span>{tgt.name.split(' ')[0]}</span>
                <span className="text-[8px] opacity-80">{tgt.classification.split(' ')[0]}</span>
                <span className="font-bold">{tgt.confidencePct.toFixed(1)}%</span>
              </div>

              {/* Bottom Slant Range / Info Bar */}
              <div className="absolute -bottom-4 left-0 text-[8px] font-mono text-slate-300 bg-black/80 px-1 rounded flex items-center gap-1">
                <span>RNG: {(tgt.slantRangeM / 1000).toFixed(1)}km</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    playTacticalClick();
                    onOpenTargetIntel(tgt);
                  }}
                  className="text-[#38BDF8] hover:underline"
                >
                  [INTEL]
                </button>
              </div>
            </div>
          );
        })}

        {/* Floating Top-Left Telemetry Readouts */}
        <div className="absolute top-2 left-2 z-20 font-mono text-[10px] space-y-0.5 text-slate-300 bg-[#0B111A]/80 p-2 rounded border border-[#1E2C3D] backdrop-blur-sm">
          <div className="flex items-center gap-2">
            <span className="text-slate-400">PAN:</span>
            <span className="text-white font-bold">{panDeg > 0 ? `+${panDeg.toFixed(1)}°` : `${panDeg.toFixed(1)}°`}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-slate-400">TILT:</span>
            <span className="text-white font-bold">{tiltDeg.toFixed(1)}°</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-slate-400">FOV:</span>
            <span className="text-[#00F2FF] font-bold">{fovDeg.toFixed(1)}° (NFOV)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-slate-400">ZOOM:</span>
            <span className="text-[#10B981] font-bold">{zoomLevel.toFixed(1)}x</span>
          </div>
        </div>

        {/* Floating Top-Right STANAG 3733 Laser Control Box */}
        <div className="absolute top-2 right-2 z-20 font-mono text-[10px] bg-[#0B111A]/80 p-2 rounded border border-[#1E2C3D] backdrop-blur-sm flex flex-col gap-1.5">
          <div className="flex items-center justify-between gap-3">
            <span className="text-slate-400">STANAG 3733 PRFC:</span>
            <span className="text-[#00F2FF] font-bold">CODE {laserCode}</span>
          </div>
          <button
            onClick={handleToggleLaser}
            className={`px-2.5 py-1 rounded text-[10px] font-bold flex items-center justify-center gap-1.5 transition-all shadow ${
              laserDesignatorActive
                ? 'bg-[#EF4444] hover:bg-[#DC2626] text-white animate-pulse'
                : 'bg-[#111A26] hover:bg-[#1E2C3D] border border-[#EF4444]/60 text-[#EF4444]'
            }`}
          >
            <Zap className="w-3.5 h-3.5" />
            <span>{laserDesignatorActive ? 'STOP DESIGNATION' : 'FIRE LASER DESIGNATOR'}</span>
          </button>
        </div>

        {/* Floating Bottom HUD Controls: Gimbal Pan/Tilt & Zoom Slider */}
        <div className="absolute bottom-2 left-2 right-2 z-20 bg-[#0B111A]/90 p-2 rounded border border-[#1E2C3D] backdrop-blur-sm flex items-center justify-between text-[11px] font-mono">
          {/* Zoom Slider */}
          <div className="flex items-center gap-2">
            <ZoomIn className="w-3.5 h-3.5 text-[#00F2FF]" />
            <span className="text-slate-400 text-[10px]">ZOOM:</span>
            <input
              type="range"
              min="1.0"
              max="60.0"
              step="0.5"
              value={zoomLevel}
              onChange={(e) => onUpdatePayload({ zoomLevel: parseFloat(e.target.value) })}
              className="w-28 accent-[#00F2FF] cursor-pointer h-1.5 bg-[#1E2C3D] rounded-lg"
            />
            <span className="text-white font-bold w-10 text-right">{zoomLevel.toFixed(1)}x</span>
          </div>

          {/* Gimbal Pan & Tilt Steppers */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1">
              <span className="text-slate-400 text-[10px]">PAN:</span>
              <button
                onClick={() => onUpdatePayload({ panDeg: Math.max(-180, panDeg - 5) })}
                className="px-1.5 py-0.5 bg-[#1E2C3D] hover:bg-[#2A3E54] text-white rounded text-[10px]"
              >
                ◀
              </button>
              <button
                onClick={() => onUpdatePayload({ panDeg: Math.min(180, panDeg + 5) })}
                className="px-1.5 py-0.5 bg-[#1E2C3D] hover:bg-[#2A3E54] text-white rounded text-[10px]"
              >
                ▶
              </button>
            </div>

            <div className="flex items-center gap-1">
              <span className="text-slate-400 text-[10px]">TILT:</span>
              <button
                onClick={() => onUpdatePayload({ tiltDeg: Math.min(15, tiltDeg + 5) })}
                className="px-1.5 py-0.5 bg-[#1E2C3D] hover:bg-[#2A3E54] text-white rounded text-[10px]"
              >
                ▲
              </button>
              <button
                onClick={() => onUpdatePayload({ tiltDeg: Math.max(-90, tiltDeg - 5) })}
                className="px-1.5 py-0.5 bg-[#1E2C3D] hover:bg-[#2A3E54] text-white rounded text-[10px]"
              >
                ▼
              </button>
            </div>
          </div>

          {/* Recenter & Unslave Button */}
          <div className="flex items-center gap-1.5">
            {slavedTargetId && (
              <button
                onClick={() => {
                  playTacticalClick();
                  onUpdatePayload({ slavedTargetId: null });
                }}
                className="px-2 py-0.5 bg-[#EF4444]/20 border border-[#EF4444]/60 text-[#EF4444] rounded text-[10px] font-bold hover:bg-[#EF4444]/30"
              >
                BREAK LOCK
              </button>
            )}
            <button
              onClick={() => {
                playTacticalClick();
                onUpdatePayload({ panDeg: 0, tiltDeg: -30, zoomLevel: 10 });
              }}
              className="px-2 py-0.5 bg-[#111A26] border border-[#1E2C3D] text-slate-300 hover:text-white rounded text-[10px]"
            >
              NADIR RECENTER
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
