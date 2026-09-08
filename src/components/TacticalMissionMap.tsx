import React, { useState } from 'react';
import { 
  Navigation, 
  Plus, 
  MapPin, 
  Compass, 
  Layers, 
  ShieldAlert, 
  Crosshair, 
  Route 
} from 'lucide-react';
import { SectorConfig, TelemetryState, Waypoint, ATRTarget } from '../types/uav';
import { playTacticalClick, playLockTone } from '../utils/tacticalAudio';

interface TacticalMissionMapProps {
  sector: SectorConfig;
  telemetry: TelemetryState;
  waypoints: Waypoint[];
  targets: ATRTarget[];
  onAddWaypoint: (lat: number, lng: number) => void;
  onOpenRoutePlanner: () => void;
  onSelectTarget: (target: ATRTarget) => void;
}

export const TacticalMissionMap: React.FC<TacticalMissionMapProps> = ({
  sector,
  telemetry,
  waypoints,
  targets,
  onAddWaypoint,
  onOpenRoutePlanner,
  onSelectTarget,
}) => {
  const [isAddMode, setIsAddMode] = useState(false);
  const [hoveredWaypoint, setHoveredWaypoint] = useState<Waypoint | null>(null);
  const [hoveredTarget, setHoveredTarget] = useState<ATRTarget | null>(null);

  // Map coordinate boundary box centered around sector base
  const latDelta = 0.55;
  const lngDelta = 0.85;
  const minLat = sector.baseLat - latDelta / 2;
  const maxLat = sector.baseLat + latDelta / 2;
  const minLng = sector.baseLng - lngDelta / 2;
  const maxLng = sector.baseLng + lngDelta / 2;

  // Convert lat/lng to SVG coordinates (0 - 800 width, 0 - 500 height)
  const project = (lat: number, lng: number) => {
    const x = ((lng - minLng) / lngDelta) * 800;
    const y = ((maxLat - lat) / latDelta) * 500; // inverted Y
    return { x, y };
  };

  const unproject = (x: number, y: number) => {
    const lng = minLng + (x / 800) * lngDelta;
    const lat = maxLat - (y / 500) * latDelta;
    return { lat, lng };
  };

  const uavPos = project(telemetry.lat, telemetry.lng);

  const handleSvgClick = (e: React.MouseEvent<SVGSVGElement>) => {
    if (!isAddMode) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = ((e.clientX - rect.left) / rect.width) * 800;
    const clickY = ((e.clientY - rect.top) / rect.height) * 500;

    const { lat, lng } = unproject(clickX, clickY);
    playTacticalClick();
    onAddWaypoint(lat, lng);
    setIsAddMode(false);
  };

  return (
    <div className="relative w-full h-full bg-[#070A0F] border border-[#1E2C3D] rounded-md overflow-hidden flex flex-col select-none shadow-inner">
      {/* Top Map Header Bar */}
      <div className="flex items-center justify-between px-2.5 py-1 bg-[#0B111A]/90 border-b border-[#1E2C3D] z-20 font-mono text-[10px]">
        <div className="flex items-center gap-2">
          <span className="px-1.5 py-0.5 bg-[#00F2FF]/20 text-[#00F2FF] border border-[#00F2FF]/40 rounded font-bold">
            VECTOR GIS C2
          </span>
          <span className="text-slate-400">SECTOR:</span>
          <span className="text-white font-bold">{sector.name}</span>
          <span className="text-[#38BDF8]">| {waypoints.length} WAYPOINTS</span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => {
              playTacticalClick();
              setIsAddMode(!isAddMode);
            }}
            className={`px-2 py-0.5 rounded text-[10px] flex items-center gap-1 transition-all ${
              isAddMode
                ? 'bg-[#10B981] text-black font-bold shadow-[0_0_8px_#10B981]'
                : 'bg-[#111A26] border border-[#1E2C3D] text-slate-300 hover:text-white'
            }`}
          >
            <Plus className="w-3 h-3" />
            <span>{isAddMode ? 'CLICK MAP TO DROP' : 'ADD WAYPOINT'}</span>
          </button>

          <button
            onClick={() => {
              playTacticalClick();
              onOpenRoutePlanner();
            }}
            className="px-2 py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#00F2FF]/40 text-[#00F2FF] rounded text-[10px] font-bold flex items-center gap-1 transition-all"
          >
            <Route className="w-3 h-3" />
            <span>ROUTE PLANNER</span>
          </button>
        </div>
      </div>

      {/* Main SVG Vector Tactical Map */}
      <div className="relative flex-1 w-full h-full overflow-hidden bg-[#070A0F] flex items-center justify-center">
        <svg
          className={`w-full h-full ${isAddMode ? 'cursor-crosshair' : 'cursor-default'}`}
          viewBox="0 0 800 500"
          onClick={handleSvgClick}
        >
          {/* Tactical Graticule Grid Lines */}
          <g stroke="#1E2C3D" strokeWidth="1" strokeDasharray="3 3">
            <line x1="160" y1="0" x2="160" y2="500" />
            <line x1="320" y1="0" x2="320" y2="500" />
            <line x1="480" y1="0" x2="480" y2="500" />
            <line x1="640" y1="0" x2="640" y2="500" />

            <line x1="0" y1="125" x2="800" y2="125" />
            <line x1="0" y1="250" x2="800" y2="250" />
            <line x1="0" y1="375" x2="800" y2="375" />
          </g>

          {/* Coordinate Graticule Text */}
          <text x="10" y="25" fill="#475569" fontSize="9" fontFamily="monospace">
            {sector.baseLat.toFixed(2)}°N / {sector.baseLng.toFixed(2)}°E GRID
          </text>

          {/* ==========================================================================
              NO-FLY ZONES (NFZ CORRIDORS)
              ========================================================================== */}
          {sector.noFlyZones.map((nfz) => {
            const pathPoints = nfz.points.map((p) => {
              const pt = project(p.lat, p.lng);
              return `${pt.x},${pt.y}`;
            }).join(' ');

            return (
              <g key={nfz.id}>
                <polygon
                  points={pathPoints}
                  fill="rgba(239, 68, 68, 0.12)"
                  stroke="#EF4444"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
                <text
                  x={project(nfz.points[0].lat, nfz.points[0].lng).x + 10}
                  y={project(nfz.points[0].lat, nfz.points[0].lng).y + 15}
                  fill="#EF4444"
                  fontSize="9"
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  {nfz.name}
                </text>
              </g>
            );
          })}

          {/* ==========================================================================
              SAM MISSILE ENGAGEMENT DOMES (HQ-9 / S-300)
              ========================================================================== */}
          {sector.samRings.map((sam) => {
            const samPos = project(sam.lat, sam.lng);
            // 1 km approx 8px scale in projection
            const lethalRadiusPx = sam.lethalRadiusKm * 5.2;
            const detectionRadiusPx = sam.detectionRadiusKm * 5.2;

            return (
              <g key={sam.id}>
                {/* Early Warning Radar Detection Envelope */}
                <circle
                  cx={samPos.x}
                  cy={samPos.y}
                  r={detectionRadiusPx}
                  fill="rgba(245, 158, 11, 0.04)"
                  stroke="#F59E0B"
                  strokeWidth="1"
                  strokeDasharray="3 3"
                />

                {/* Lethal Missile Engagement Ring */}
                <circle
                  cx={samPos.x}
                  cy={samPos.y}
                  r={lethalRadiusPx}
                  fill="rgba(239, 68, 68, 0.15)"
                  stroke="#EF4444"
                  strokeWidth="1.8"
                />

                {/* Center SAM Launcher Marker */}
                <rect
                  x={samPos.x - 5}
                  y={samPos.y - 5}
                  width="10"
                  height="10"
                  fill="#EF4444"
                  stroke="#000000"
                  strokeWidth="1.5"
                />
                <text
                  x={samPos.x + 8}
                  y={samPos.y + 3}
                  fill="#EF4444"
                  fontSize="9"
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  {sam.type} [LETHAL {sam.lethalRadiusKm}km]
                </text>
              </g>
            );
          })}

          {/* ==========================================================================
              FLIGHT CORRIDOR LEGS (WAYPOINTS CONNECTING LINES)
              ========================================================================== */}
          {waypoints.map((wp, idx) => {
            if (idx === waypoints.length - 1) return null;
            const nextWp = waypoints[idx + 1];
            const p1 = project(wp.lat, wp.lng);
            const p2 = project(nextWp.lat, nextWp.lng);

            return (
              <line
                key={`leg-${wp.id}-${nextWp.id}`}
                x1={p1.x}
                y1={p1.y}
                x2={p2.x}
                y2={p2.y}
                stroke="#00F2FF"
                strokeWidth="1.5"
                strokeDasharray="4 4"
                opacity="0.8"
              />
            );
          })}

          {/* Active Leg from UAV to Next Active Waypoint */}
          {waypoints.length > 1 && (
            <line
              x1={uavPos.x}
              y1={uavPos.y}
              x2={project(waypoints[1].lat, waypoints[1].lng).x}
              y2={project(waypoints[1].lat, waypoints[1].lng).y}
              stroke="#10B981"
              strokeWidth="2"
              strokeDasharray="2 2"
            />
          )}

          {/* ==========================================================================
              WAYPOINTS (TACTICAL DIAMONDS)
              ========================================================================== */}
          {waypoints.map((wp) => {
            const p = project(wp.lat, wp.lng);
            const isHovered = hoveredWaypoint?.id === wp.id;

            return (
              <g
                key={wp.id}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredWaypoint(wp)}
                onMouseLeave={() => setHoveredWaypoint(null)}
              >
                {/* Tactical Diamond Polygon */}
                <polygon
                  points={`${p.x},${p.y - 7} ${p.x + 7},${p.y} ${p.x},${p.y + 7} ${p.x - 7},${p.y}`}
                  fill={wp.passed ? '#1E2C3D' : '#00F2FF'}
                  stroke="#000000"
                  strokeWidth="1.5"
                />

                {/* Waypoint Number Label */}
                <text
                  x={p.x + 9}
                  y={p.y - 2}
                  fill={wp.passed ? '#64748B' : '#FFFFFF'}
                  fontSize="9"
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  WP-{wp.index}
                </text>
                <text
                  x={p.x + 9}
                  y={p.y + 8}
                  fill="#38BDF8"
                  fontSize="8"
                  fontFamily="monospace"
                >
                  FL{Math.round(wp.altFt / 100)} / {wp.speedKts}KT
                </text>
              </g>
            );
          })}

          {/* ==========================================================================
              ATR HOSTILE / DETECTED TARGETS
              ========================================================================== */}
          {targets.map((tgt) => {
            const p = project(tgt.lat, tgt.lng);
            const isHovered = hoveredTarget?.id === tgt.id;

            return (
              <g
                key={tgt.id}
                className="cursor-pointer"
                onClick={() => {
                  playLockTone();
                  onSelectTarget(tgt);
                }}
                onMouseEnter={() => setHoveredTarget(tgt)}
                onMouseLeave={() => setHoveredTarget(null)}
              >
                {/* Target Hostile Marker Ring */}
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={tgt.slaved ? '8' : '6'}
                  fill={tgt.hostile ? 'rgba(239,68,68,0.3)' : 'rgba(0,242,255,0.3)'}
                  stroke={tgt.hostile ? '#EF4444' : '#00F2FF'}
                  strokeWidth="2"
                />
                {tgt.slaved && (
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r="12"
                    fill="none"
                    stroke="#EF4444"
                    strokeWidth="1"
                    strokeDasharray="2 2"
                  />
                )}
                <text
                  x={p.x + 10}
                  y={p.y + 3}
                  fill={tgt.hostile ? '#EF4444' : '#00F2FF'}
                  fontSize="9"
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  {tgt.name.split(' ')[0]} ({tgt.confidencePct.toFixed(0)}%)
                </text>
              </g>
            );
          })}

          {/* ==========================================================================
              UAV POSITION, VECTOR & CONCENTRIC RANGE RINGS
              ========================================================================== */}
          {/* Concentric Range Rings (10km, 25km, 50km) */}
          <circle cx={uavPos.x} cy={uavPos.y} r={10 * 5.2} fill="none" stroke="#1E2C3D" strokeWidth="1" strokeDasharray="2 2" />
          <text x={uavPos.x + 10 * 5.2 + 2} y={uavPos.y} fill="#475569" fontSize="7" fontFamily="monospace">10km</text>

          <circle cx={uavPos.x} cy={uavPos.y} r={25 * 5.2} fill="none" stroke="#1E2C3D" strokeWidth="1" strokeDasharray="3 3" />
          <text x={uavPos.x + 25 * 5.2 + 2} y={uavPos.y} fill="#475569" fontSize="7" fontFamily="monospace">25km</text>

          {/* 3-Minute Projected Velocity Track Vector Line */}
          <line
            x1={uavPos.x}
            y1={uavPos.y}
            x2={uavPos.x + Math.sin((telemetry.headingDeg * Math.PI) / 180) * 55}
            y2={uavPos.y - Math.cos((telemetry.headingDeg * Math.PI) / 180) * 55}
            stroke="#00F2FF"
            strokeWidth="2"
          />

          {/* TAPAS UAV Vector Aircraft Silhouette */}
          <g
            transform={`translate(${uavPos.x}, ${uavPos.y}) rotate(${telemetry.headingDeg})`}
          >
            {/* Fuselage & Wings */}
            <path
              d="M0,-12 L4,-2 L18,4 L18,7 L4,4 L3,12 L7,15 L7,17 L-7,17 L-7,15 L-3,12 L-4,4 L-18,7 L-18,4 L-4,-2 Z"
              fill="#00F2FF"
              stroke="#000000"
              strokeWidth="1"
            />
          </g>
        </svg>

        {/* Tactical Map Compass Rose / North Arrow Overlay */}
        <div className="absolute top-2 right-2 p-1.5 bg-[#0B111A]/80 rounded border border-[#1E2C3D] font-mono text-[9px] text-center flex flex-col items-center">
          <Compass className="w-4 h-4 text-[#00F2FF] animate-pulse" />
          <span className="text-[#00F2FF] font-bold mt-0.5">N</span>
        </div>

        {/* Hovered Waypoint Tooltip */}
        {hoveredWaypoint && (
          <div className="absolute bottom-3 left-3 bg-[#0B111A] border border-[#00F2FF] p-2 rounded shadow-xl font-mono text-[10px] z-30 space-y-0.5">
            <div className="text-white font-bold">{hoveredWaypoint.name}</div>
            <div className="text-[#38BDF8]">
              ALT: {hoveredWaypoint.altFt.toLocaleString()} FT | SPD: {hoveredWaypoint.speedKts} KT
            </div>
            <div className="text-slate-400">
              DEM ELEVATION: {hoveredWaypoint.demElevationFt.toLocaleString()} FT MSL
            </div>
            <div className="text-[#10B981]">ACTION: {hoveredWaypoint.action}</div>
          </div>
        )}

        {/* Hovered Target Tooltip */}
        {hoveredTarget && (
          <div className="absolute bottom-3 right-3 bg-[#0B111A] border border-[#EF4444] p-2 rounded shadow-xl font-mono text-[10px] z-30 space-y-0.5">
            <div className="text-[#EF4444] font-bold">{hoveredTarget.name}</div>
            <div className="text-white">{hoveredTarget.classification}</div>
            <div className="text-[#38BDF8]">
              CONFIDENCE: {hoveredTarget.confidencePct.toFixed(1)}% | RANGE: {(hoveredTarget.slantRangeM / 1000).toFixed(1)}km
            </div>
            <div className="text-slate-400">
              LAT/LNG: {hoveredTarget.lat.toFixed(4)}°N, {hoveredTarget.lng.toFixed(4)}°E
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
