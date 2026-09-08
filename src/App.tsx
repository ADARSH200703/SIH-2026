import React, { useState, useEffect } from 'react';
import { 
  MOCK_SECTORS, 
  MOCK_FLEET, 
  INITIAL_TELEMETRY, 
  INITIAL_PAYLOAD, 
  INITIAL_LOGS, 
  MOCK_STANAG_PACKETS 
} from './data/mockMissionData';
import { 
  TelemetryState, 
  PayloadState, 
  ATRTarget, 
  Waypoint, 
  FleetUav, 
  SectorConfig, 
  TelemetryLogEntry, 
  StanagPacket 
} from './types/uav';
import { GcsHeader } from './components/GcsHeader';
import { SwarmFleetBar } from './components/SwarmFleetBar';
import { PrimaryFlightDisplay } from './components/PrimaryFlightDisplay';
import { TacticalCameraFeed } from './components/TacticalCameraFeed';
import { TacticalMissionMap } from './components/TacticalMissionMap';
import { MissionControlPanel } from './components/MissionControlPanel';
import { AvionicsHealthPanel } from './components/AvionicsHealthPanel';
import { TelemetryLogStream } from './components/TelemetryLogStream';
import { WaypointMissionPlanner } from './components/WaypointMissionPlanner';
import { StanagPacketInspectorModal } from './components/StanagPacketInspectorModal';
import { TargetIntelModal } from './components/TargetIntelModal';
import { AnomalyInjectorModal } from './components/AnomalyInjectorModal';
import { DefensePitchWalkthrough } from './components/DefensePitchWalkthrough';
import { SihEvaluationModal } from './components/SihEvaluationModal';
import { AerisGcsMasterDashboard } from './components/AerisGcsMasterDashboard';
import { setAudioMuted, isAudioMuted, playLaserPulse, playLockTone } from './utils/tacticalAudio';

export const App: React.FC = () => {
  // Global View Navigation State (DASHBOARD = Stitch Master GCS, COCKPIT = Tactical PFD & GIS)
  const [activeView, setActiveView] = useState<'DASHBOARD' | 'COCKPIT' | 'INTEL' | 'AVIONICS' | 'SIH_BRIEF'>('DASHBOARD');

  // Sectors & Fleet State
  const [currentSector, setCurrentSector] = useState<SectorConfig>(MOCK_SECTORS[0]);
  const [fleet, setFleet] = useState<FleetUav[]>(MOCK_FLEET);
  const [activeUavId, setActiveUavId] = useState<string>(MOCK_FLEET[0].id);

  // Core Subsystems State
  const [telemetry, setTelemetry] = useState<TelemetryState>(INITIAL_TELEMETRY);
  const [payload, setPayload] = useState<PayloadState>(INITIAL_PAYLOAD);
  const [waypoints, setWaypoints] = useState<Waypoint[]>(MOCK_SECTORS[0].initialWaypoints);
  const [targets, setTargets] = useState<ATRTarget[]>(MOCK_SECTORS[0].initialTargets);
  const [logs, setLogs] = useState<TelemetryLogEntry[]>(INITIAL_LOGS);
  const [packets] = useState<StanagPacket[]>(MOCK_STANAG_PACKETS);
  const [audioMuted, setAudioMutedState] = useState(false);

  // Modal Open States
  const [isWaypointPlannerOpen, setIsWaypointPlannerOpen] = useState(false);
  const [isPacketInspectorOpen, setIsPacketInspectorOpen] = useState(false);
  const [selectedIntelTarget, setSelectedIntelTarget] = useState<ATRTarget | null>(null);
  const [isAnomalyInjectorOpen, setIsAnomalyInjectorOpen] = useState(false);
  const [isSihScorecardOpen, setIsSihScorecardOpen] = useState(false);

  // Handle Sector Switching
  const handleSelectSector = (sectorId: string) => {
    const found = MOCK_SECTORS.find((s) => s.id === sectorId);
    if (found) {
      setCurrentSector(found);
      setWaypoints(found.initialWaypoints);
      setTargets(found.initialTargets);
      setTelemetry((prev) => ({
        ...prev,
        lat: found.baseLat + 0.08,
        lng: found.baseLng + 0.08,
        altitudeFt: found.defaultAltFt,
        commandedAltitudeFt: found.defaultAltFt,
      }));
    }
  };

  // Handle Fleet UAV Switching
  const handleSelectUav = (uavId: string) => {
    setActiveUavId(uavId);
    const selected = fleet.find((u) => u.id === uavId);
    if (selected) {
      setTelemetry((prev) => ({
        ...prev,
        altitudeFt: selected.altFt,
        commandedAltitudeFt: selected.altFt,
        airspeedKts: selected.speedKts,
        headingDeg: selected.headingDeg,
      }));
    }
  };

  // Audio Toggle
  const handleToggleMute = () => {
    const nextMuted = !audioMuted;
    setAudioMutedState(nextMuted);
    setAudioMuted(nextMuted);
  };

  // Subsystem Partial Updaters
  const handleUpdateTelemetry = (updates: Partial<TelemetryState>) => {
    setTelemetry((prev) => ({ ...prev, ...updates }));
  };

  const handleUpdatePayload = (updates: Partial<PayloadState>) => {
    setPayload((prev) => ({ ...prev, ...updates }));
  };

  // Add Dynamic Waypoint from Map Click
  const handleAddWaypointFromMap = (lat: number, lng: number) => {
    const newIndex = waypoints.length + 1;
    const newWp: Waypoint = {
      id: `WP_DYNAMIC_${Date.now()}`,
      index: newIndex,
      name: `WP-0${newIndex} TACTICAL POINT`,
      lat,
      lng,
      altFt: telemetry.commandedAltitudeFt,
      speedKts: telemetry.commandedAirspeedKts,
      action: 'SURVEILLANCE',
      demElevationFt: Math.round(currentSector.elevationMslFt + 1200),
      passed: false,
    };
    setWaypoints((prev) => [...prev, newWp]);

    // Add Audit Log
    const newLog: TelemetryLogEntry = {
      id: `log-${Date.now()}`,
      timestamp: new Date().toISOString().substring(11, 23),
      level: 'INFO',
      subsystem: 'NAV',
      message: `New waypoint WP-0${newIndex} inserted at ${lat.toFixed(4)}°N, ${lng.toFixed(4)}°E.`,
    };
    setLogs((prev) => [newLog, ...prev.slice(0, 49)]);
  };

  // ==========================================================================
  // 5Hz REAL-TIME FLIGHT LOOP & TELEMETRY SIMULATION
  // ==========================================================================
  useEffect(() => {
    const interval = setInterval(() => {
      setTelemetry((prev) => {
        // Natural turbulence & pitch/roll jitter
        const pitchJitter = (Math.random() - 0.5) * 0.4;
        const rollJitter = (Math.random() - 0.5) * 0.6;
        const speedJitter = (Math.random() - 0.5) * 0.5;

        // Smooth flight dynamics towards commanded setpoints
        const altDiff = prev.commandedAltitudeFt - prev.altitudeFt;
        const targetVsi = Math.max(-1500, Math.min(1500, altDiff * 1.5));
        const newVsi = prev.verticalSpeedFpm + (targetVsi - prev.verticalSpeedFpm) * 0.1;
        const newAlt = prev.altitudeFt + (newVsi / 60) * 0.2; // 0.2s delta

        const spdDiff = prev.commandedAirspeedKts - prev.airspeedKts;
        const newSpeed = prev.airspeedKts + spdDiff * 0.05 + speedJitter;

        const hdgDiff = ((prev.commandedHeadingDeg - prev.headingDeg + 540) % 360) - 180;
        const newHdg = (prev.headingDeg + hdgDiff * 0.04 + 360) % 360;

        // Position progression along heading
        const speedMps = (newSpeed * 1.852) / 3.6;
        const distKm = (speedMps * 0.2) / 1000;
        const radHdg = (newHdg * Math.PI) / 180;
        const dLat = (distKm * Math.cos(radHdg)) / 111.0;
        const dLng = (distKm * Math.sin(radHdg)) / (111.0 * Math.cos((prev.lat * Math.PI) / 180));

        // Fuel burn deduction
        const fuelBurnPerTick = (prev.fuelFlowLitersHr / 3600) * 0.2;
        const newFuel = Math.max(0, prev.fuelRemainingLiters - fuelBurnPerTick);

        // Simulated Rotax 914 engine variables with thermal dynamics
        const isOverheat = prev.activeAnomalies.includes('ENGINE_OVERHEAT');
        const targetCht = isOverheat ? 152.4 : 118.0 + (newSpeed / 160) * 12;
        const newCht = prev.chtC + (targetCht - prev.chtC) * 0.02;

        const targetEgt = isOverheat ? 845.0 : 680.0 + (newSpeed / 160) * 60;
        const newEgt = prev.egtC + (targetEgt - prev.egtC) * 0.02;

        const isLinkDropped = prev.activeAnomalies.includes('LINK_LOSS');
        const dliLat = isLinkDropped ? 180 + Math.random() * 20 : 22 + Math.random() * 5;

        return {
          ...prev,
          pitchDeg: parseFloat((prev.pitchDeg * 0.9 + pitchJitter).toFixed(2)),
          rollDeg: parseFloat((prev.rollDeg * 0.9 + rollJitter).toFixed(2)),
          airspeedKts: parseFloat(newSpeed.toFixed(1)),
          altitudeFt: parseFloat(newAlt.toFixed(1)),
          aglFt: parseFloat(Math.max(100, newAlt - currentSector.elevationMslFt).toFixed(1)),
          headingDeg: parseFloat(newHdg.toFixed(1)),
          verticalSpeedFpm: parseFloat(newVsi.toFixed(0)),
          lat: prev.lat + dLat,
          lng: prev.lng + dLng,
          flightTimeSec: prev.flightTimeSec + 0.2,
          fuelRemainingLiters: parseFloat(newFuel.toFixed(2)),
          chtC: parseFloat(newCht.toFixed(1)),
          egtC: parseFloat(newEgt.toFixed(1)),
          dliLatencyMs: parseFloat(dliLat.toFixed(1)),
        };
      });

      // Handle Laser Designator Countdown
      setPayload((prev) => {
        if (prev.laserDesignatorActive && prev.laserCountdownSec > 0) {
          const nextSec = prev.laserCountdownSec - 0.2;
          if (nextSec <= 0) {
            return { ...prev, laserDesignatorActive: false, laserCountdownSec: 0 };
          }
          return { ...prev, laserCountdownSec: parseFloat(nextSec.toFixed(1)) };
        }
        return prev;
      });
    }, 200); // 5Hz loop

    return () => clearInterval(interval);
  }, [currentSector.elevationMslFt]);

  return (
    <div className="w-screen h-screen bg-[#070A0F] text-slate-100 flex flex-col overflow-hidden select-none">
      {/* 1. TOP MILITARY COMMAND BAR */}
      <GcsHeader
        activeView={activeView}
        setActiveView={setActiveView}
        currentSector={currentSector}
        allSectors={MOCK_SECTORS}
        onSelectSector={handleSelectSector}
        telemetry={telemetry}
        isMuted={audioMuted}
        onToggleMute={handleToggleMute}
        onOpenPacketInspector={() => setIsPacketInspectorOpen(true)}
        onOpenAnomalyInjector={() => setIsAnomalyInjectorOpen(true)}
        onOpenSihScorecard={() => setIsSihScorecardOpen(true)}
      />

      {/* 2. SWARM SQUADRON FORMATION RIBBON */}
      <SwarmFleetBar
        fleet={fleet}
        activeUavId={activeUavId}
        onSelectUav={handleSelectUav}
      />

      {/* 3. MAIN WORKSPACE VIEW ROUTING */}
      <main className="flex-1 w-full overflow-hidden flex flex-col">
        {activeView === 'DASHBOARD' && (
          <div className="flex-1 w-full h-full overflow-y-auto">
            <AerisGcsMasterDashboard onSwitchToCockpit={() => setActiveView('COCKPIT')} />
          </div>
        )}

        {activeView === 'COCKPIT' && (
          <div className="flex-1 flex flex-col gap-2 overflow-hidden p-2">
            {/* Upper Tactical Workspace: PFD + Camera Feed + Airspace Map */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-2 overflow-hidden min-h-[360px]">
              {/* Left: Primary Flight Display (ADI / VSD) */}
              <div className="w-full h-full overflow-hidden">
                <PrimaryFlightDisplay
                  telemetry={telemetry}
                  msaFl={currentSector.msaFl}
                />
              </div>

              {/* Center: Multi-Spectral Camera Feed (EO / FLIR / SAR) */}
              <div className="w-full h-full overflow-hidden">
                <TacticalCameraFeed
                  payload={payload}
                  targets={targets}
                  onUpdatePayload={handleUpdatePayload}
                  onSelectTarget={(tgt) => {
                    setSelectedIntelTarget(tgt);
                    handleUpdatePayload({ slavedTargetId: tgt.id });
                  }}
                  onOpenTargetIntel={(tgt) => setSelectedIntelTarget(tgt)}
                />
              </div>

              {/* Right: Tactical Vector GIS Map */}
              <div className="w-full h-full overflow-hidden">
                <TacticalMissionMap
                  sector={currentSector}
                  telemetry={telemetry}
                  waypoints={waypoints}
                  targets={targets}
                  onAddWaypoint={handleAddWaypointFromMap}
                  onOpenRoutePlanner={() => setIsWaypointPlannerOpen(true)}
                  onSelectTarget={(tgt) => setSelectedIntelTarget(tgt)}
                />
              </div>
            </div>

            {/* Lower Tactical Workspace: Autopilot Controls + Audit Log Stream */}
            <div className="h-44 grid grid-cols-1 lg:grid-cols-3 gap-2 overflow-hidden">
              {/* Autopilot Controls (Spans 2 columns) */}
              <div className="lg:col-span-2 h-full overflow-hidden">
                <MissionControlPanel
                  telemetry={telemetry}
                  onUpdateTelemetry={handleUpdateTelemetry}
                />
              </div>

              {/* Audit Log Stream (Spans 1 column) */}
              <div className="h-full overflow-hidden">
                <TelemetryLogStream
                  logs={logs}
                  onClearLogs={() => setLogs([])}
                />
              </div>
            </div>
          </div>
        )}

        {activeView === 'INTEL' && (
          <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-2 overflow-hidden">
            <div className="lg:col-span-2 h-full">
              <TacticalCameraFeed
                payload={payload}
                targets={targets}
                onUpdatePayload={handleUpdatePayload}
                onSelectTarget={(tgt) => setSelectedIntelTarget(tgt)}
                onOpenTargetIntel={(tgt) => setSelectedIntelTarget(tgt)}
              />
            </div>
            <div className="h-full">
              <TacticalMissionMap
                sector={currentSector}
                telemetry={telemetry}
                waypoints={waypoints}
                targets={targets}
                onAddWaypoint={handleAddWaypointFromMap}
                onOpenRoutePlanner={() => setIsWaypointPlannerOpen(true)}
                onSelectTarget={(tgt) => setSelectedIntelTarget(tgt)}
              />
            </div>
          </div>
        )}

        {activeView === 'AVIONICS' && (
          <div className="flex-1 w-full h-full overflow-hidden">
            <AvionicsHealthPanel telemetry={telemetry} />
          </div>
        )}

        {activeView === 'SIH_BRIEF' && (
          <div className="flex-1 w-full h-full overflow-hidden">
            <DefensePitchWalkthrough
              onOpenAnomalyInjector={() => setIsAnomalyInjectorOpen(true)}
              onOpenPacketInspector={() => setIsPacketInspectorOpen(true)}
              onOpenScorecard={() => setIsSihScorecardOpen(true)}
            />
          </div>
        )}
      </main>

      {/* 4. MODALS & DIAGNOSTIC TOOLS */}
      {isWaypointPlannerOpen && (
        <WaypointMissionPlanner
          waypoints={waypoints}
          onUpdateWaypoints={(newWps) => setWaypoints(newWps)}
          onClose={() => setIsWaypointPlannerOpen(false)}
        />
      )}

      {isPacketInspectorOpen && (
        <StanagPacketInspectorModal
          packets={packets}
          onClose={() => setIsPacketInspectorOpen(false)}
        />
      )}

      {selectedIntelTarget && (
        <TargetIntelModal
          target={selectedIntelTarget}
          onClose={() => setSelectedIntelTarget(null)}
          onSlaveGimbal={(targetId) => {
            handleUpdatePayload({ slavedTargetId: targetId });
          }}
          onFireLaser={() => {
            handleUpdatePayload({
              laserDesignatorActive: true,
              laserCountdownSec: 20,
            });
          }}
        />
      )}

      {isAnomalyInjectorOpen && (
        <AnomalyInjectorModal
          telemetry={telemetry}
          onUpdateTelemetry={handleUpdateTelemetry}
          onClose={() => setIsAnomalyInjectorOpen(false)}
        />
      )}

      {isSihScorecardOpen && (
        <SihEvaluationModal onClose={() => setIsSihScorecardOpen(false)} />
      )}
    </div>
  );
};
