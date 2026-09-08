import React, { useState } from 'react';
import { Mountain, Compass, Eye, ShieldAlert, ArrowUpRight } from 'lucide-react';
import { TelemetryState } from '../types/uav';
import { playTacticalClick } from '../utils/tacticalAudio';

interface PrimaryFlightDisplayProps {
  telemetry: TelemetryState;
  msaFl: string;
}

export const PrimaryFlightDisplay: React.FC<PrimaryFlightDisplayProps> = ({
  telemetry,
  msaFl,
}) => {
  const [displayMode, setDisplayMode] = useState<'ADI' | 'VSD'>('ADI');

  const {
    airspeedKts,
    commandedAirspeedKts,
    altitudeFt,
    commandedAltitudeFt,
    aglFt,
    headingDeg,
    commandedHeadingDeg,
    pitchDeg,
    rollDeg,
    verticalSpeedFpm,
    flightMode,
  } = telemetry;

  // Speed tape tick marks (window +/- 30 kts around current speed)
  const currentSpeedInt = Math.round(airspeedKts);
  const minSpeedTick = Math.floor((currentSpeedInt - 30) / 10) * 10;
  const maxSpeedTick = Math.ceil((currentSpeedInt + 30) / 10) * 10;
  const speedTicks = [];
  for (let s = minSpeedTick; s <= maxSpeedTick; s += 10) {
    speedTicks.push(s);
  }

  // Altitude tape tick marks (window +/- 400 ft around current altitude)
  const currentAltInt = Math.round(altitudeFt);
  const minAltTick = Math.floor((currentAltInt - 400) / 100) * 100;
  const maxAltTick = Math.ceil((currentAltInt + 400) / 100) * 100;
  const altTicks = [];
  for (let a = minAltTick; a <= maxAltTick; a += 100) {
    altTicks.push(a);
  }

  // Heading tape tick marks (window +/- 40 deg around current heading)
  const currentHdgInt = Math.round(headingDeg);
  const hdgTicks = [];
  for (let offset = -40; offset <= 40; offset += 10) {
    const rawHdg = (currentHdgInt + offset + 360) % 360;
    hdgTicks.push({ offset, hdg: rawHdg });
  }

  // Vertical speed needle calculation (-2000 to +2000 clamped to -80px to +80px)
  const clampedVsi = Math.max(-2000, Math.min(2000, verticalSpeedFpm));
  const vsiOffsetPx = -(clampedVsi / 2000) * 70; // negative goes up

  // Ground proximity warning flag
  const isGroundProximity = aglFt < 1000;

  return (
    <div className="relative w-full h-full bg-[#070A0F] border border-[#1E2C3D] rounded-md overflow-hidden flex flex-col select-none shadow-inner">
      {/* PFD Header Bar */}
      <div className="flex items-center justify-between px-2.5 py-1 bg-[#0B111A]/90 border-b border-[#1E2C3D] z-20">
        <div className="flex items-center gap-2 font-mono text-[10px]">
          <span className="px-1.5 py-0.5 bg-[#00F2FF]/20 text-[#00F2FF] border border-[#00F2FF]/40 rounded font-bold">
            ADI-01
          </span>
          <span className="text-slate-400">MODE:</span>
          <span className="text-white font-bold tracking-wider">{flightMode}</span>
          <span className="text-[#38BDF8] font-semibold">| MSA {msaFl}</span>
        </div>

        {/* ADI / VSD Toggle */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => {
              playTacticalClick();
              setDisplayMode('ADI');
            }}
            className={`px-2 py-0.5 rounded text-[10px] font-mono flex items-center gap-1 transition-all ${
              displayMode === 'ADI'
                ? 'bg-[#00F2FF]/20 text-[#00F2FF] border border-[#00F2FF]/50 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Eye className="w-3 h-3" />
            <span>ATTITUDE</span>
          </button>
          <button
            onClick={() => {
              playTacticalClick();
              setDisplayMode('VSD');
            }}
            className={`px-2 py-0.5 rounded text-[10px] font-mono flex items-center gap-1 transition-all ${
              displayMode === 'VSD'
                ? 'bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/50 font-bold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Mountain className="w-3 h-3" />
            <span>VSD TERRAIN</span>
          </button>
        </div>
      </div>

      {/* MAIN DISPLAY AREA */}
      <div className="relative flex-1 w-full h-full overflow-hidden">
        {displayMode === 'ADI' ? (
          /* ==========================================================================
             ARTIFICIAL HORIZON ATTITUDE DIRECTOR INDICATOR (ADI)
             ========================================================================== */
          <div className="relative w-full h-full flex items-center justify-center overflow-hidden">
            {/* Attitude Director Horizon Ball */}
            <div
              className="absolute w-[800px] h-[800px] transition-transform duration-100 ease-out"
              style={{
                transform: `rotate(${-rollDeg}deg) translateY(${pitchDeg * 5}px)`,
              }}
            >
              {/* Sky Half */}
              <div className="w-full h-1/2 bg-gradient-to-b from-[#07172B] via-[#0B2545] to-[#133A66] border-b-2 border-white relative">
                {/* Roll Angle Scale Arc */}
                <svg className="absolute bottom-0 left-0 w-full h-full" viewBox="0 0 800 400">
                  {/* Bank Angle Ticks: -45, -30, -20, -10, 0, +10, +20, +30, +45 */}
                  {[-45, -30, -20, -10, 0, 10, 20, 30, 45].map((angle) => {
                    const rad = ((angle - 90) * Math.PI) / 180;
                    const r1 = 190;
                    const r2 = angle % 30 === 0 ? 172 : 180;
                    const x1 = 400 + r1 * Math.cos(rad);
                    const y1 = 400 + r1 * Math.sin(rad);
                    const x2 = 400 + r2 * Math.cos(rad);
                    const y2 = 400 + r2 * Math.sin(rad);
                    return (
                      <line
                        key={angle}
                        x1={x1}
                        y1={y1}
                        x2={x2}
                        y2={y2}
                        stroke="#FFFFFF"
                        strokeWidth={angle === 0 ? 3 : 1.5}
                        opacity={0.85}
                      />
                    );
                  })}
                </svg>

                {/* Pitch Ladder (Sky Rungs +5, +10, +15, +20) */}
                <div className="absolute bottom-0 w-full flex flex-col items-center">
                  {[5, 10, 15, 20].map((deg) => (
                    <div
                      key={deg}
                      className="absolute flex items-center justify-center gap-1 font-mono text-[9px] text-white opacity-90"
                      style={{ bottom: `${deg * 10}px` }}
                    >
                      <span className="w-4 text-right">{deg}</span>
                      <div className="w-14 h-[2px] bg-white" />
                      <div className="w-4 h-[2px] border-b border-transparent" />
                      <div className="w-14 h-[2px] bg-white" />
                      <span className="w-4 text-left">{deg}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Ground Half */}
              <div className="w-full h-1/2 bg-gradient-to-t from-[#110E0C] via-[#1C1917] to-[#2B231D] relative">
                {/* Pitch Ladder (Ground Rungs -5, -10, -15, -20) */}
                <div className="absolute top-0 w-full flex flex-col items-center">
                  {[-5, -10, -15, -20].map((deg) => (
                    <div
                      key={deg}
                      className="absolute flex items-center justify-center gap-1 font-mono text-[9px] text-amber-200/90"
                      style={{ top: `${Math.abs(deg) * 10}px` }}
                    >
                      <span className="w-4 text-right">{Math.abs(deg)}</span>
                      <div className="w-14 h-[2px] bg-[#F59E0B] border-dashed border-b" />
                      <div className="w-4 h-[2px] border-b border-transparent" />
                      <div className="w-14 h-[2px] bg-[#F59E0B] border-dashed border-b" />
                      <span className="w-4 text-left">{Math.abs(deg)}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Static Aircraft Reference Symbol (MIL-STD Reticle) */}
            <div className="absolute z-10 pointer-events-none flex items-center justify-center">
              {/* Left Wing */}
              <div className="w-12 h-1.5 bg-[#00F2FF] shadow-[0_0_8px_rgba(0,242,255,0.8)] border border-black" />
              {/* Center Dot & Pip */}
              <div className="w-3 h-3 mx-2 rounded-full border-2 border-[#00F2FF] bg-black/50 shadow-[0_0_8px_rgba(0,242,255,0.8)] flex items-center justify-center">
                <div className="w-1 h-1 bg-[#00F2FF] rounded-full" />
              </div>
              {/* Right Wing */}
              <div className="w-12 h-1.5 bg-[#00F2FF] shadow-[0_0_8px_rgba(0,242,255,0.8)] border border-black" />
            </div>

            {/* Inverted Bank Triangle Pointer at Top Center */}
            <div className="absolute top-3 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
              <div className="w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[9px] border-t-[#00F2FF] shadow-[0_0_8px_rgba(0,242,255,0.8)]" />
            </div>

            {/* Velocity Vector Flight Path Marker (FPM) */}
            <div
              className="absolute z-10 pointer-events-none transition-transform duration-150"
              style={{
                transform: `translate(${-rollDeg * 1.5}px, ${-pitchDeg * 2}px)`,
              }}
            >
              <div className="w-4 h-4 rounded-full border border-[#10B981] flex items-center justify-center shadow-[0_0_6px_rgba(16,185,129,0.7)]">
                <div className="w-6 h-[1px] bg-[#10B981] absolute" />
                <div className="h-3 w-[1px] bg-[#10B981] absolute -top-1" />
              </div>
            </div>
          </div>
        ) : (
          /* ==========================================================================
             VERTICAL SITUATION DISPLAY (VSD TERRAIN PROFILE)
             ========================================================================== */
          <div className="relative w-full h-full bg-[#070A0F] p-4 flex flex-col justify-between">
            {/* VSD Status Badges */}
            <div className="flex items-center justify-between z-10 font-mono text-[10px]">
              <div className="flex items-center gap-2">
                <span className="text-slate-400">FLIGHT PROFILE:</span>
                <span className="text-[#F59E0B] font-bold">DIGITAL ELEVATION MODEL (DEM-30M)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-slate-400">MSA CEILING:</span>
                <span className="text-[#EF4444] font-bold">{msaFl} (26,000 FT)</span>
              </div>
            </div>

            {/* VSD Profile Vector SVG */}
            <div className="relative flex-1 w-full h-full py-2">
              <svg className="w-full h-full" viewBox="0 0 500 200" preserveAspectRatio="none">
                {/* Elevation Grid Lines (10k, 20k, 30k ft) */}
                <line x1="0" y1="50" x2="500" y2="50" stroke="#1E2C3D" strokeDasharray="3 3" />
                <text x="5" y="46" fill="#64748B" fontSize="9" fontFamily="monospace">25,000 FT (FL250)</text>

                <line x1="0" y1="100" x2="500" y2="100" stroke="#1E2C3D" strokeDasharray="3 3" />
                <text x="5" y="96" fill="#64748B" fontSize="9" fontFamily="monospace">18,000 FT (FL180)</text>

                <line x1="0" y1="150" x2="500" y2="150" stroke="#1E2C3D" strokeDasharray="3 3" />
                <text x="5" y="146" fill="#64748B" fontSize="9" fontFamily="monospace">10,000 FT (FL100)</text>

                {/* MSA dashed safety ceiling */}
                <line x1="0" y1="35" x2="500" y2="35" stroke="#EF4444" strokeWidth="1.5" strokeDasharray="4 4" opacity="0.8" />
                <text x="420" y="30" fill="#EF4444" fontSize="8" fontFamily="monospace">MSA LIMIT</text>

                {/* Layered Mountain Silhouette Polygons */}
                <polygon
                  points="0,200 60,160 120,130 180,110 240,140 310,95 380,125 440,150 500,170 500,200"
                  fill="#1E2C3D"
                  opacity="0.4"
                />
                <polygon
                  points="0,200 40,180 90,145 150,135 220,160 290,120 350,140 420,165 500,190 500,200"
                  fill="#2A3E54"
                  opacity="0.7"
                />
                <polygon
                  points="0,200 50,190 110,165 170,145 230,175 300,135 370,155 450,180 500,195 500,200"
                  fill="#111A26"
                  stroke="#F59E0B"
                  strokeWidth="1.2"
                />

                {/* Clearance Envelope Zone under UAV */}
                <rect x="180" y="60" width="140" height="75" fill="rgba(16, 185, 129, 0.08)" stroke="#10B981" strokeDasharray="2 2" />

                {/* UAV Position & Projected Glidepath Vector */}
                <circle cx="250" cy="58" r="4" fill="#00F2FF" />
                <line x1="250" y1="58" x2="380" y2="58" stroke="#00F2FF" strokeWidth="2" strokeDasharray="3 3" />
                <line x1="250" y1="58" x2="250" y2="135" stroke="#38BDF8" strokeWidth="1" strokeDasharray="2 2" />
              </svg>

              {/* Real-time UAV Callout */}
              <div className="absolute top-[28%] left-[48%] -translate-x-1/2 bg-[#0B111A] border border-[#00F2FF] px-2 py-0.5 rounded font-mono text-[9px] shadow-lg flex items-center gap-1.5">
                <span className="text-[#00F2FF] font-bold">TAPAS-07</span>
                <span className="text-slate-300">ALT: {altitudeFt.toLocaleString()} FT</span>
                <span className="text-[#10B981]">AGL: {aglFt.toLocaleString()} FT</span>
              </div>
            </div>

            {/* Terrain Proximity Legend */}
            <div className="flex items-center justify-between border-t border-[#1E2C3D] pt-1.5 font-mono text-[9px] text-slate-400">
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-[#10B981]" /> SAFE (&gt;2,000 FT AGL)
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-[#F59E0B]" /> CAUTION (1,000-2,000 FT)
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-[#EF4444]" /> DANGER (&lt;1,000 FT)
                </span>
              </div>
              <span className="text-[#38BDF8]">TERRAIN LOOKAHEAD: 15 NM</span>
            </div>
          </div>
        )}

        {/* ==========================================================================
            SPEED TAPE (LEFT SIDE)
            ========================================================================== */}
        <div className="absolute top-0 left-0 bottom-8 w-16 bg-[#0B111A]/85 border-r border-[#1E2C3D] flex flex-col justify-center items-end pr-1 z-15 font-mono select-none">
          {/* Target Commanded Airspeed Bug at Top */}
          <div className="absolute top-1 left-1 right-1 bg-[#111A26] border border-[#00F2FF]/40 rounded px-1 py-0.5 text-[9px] text-center text-[#00F2FF] font-bold">
            CMD {commandedAirspeedKts}
          </div>

          {/* Rolling Ticks */}
          <div className="relative w-full h-48 overflow-hidden flex flex-col justify-center items-end pr-1">
            {speedTicks.map((spd) => {
              const diff = spd - airspeedKts;
              const yOffset = -diff * 3.5; // pixel displacement
              const isOverSpeed = spd >= 180;
              const isStall = spd <= 65;

              return (
                <div
                  key={spd}
                  className="absolute right-0 flex items-center gap-1 text-[10px]"
                  style={{ transform: `translateY(${yOffset}px)` }}
                >
                  <span
                    className={`font-semibold ${
                      isOverSpeed ? 'text-[#EF4444]' : isStall ? 'text-[#F59E0B]' : 'text-slate-300'
                    }`}
                  >
                    {spd}
                  </span>
                  <div
                    className={`h-[1.5px] ${
                      isOverSpeed
                        ? 'w-3.5 bg-[#EF4444]'
                        : isStall
                        ? 'w-3.5 bg-[#F59E0B]'
                        : spd % 20 === 0
                        ? 'w-3 bg-white'
                        : 'w-1.5 bg-slate-400'
                    }`}
                  />
                </div>
              );
            })}
          </div>

          {/* Current Airspeed Readout Box with Pointer */}
          <div className="absolute left-1 right-0 bg-[#111A26] border-y-2 border-l-2 border-[#00F2FF] py-1 px-1 rounded-l text-right shadow-[0_0_8px_rgba(0,242,255,0.4)] flex items-center justify-between">
            <span className="text-[8px] text-slate-400 font-bold">IAS</span>
            <span className="text-xs font-bold text-white tracking-wider">
              {airspeedKts.toFixed(0)}
              <span className="text-[9px] text-[#00F2FF] ml-0.5">KT</span>
            </span>
          </div>

          {/* Stall / Overspeed warning ribbon indicator */}
          <div className="absolute bottom-1 left-1 right-1 text-[8px] text-center text-slate-400 font-bold">
            GS {Math.round(airspeedKts * 1.05)}
          </div>
        </div>

        {/* ==========================================================================
            ALTITUDE TAPE (RIGHT SIDE)
            ========================================================================== */}
        <div className="absolute top-0 right-7 bottom-8 w-20 bg-[#0B111A]/85 border-l border-[#1E2C3D] flex flex-col justify-center items-start pl-1 z-15 font-mono select-none">
          {/* Target Commanded Altitude Bug at Top */}
          <div className="absolute top-1 left-1 right-1 bg-[#111A26] border border-[#38BDF8]/40 rounded px-1 py-0.5 text-[9px] text-center text-[#38BDF8] font-bold">
            CMD {commandedAltitudeFt.toLocaleString()}
          </div>

          {/* Rolling Altitude Ticks */}
          <div className="relative w-full h-48 overflow-hidden flex flex-col justify-center items-start pl-1">
            {altTicks.map((alt) => {
              const diff = alt - altitudeFt;
              const yOffset = -(diff / 100) * 25; // 25px per 100ft

              return (
                <div
                  key={alt}
                  className="absolute left-0 flex items-center gap-1 text-[10px]"
                  style={{ transform: `translateY(${yOffset}px)` }}
                >
                  <div
                    className={`h-[1.5px] ${
                      alt % 500 === 0 ? 'w-3.5 bg-white' : 'w-2 bg-slate-400'
                    }`}
                  />
                  <span className={`font-semibold ${alt % 1000 === 0 ? 'text-white' : 'text-slate-300'}`}>
                    {alt}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Current Baro Altitude Readout Box */}
          <div className="absolute left-0 right-1 bg-[#111A26] border-y-2 border-r-2 border-[#38BDF8] py-1 px-1 rounded-r text-left shadow-[0_0_8px_rgba(56,189,248,0.4)] flex items-center justify-between">
            <span className="text-xs font-bold text-white tracking-wider">
              {Math.round(altitudeFt).toLocaleString()}
            </span>
            <span className="text-[8px] text-[#38BDF8] font-bold">FT</span>
          </div>

          {/* Radar Altimeter Readout (AGL) */}
          <div
            className={`absolute bottom-1 left-1 right-1 text-[8px] text-center font-bold px-1 py-0.5 rounded ${
              isGroundProximity
                ? 'bg-[#EF4444]/30 text-[#EF4444] border border-[#EF4444] animate-pulse'
                : 'bg-[#111A26] text-[#10B981]'
            }`}
          >
            AGL {Math.round(aglFt)} FT
          </div>
        </div>

        {/* ==========================================================================
            VERTICAL SPEED INDICATOR (VSI - FAR RIGHT)
            ========================================================================== */}
        <div className="absolute top-0 right-0 bottom-8 w-7 bg-[#070A0F] border-l border-[#1E2C3D] flex flex-col items-center justify-center font-mono text-[8px] z-15 text-slate-400">
          <span className="absolute top-2">+20</span>
          <span className="absolute top-1/4">+10</span>
          <div className="w-2.5 h-[1.5px] bg-slate-400" />
          <span className="absolute bottom-1/4">-10</span>
          <span className="absolute bottom-2">-20</span>

          {/* Dynamic Pointer Needle */}
          <div
            className="absolute right-0 w-4 h-2 flex items-center justify-end transition-transform duration-100 ease-out"
            style={{ transform: `translateY(${vsiOffsetPx}px)` }}
          >
            <div className="w-0 h-0 border-t-[4px] border-t-transparent border-b-[4px] border-b-transparent border-r-[7px] border-r-[#00F2FF]" />
          </div>
        </div>

        {/* Ground Proximity HUD Banner */}
        {isGroundProximity && (
          <div className="absolute top-10 left-1/2 -translate-x-1/2 bg-[#EF4444]/90 text-white font-mono text-xs font-bold px-4 py-1 rounded shadow-lg flex items-center gap-2 animate-bounce z-30">
            <ShieldAlert className="w-4 h-4" />
            <span>TERRAIN PULL UP: &lt;1,000 FT AGL</span>
          </div>
        )}
      </div>

      {/* ==========================================================================
          HEADING TAPE / COMPASS ROSE (BOTTOM BAR)
          ========================================================================== */}
      <div className="relative w-full h-8 bg-[#0B111A] border-t border-[#1E2C3D] flex items-center justify-center z-20 font-mono overflow-hidden">
        {/* Center Lubber Line */}
        <div className="absolute top-0 bottom-0 left-1/2 -translate-x-1/2 w-0.5 bg-[#00F2FF] z-20 shadow-[0_0_6px_rgba(0,242,255,0.8)]" />

        {/* Moving Heading Strip */}
        <div className="relative w-full h-full flex items-center justify-center">
          {hdgTicks.map(({ offset, hdg }) => {
            const xOffset = offset * 4.2; // 4.2px per degree
            const isCardinal = hdg === 0 || hdg === 90 || hdg === 180 || hdg === 270;
            const cardinalLabel =
              hdg === 0 ? 'N' : hdg === 90 ? 'E' : hdg === 180 ? 'S' : hdg === 270 ? 'W' : `${hdg}°`;

            return (
              <div
                key={`${offset}-${hdg}`}
                className="absolute flex flex-col items-center"
                style={{ transform: `translateX(${xOffset}px)` }}
              >
                <div
                  className={`h-2 ${
                    isCardinal ? 'w-1 bg-[#00F2FF]' : hdg % 30 === 0 ? 'w-0.5 bg-white' : 'w-0.5 bg-slate-500'
                  }`}
                />
                <span
                  className={`text-[9px] mt-0.5 ${
                    isCardinal
                      ? 'text-[#00F2FF] font-bold'
                      : hdg % 30 === 0
                      ? 'text-white'
                      : 'text-slate-400 text-[8px]'
                  }`}
                >
                  {cardinalLabel}
                </span>
              </div>
            );
          })}
        </div>

        {/* Commanded Heading Bug */}
        {Math.abs(commandedHeadingDeg - headingDeg) < 40 && (
          <div
            className="absolute top-0 z-20 text-[#F59E0B]"
            style={{
              transform: `translateX(${(commandedHeadingDeg - headingDeg) * 4.2}px)`,
            }}
          >
            <div className="w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-t-[6px] border-t-[#F59E0B]" />
          </div>
        )}

        {/* Digital Readout Left & Right */}
        <div className="absolute left-2 bg-[#111A26] px-1.5 py-0.5 rounded border border-[#1E2C3D] text-[10px] text-white font-bold flex items-center gap-1">
          <Compass className="w-3 h-3 text-[#00F2FF]" />
          <span>HDG: {Math.round(headingDeg)}°</span>
        </div>

        <div className="absolute right-2 bg-[#111A26] px-1.5 py-0.5 rounded border border-[#1E2C3D] text-[10px] text-[#F59E0B] font-bold flex items-center gap-1">
          <ArrowUpRight className="w-3 h-3" />
          <span>BUG: {Math.round(commandedHeadingDeg)}°</span>
        </div>
      </div>
    </div>
  );
};
