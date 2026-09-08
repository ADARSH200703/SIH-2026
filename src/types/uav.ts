export type FlightMode = 
  | 'MANUAL' 
  | 'AUTO_NAV' 
  | 'LOITER_HOLD' 
  | 'TERRAIN_FOLLOW' 
  | 'RTH_FAILSAFE';

export type SensorPalette = 
  | 'EO' 
  | 'FLIR_WHITE' 
  | 'FLIR_BLACK' 
  | 'FLIR_IRONBOW' 
  | 'SAR';

export type LogLevel = 'INFO' | 'WARNING' | 'CAUTION' | 'EMERGENCY' | 'SUCCESS';
export type Subsystem = 'NAV' | 'AVIONICS' | 'PAYLOAD' | 'ATR' | 'DATALINK';

export interface TelemetryState {
  // Flight dynamics & Navigation
  airspeedKts: number;
  commandedAirspeedKts: number;
  altitudeFt: number;
  commandedAltitudeFt: number;
  aglFt: number;
  headingDeg: number;
  commandedHeadingDeg: number;
  pitchDeg: number;
  rollDeg: number;
  verticalSpeedFpm: number;
  lat: number;
  lng: number;
  flightMode: FlightMode;
  flightTimeSec: number;
  gpsSats: number;
  gpsQuality: '3D_FIX' | 'DGPS' | 'RTK' | 'JAMMED' | 'DENIED';

  // Rotax 914 Turbocharged Engine & Propulsion
  rpm: number;
  chtC: number;           // Cylinder Head Temp (<135 nominal, 150 redline)
  egtC: number;           // Exhaust Gas Temp (<750 nominal, 850 redline)
  oilPressureBar: number; // 2.5 - 5.0 nominal
  oilTempC: number;       // 70 - 110 nominal
  mapInHg: number;        // Manifold Absolute Pressure (25 - 40 inHg)
  engineHealthPct: number;
  engineLoadPct: number;

  // Electrical & Power
  generatorVoltageV: number; // 28.0V nominal
  batteryVoltageV: number;   // 25.2V nominal
  busCurrentA: number;       // 32.4A nominal
  batterySoCPct: number;     // 98% nominal

  // Fuel Subsystem
  fuelRemainingLiters: number;
  fuelCapacityLiters: number;
  fuelFlowLitersHr: number;
  bingoFuelThresholdLiters: number;

  // Flight Control Surfaces & Actuators (degrees deflection)
  aileronLeftDeg: number;
  aileronRightDeg: number;
  elevatorDeg: number;
  rudderDeg: number;
  flapsDeg: number;

  // Gear & Environmental
  gearState: 'LOCKED_DOWN' | 'IN_TRANSIT' | 'RETRACTED';
  pitotHeatActive: boolean;
  avionicsBayTempC: number;
  oatC: number; // Outside Air Temp

  // Datalink & EW
  datalinkStrengthPct: number;
  datalinkBand: 'C_BAND' | 'KU_SATCOM' | 'LOS_UHF';
  dliLatencyMs: number;
  ewJammingDetected: boolean;
  activeAnomalies: string[];
}

export interface PayloadState {
  palette: SensorPalette;
  zoomLevel: number;        // 1.0x to 60.0x
  panDeg: number;           // -180 to +180
  tiltDeg: number;          // -90 to +15 (nadir to horizon)
  fovDeg: number;           // 1.2° to 45°
  laserDesignatorActive: boolean;
  laserCode: number;        // STANAG 3733 code e.g., 1688
  laserCountdownSec: number;
  slavedTargetId: string | null;
  gyroStabilized: boolean;
  reticleMode: 'TACTICAL_CROSSHAIR' | 'MIL_STD_GRID' | 'TRACKING_BOX' | 'CLEAN';
}

export interface ATRTarget {
  id: string;
  name: string;
  classification: string;
  milStdCode: string; // e.g., "SFGPUCI----"
  confidencePct: number;
  hostile: boolean;
  lat: number;
  lng: number;
  altMslFt: number;
  slantRangeM: number;
  speedKts: number;
  headingDeg: number;
  bbox: {
    x: number; // 0 - 100 percentage inside camera frame
    y: number;
    w: number;
    h: number;
  };
  threatLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'DETECTED' | 'TRACKING' | 'LOCKED' | 'DESIGNATED';
  lastSeenSecAgo: number;
  slaved: boolean;
  notes: string;
}

export interface Waypoint {
  id: string;
  index: number;
  name: string;
  lat: number;
  lng: number;
  altFt: number;
  speedKts: number;
  action: 'FLYOVER' | 'LOITER' | 'SURVEILLANCE' | 'STRIKE_COORDINATE' | 'TOUCHDOWN';
  loiterTimeSec?: number;
  demElevationFt: number;
  turnRadiusM?: number;
  passed?: boolean;
}

export interface FleetUav {
  id: string;
  callsign: string;
  model: string;
  role: 'RECONNAISSANCE' | 'STRIKE_ESCORT' | 'EW_COMM_RELAY';
  status: 'AIRBORNE_ACTIVE' | 'AIRBORNE_STANDBY' | 'RTB' | 'MAINTENANCE';
  lat: number;
  lng: number;
  altFt: number;
  speedKts: number;
  headingDeg: number;
  fuelPct: number;
  linkStrengthPct: number;
  isLeader: boolean;
  assignedSectorId: string;
}

export interface SamThreatRing {
  id: string;
  name: string;
  type: 'HQ-9B' | 'S-300' | 'PANTSIR-S1' | 'RADAR_EARLY_WARNING';
  lat: number;
  lng: number;
  lethalRadiusKm: number;
  detectionRadiusKm: number;
  maxEngageAltFt: number;
  active: boolean;
}

export interface NoFlyZone {
  id: string;
  name: string;
  type: 'RESTRICTED_AIRSPACE' | 'CIVILIAN_CORRIDOR' | 'JAMMING_HAZARD';
  points: Array<{ lat: number; lng: number }>;
}

export interface SectorConfig {
  id: string;
  name: string;
  code: string;
  description: string;
  baseLat: number;
  baseLng: number;
  coordinatesBadge: string;
  elevationMslFt: number;
  defaultAltFt: number;
  msaFl: string; // Minimum Safe Altitude e.g. "FL240"
  samRings: SamThreatRing[];
  noFlyZones: NoFlyZone[];
  initialWaypoints: Waypoint[];
  initialTargets: ATRTarget[];
}

export interface TelemetryLogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  subsystem: Subsystem;
  message: string;
  details?: string;
  value?: string | number;
}

export interface StanagPacket {
  id: string;
  timestamp: string;
  messageId: string; // e.g. "DLI_#2000_VEHICLE_CONFIG" or "MISB_ST_0601_KLV"
  subsystem: string;
  lengthBytes: number;
  klvTags: Array<{
    tag: number;
    name: string;
    value: string;
    hex: string;
  }>;
  rawHex: string;
  crc16: string;
}
