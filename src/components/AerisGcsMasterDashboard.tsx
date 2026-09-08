import React, { useState, useEffect, useRef } from 'react';
import * as THREE from 'three';
import { 
  Activity, 
  AlertTriangle, 
  Cpu, 
  Play, 
  Pause, 
  RotateCcw, 
  FastForward, 
  Rewind, 
  Layers, 
  Sliders, 
  CheckCircle2, 
  Download, 
  Radio, 
  Clock, 
  ShieldCheck, 
  Compass, 
  Eye, 
  Sparkles, 
  ChevronRight, 
  Maximize2, 
  Zap, 
  Wrench, 
  BrainCircuit, 
  Workflow, 
  History,
  Volume2,
  VolumeX,
  RefreshCw,
  HelpCircle,
  TrendingUp,
  AlertCircle
} from 'lucide-react';
import { playTacticalClick, playWarningAlarm, setAudioMuted, isAudioMuted } from '../utils/tacticalAudio';

interface AerisGcsMasterDashboardProps {
  onSwitchToCockpit?: () => void;
}

interface TelemetryData {
  rpm: number;
  temperature: number;
  oilPressure: number;
  vibration: number;
  fuelFlow: number;
  engineLoad: number;
  altitude_ft?: number;
  ambient_temp_c?: number;
}

interface StreamMetrics {
  status?: string;
  source?: string;
  fps?: number;
  data_age_ms?: number;
  packet_loss_pct?: number;
  link_status?: string;
  bus_latency_ms?: number;
}

export const AerisGcsMasterDashboard: React.FC<AerisGcsMasterDashboardProps> = ({
  onSwitchToCockpit,
}) => {
  // Navigation Sub-Tabs within AERIS GCS
  const [activeSubTab, setActiveSubTab] = useState<
    'mission' | 'telemetry' | 'twin' | 'prognostics' | 'pipeline' | 'replay'
  >('mission');

  // Operating Mode: LIVE, SIMULATION, REPLAY
  const [operatingMode, setOperatingMode] = useState<'LIVE' | 'SIMULATION' | 'REPLAY'>('SIMULATION');
  const [isLiveConnected, setIsLiveConnected] = useState<boolean>(false);
  const [liveStatusMessage, setLiveStatusMessage] = useState<string>('SYNTHETIC RIG ACTIVE');
  const [isStreamPaused, setIsStreamPaused] = useState<boolean>(false);
  const [targetRateHz, setTargetRateHz] = useState<number>(10.0);

  // Audio State
  const [muted, setMuted] = useState<boolean>(isAudioMuted());

  // Real-time Telemetry State from Backend
  const [telemetry, setTelemetry] = useState<TelemetryData>({
    rpm: 5420,
    temperature: 173.8,
    oilPressure: 5.47,
    vibration: 1.42,
    fuelFlow: 24.6,
    engineLoad: 84.2,
    altitude_ft: 18500,
    ambient_temp_c: -14.5,
  });

  // History Buffers for Rolling Sparklines (max 30 points)
  const [rpmHistory, setRpmHistory] = useState<number[]>([5400, 5410, 5420, 5420, 5415, 5425, 5420]);
  const [chtHistory, setChtHistory] = useState<number[]>([165, 168, 170, 172, 173.5, 174, 173.8]);
  const [oilHistory, setOilHistory] = useState<number[]>([4.8, 5.0, 5.2, 5.4, 5.45, 5.48, 5.47]);
  const [vibHistory, setVibHistory] = useState<number[]>([1.35, 1.38, 1.40, 1.42, 1.41, 1.43, 1.42]);
  const [ffHistory, setFfHistory] = useState<number[]>([24.2, 24.4, 24.5, 24.6, 24.6, 24.7, 24.6]);
  const [loadHistory, setLoadHistory] = useState<number[]>([82.0, 83.5, 84.0, 84.2, 84.0, 84.5, 84.2]);

  // Executive Intelligence & AI Metrics
  const [healthIndex, setHealthIndex] = useState<number>(88.5);
  const [anomalyScore, setAnomalyScore] = useState<number>(0.58);
  const [anomalyThreshold, setAnomalyThreshold] = useState<number>(0.65);
  const [faultClass, setFaultClass] = useState<string>('SYNTHETIC TRANSDUCER DRIFT');
  const [faultConfidence, setFaultConfidence] = useState<number>(72.4);
  const [rulHours, setRulHours] = useState<number>(194.0);
  const [sensorTrustScore, setSensorTrustScore] = useState<number>(78.2);
  const [streamMetrics, setStreamMetrics] = useState<StreamMetrics>({
    status: 'ACTIVE',
    source: 'HIL RIG-04',
    fps: 42.0,
    data_age_ms: 1.2,
    packet_loss_pct: 0.0,
    link_status: 'CONNECTED',
    bus_latency_ms: 1.2,
  });

  // Physics Residuals
  const [residuals, setResiduals] = useState({
    rpm: '+0.04%',
    temperature: '+8.4 °C DISCREPANCY',
    oilPressure: '+0.65 bar WARNING',
    vibration: '+0.03 mm/s',
    fuelFlow: '-0.02 L/h',
    engineLoad: '+0.3%',
  });

  // AI Softmax Fault Distribution Probabilities
  const [faultProbs, setFaultProbs] = useState({
    sensorDrift: 72.4,
    nominal: 18.2,
    bearing: 5.1,
    lubrication: 3.1,
    thermal: 1.2,
  });

  // 3D Subsystem Isolation
  const [selectedSubsystem, setSelectedSubsystem] = useState<
    'HARNESS' | 'CRANKCASE' | 'CYLINDERS' | 'TURBO' | 'LUBE'
  >('HARNESS');
  const [view3DMode, setView3DMode] = useState<'STANDARD' | 'HEATMAP' | 'EXPLODED'>('STANDARD');

  // Timeline & Replay Scrubber State
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [progressPct, setProgressPct] = useState<number>(76.0);
  const [metTimeStr, setMetTimeStr] = useState<string>('04:18:22 Z');
  const [utcTimeStr, setUtcTimeStr] = useState<string>('14:22:08');

  // Three.js Canvas Container Reference
  const mountRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const engineGroupRef = useRef<THREE.Group | null>(null);
  const bearingAlertRef = useRef<THREE.Mesh | null>(null);
  const propShaftRef = useRef<THREE.Mesh | null>(null);
  const warningLightRef = useRef<THREE.PointLight | null>(null);
  const cylinderHeadMeshes = useRef<THREE.Mesh[]>([]);
  const turboScrollRef = useRef<THREE.Mesh | null>(null);

  // WebSocket Reference
  const wsRef = useRef<WebSocket | null>(null);

  // UTC Clock
  useEffect(() => {
    const clockTimer = setInterval(() => {
      const now = new Date();
      setUtcTimeStr(now.toISOString().substring(11, 19));
    }, 1000);
    return () => clearInterval(clockTimer);
  }, []);

  // ==========================================================================
  // REAL-TIME WEBSOCKET GATEWAY CONNECTION (AERIS-TWIN BACKEND)
  // ==========================================================================
  useEffect(() => {
    let isMounted = true;
    let reconnectTimeout: NodeJS.Timeout | null = null;

    const connectWebSocket = () => {
      const isDevPort = window.location.port === '3000' || window.location.port === '5173';
      const wsHost = isDevPort
        ? `${window.location.hostname || 'localhost'}:8000`
        : window.location.host;
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${wsHost}/ws/telemetry`;

      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
          console.log('[AERIS-TWIN WS] Connected to Telemetry Gateway:', wsUrl);
        };

        ws.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const msg = JSON.parse(event.data);

            if (msg.type === 'TELEMETRY_UPDATE') {
              const raw = msg.state || msg.data?.raw_telemetry || {};
              const inf = msg.inference || msg.data?.inference || {};
              const twin = msg.twin_state || msg.data?.twin_state || {};
              const db = msg.dashboard_view || msg.data?.dashboard_view || {};
              const res = msg.residuals || msg.data?.residuals || {};
              const trust = msg.sensor_trust || msg.data?.sensor_trust || {};

              setIsLiveConnected(true);
              if (msg.mode) setOperatingMode(msg.mode);

              // Update Live Telemetry
              const newRpm = raw.rpm || db.rpm || 5420;
              const newCht = raw.temperature || raw.cht_c || db.temperature || 173.8;
              const newOil = raw.oilPressure || raw.oil_pressure_bar || db.oilPressure || 5.47;
              const newVib = raw.vibration || raw.vibration_mms || db.vibration || 1.42;
              const newFf = raw.fuelFlow || raw.fuel_flow_lh || db.fuelFlow || 24.6;
              const newLoad = raw.throttle || raw.engine_load_pct || db.engineLoad || 84.2;

              setTelemetry({
                rpm: Math.round(newRpm),
                temperature: parseFloat(newCht.toFixed(1)),
                oilPressure: parseFloat(newOil.toFixed(2)),
                vibration: parseFloat(newVib.toFixed(2)),
                fuelFlow: parseFloat(newFf.toFixed(1)),
                engineLoad: parseFloat(newLoad.toFixed(1)),
                altitude_ft: raw.altitude_ft || 18500,
                ambient_temp_c: raw.ambient_temperature_c || -14.5,
              });

              // Rolling Sparkline History
              setRpmHistory((prev) => [...prev.slice(-20), Math.round(newRpm)]);
              setChtHistory((prev) => [...prev.slice(-20), parseFloat(newCht.toFixed(1))]);
              setOilHistory((prev) => [...prev.slice(-20), parseFloat(newOil.toFixed(2))]);
              setVibHistory((prev) => [...prev.slice(-20), parseFloat(newVib.toFixed(2))]);
              setFfHistory((prev) => [...prev.slice(-20), parseFloat(newFf.toFixed(1))]);
              setLoadHistory((prev) => [...prev.slice(-20), parseFloat(newLoad.toFixed(1))]);

              // Update AI & Prognostics Metrics from Backend
              if (twin.health_state?.value?.health_index !== undefined) {
                setHealthIndex(parseFloat(twin.health_state.value.health_index.toFixed(1)));
              } else if (db.health_score !== undefined) {
                setHealthIndex(parseFloat(db.health_score.toFixed(1)));
              }

              if (inf.anomalyScore !== undefined) {
                setAnomalyScore(parseFloat(inf.anomalyScore.toFixed(2)));
              }
              if (inf.anomalyThreshold !== undefined) {
                setAnomalyThreshold(parseFloat(inf.anomalyThreshold.toFixed(2)));
              }
              if (inf.possibleIssue) {
                setFaultClass(inf.possibleIssue.replace(/_/g, ' ').toUpperCase());
              }
              if (inf.confidencePct !== undefined) {
                setFaultConfidence(parseFloat(inf.confidencePct.toFixed(1)));
              }

              if (twin.rul_state?.value?.rul_estimate_hours !== undefined) {
                setRulHours(parseFloat(twin.rul_state.value.rul_estimate_hours.toFixed(1)));
              }

              if (trust.overall_trust_score !== undefined) {
                setSensorTrustScore(parseFloat((trust.overall_trust_score * 100).toFixed(1)));
              }

              // Update Stream Metrics
              if (msg.stream_metrics) {
                setStreamMetrics((prev) => ({ ...prev, ...msg.stream_metrics }));
              }

              // Update MET Flight Time
              if (raw.flight_time_seconds) {
                const totalSec = Math.floor(raw.flight_time_seconds);
                const hrs = Math.floor(totalSec / 3600).toString().padStart(2, '0');
                const mins = Math.floor((totalSec % 3600) / 60).toString().padStart(2, '0');
                const secs = (totalSec % 60).toString().padStart(2, '0');
                setMetTimeStr(`${hrs}:${mins}:${secs} Z`);
              }
            } else if (msg.type === 'LIVE_STREAM_STATUS') {
              setIsLiveConnected(msg.connected);
              setLiveStatusMessage(msg.message || msg.status || 'NO DATA');
              if (msg.status_details) {
                setStreamMetrics((prev) => ({ ...prev, ...msg.status_details }));
              }
            }
          } catch (err) {
            console.error('[AERIS-TWIN WS] JSON Parse Error:', err);
          }
        };

        ws.onclose = () => {
          if (!isMounted) return;
          console.warn('[AERIS-TWIN WS] Disconnected. Retrying in 2.5s...');
          reconnectTimeout = setTimeout(connectWebSocket, 2500);
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch (e) {
        console.error('[AERIS-TWIN WS] Connection Exception:', e);
        reconnectTimeout = setTimeout(connectWebSocket, 2500);
      }
    };

    connectWebSocket();

    return () => {
      isMounted = false;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // Operating Mode Switch Action
  const handleModeSwitch = async (newMode: 'LIVE' | 'SIMULATION' | 'REPLAY') => {
    playTacticalClick();
    setOperatingMode(newMode);

    const isDevPort = window.location.port === '3000' || window.location.port === '5173';
    const host = isDevPort
      ? `${window.location.hostname || 'localhost'}:8000`
      : window.location.host;
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';

    try {
      await fetch(`${protocol}//${host}/api/mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: newMode === 'SIMULATION' ? 'SIMULATION' : newMode }),
      });

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: 'SET_MODE', mode: newMode }));
      }
    } catch (e) {
      console.warn('[AERIS-TWIN API] Mode switch REST call error:', e);
    }
  };

  // Replay Control Action
  const handleReplayToggle = async () => {
    playTacticalClick();
    const nextState = !isPlaying;
    setIsPlaying(nextState);

    const isDevPort = window.location.port === '3000' || window.location.port === '5173';
    const host = isDevPort
      ? `${window.location.hostname || 'localhost'}:8000`
      : window.location.host;
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';

    try {
      await fetch(`${protocol}//${host}/replay/${nextState ? 'resume' : 'pause'}`, {
        method: 'POST',
      });
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: nextState ? 'REPLAY_START' : 'REPLAY_PAUSE' }));
      }
    } catch (e) {
      console.warn('[AERIS-TWIN API] Replay toggle error:', e);
    }
  };

  // Replay Speed Multiplier Action
  const handleSpeedCycle = async () => {
    playTacticalClick();
    const nextSpeed = playbackSpeed === 1.0 ? 2.0 : playbackSpeed === 2.0 ? 5.0 : 1.0;
    setPlaybackSpeed(nextSpeed);

    const isDevPort = window.location.port === '3000' || window.location.port === '5173';
    const host = isDevPort
      ? `${window.location.hostname || 'localhost'}:8000`
      : window.location.host;
    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';

    try {
      await fetch(`${protocol}//${host}/replay/speed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ speed: nextSpeed }),
      });
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: 'REPLAY_SPEED', speed: nextSpeed }));
      }
    } catch (e) {
      console.warn('[AERIS-TWIN API] Replay speed error:', e);
    }
  };

  // Blackbox HDF5 Export
  const handleExportBlackbox = () => {
    playTacticalClick();
    const blackboxPayload = {
      header: {
        system: 'AERIS-TWIN GCS v2.5.0-PROD',
        tail: 'UAV-MALE-TX07',
        airframe: 'DRDO TAPAS-BH-201 / HERMES MQ-9',
        powerplant: 'ROTAX 915-iS TURBOCHARGED',
        export_format: 'HDF5_DATA_FRAME_V2',
        timestamp: new Date().toISOString(),
      },
      telemetry: {
        rpm: telemetry.rpm,
        temperature_c: telemetry.temperature,
        oil_pressure_bar: telemetry.oilPressure,
        vibration_mms: telemetry.vibration,
        fuel_flow_lh: telemetry.fuelFlow,
        engine_load_pct: telemetry.engineLoad,
      },
      intelligence: {
        health_index: healthIndex,
        anomaly_score: anomalyScore,
        fault_class: faultClass,
        fault_confidence_pct: faultConfidence,
        rul_estimate_hours: rulHours,
        sensor_trust_score_pct: sensorTrustScore,
      },
      residuals,
      history_buffers: {
        rpm: rpmHistory,
        temperature: chtHistory,
        oil_pressure: oilHistory,
        vibration: vibHistory,
        fuel_flow: ffHistory,
        engine_load: loadHistory,
      },
    };

    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(blackboxPayload, null, 2));
    const a = document.createElement('a');
    a.href = dataStr;
    a.download = `AERIS_TWIN_BLACKBOX_${Date.now()}.hdf5.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  // Toggle Audio
  const handleToggleAudio = () => {
    const nextMuted = !muted;
    setMuted(nextMuted);
    setAudioMuted(nextMuted);
    if (!nextMuted) playTacticalClick();
  };

  // Three.js 3D Engine Digital Twin Lifecycle
  useEffect(() => {
    if (!mountRef.current) return;
    const container = mountRef.current;
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 480;

    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, 8, 22);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.shadowMap.enabled = true;
    container.replaceChildren(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x2a3b4c, 1.4);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xe2e8f0, 2.0);
    dirLight.position.set(15, 25, 20);
    scene.add(dirLight);

    const rimLight = new THREE.DirectionalLight(0x00e5ff, 1.2);
    rimLight.position.set(-15, -10, -15);
    scene.add(rimLight);

    const warningLight = new THREE.PointLight(0xf59e0b, 1.5, 30);
    warningLight.position.set(2, 4, 3);
    scene.add(warningLight);
    warningLightRef.current = warningLight;

    // Group container for engine assembly
    const engineGroup = new THREE.Group();
    scene.add(engineGroup);
    engineGroupRef.current = engineGroup;

    // Materials
    const matBlock = new THREE.MeshPhongMaterial({ color: 0x1e293b, specular: 0x64748b, shininess: 40 });
    const matCylinder = new THREE.MeshPhongMaterial({ color: 0x334155, specular: 0x94a3b8, shininess: 60 });
    const matCylinderHead = new THREE.MeshPhongMaterial({ color: 0x475569, specular: 0xcfd8dc, shininess: 70 });
    const matTurbo = new THREE.MeshPhongMaterial({ color: 0xd97706, specular: 0xfde68a, shininess: 80 });
    const matExhaust = new THREE.MeshPhongMaterial({ color: 0x64748b, specular: 0x94a3b8, shininess: 30 });
    const matShaft = new THREE.MeshPhongMaterial({ color: 0x06b6d4, specular: 0xa5f3fc, shininess: 90 });
    const matFins = new THREE.MeshPhongMaterial({ color: 0x243242, specular: 0x475569, shininess: 20 });
    const matBearing = new THREE.MeshPhongMaterial({ color: 0xef4444, specular: 0xfca5a5, shininess: 100 });

    // 1. Crankcase
    const crankcaseGeom = new THREE.BoxGeometry(6.5, 4.2, 10);
    const crankcase = new THREE.Mesh(crankcaseGeom, matBlock);
    engineGroup.add(crankcase);

    const oilPanGeom = new THREE.BoxGeometry(5.5, 1.2, 8.5);
    const oilPan = new THREE.Mesh(oilPanGeom, new THREE.MeshPhongMaterial({ color: 0x0f172a }));
    oilPan.position.set(0, -2.5, 0);
    engineGroup.add(oilPan);

    // 2. 4 Boxer Cylinders
    const cylPositions = [
      { x: -4.5, y: 0.6, z: -2.8, angle: -Math.PI / 2 },
      { x: 4.5, y: 0.6, z: -1.2, angle: Math.PI / 2 },
      { x: -4.5, y: 0.6, z: 1.2, angle: -Math.PI / 2 },
      { x: 4.5, y: 0.6, z: 2.8, angle: Math.PI / 2 }
    ];

    cylinderHeadMeshes.current = [];

    cylPositions.forEach((pos, idx) => {
      const cylBank = new THREE.Group();
      cylBank.position.set(pos.x, pos.y, pos.z);
      cylBank.rotation.z = pos.angle;

      const barrel = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 1.4, 3.2, 24), matCylinder);
      cylBank.add(barrel);

      for (let f = -1.2; f <= 1.2; f += 0.35) {
        const fin = new THREE.Mesh(new THREE.CylinderGeometry(1.7, 1.7, 0.08, 24), matFins);
        fin.position.y = f;
        cylBank.add(fin);
      }

      const head = new THREE.Mesh(new THREE.BoxGeometry(2.6, 1.0, 2.6), idx === 0 ? matTurbo : matCylinderHead);
      head.position.y = 2.0;
      cylBank.add(head);
      cylinderHeadMeshes.current.push(head);

      engineGroup.add(cylBank);
    });

    // 3. Central Propeller / Output Drive Shaft
    const propShaft = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.7, 13.5, 32), matShaft);
    propShaft.rotation.x = Math.PI / 2;
    engineGroup.add(propShaft);
    propShaftRef.current = propShaft;

    // Propeller Flange Mount
    const flange = new THREE.Mesh(new THREE.CylinderGeometry(1.8, 1.8, 0.6, 24), matCylinderHead);
    flange.rotation.x = Math.PI / 2;
    flange.position.set(0, 0, 6.8);
    engineGroup.add(flange);

    // Monitored Main Bearing #2
    const bearingAlert = new THREE.Mesh(new THREE.TorusGeometry(1.1, 0.22, 16, 32), matBearing);
    bearingAlert.position.set(0, 0, 3.8);
    engineGroup.add(bearingAlert);
    bearingAlertRef.current = bearingAlert;

    // 4. Turbocharger & Manifold Plumbing
    const turboScroll = new THREE.Mesh(new THREE.TorusGeometry(1.4, 0.55, 16, 32), matTurbo);
    turboScroll.rotation.y = Math.PI / 2;
    turboScroll.position.set(0, 3.2, -4.6);
    engineGroup.add(turboScroll);
    turboScrollRef.current = turboScroll;

    const turboCenter = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 0.9, 1.4, 24), matCylinderHead);
    turboCenter.rotation.z = Math.PI / 2;
    turboCenter.position.set(0, 3.2, -4.6);
    engineGroup.add(turboCenter);

    // Exhaust runners
    const runnerL = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 6.2, 16), matExhaust);
    runnerL.rotation.z = 0.4;
    runnerL.rotation.x = 0.2;
    runnerL.position.set(-2.8, 2.1, -1.8);
    engineGroup.add(runnerL);

    const runnerR = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 6.2, 16), matExhaust);
    runnerR.rotation.z = -0.4;
    runnerR.rotation.x = 0.2;
    runnerR.position.set(2.8, 2.1, -1.8);
    engineGroup.add(runnerR);

    // 5. Avionics Wireframe Grid Floor
    const gridHelper = new THREE.GridHelper(26, 26, 0x0ea5e9, 0x1e293b);
    gridHelper.position.y = -4.0;
    scene.add(gridHelper);

    // Mouse Interaction
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    let rotX = 0.35;
    let rotY = -0.65;

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;

      rotY += deltaX * 0.008;
      rotX += deltaY * 0.008;
      rotX = Math.max(-1.0, Math.min(1.2, rotX));

      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      camera.position.z = Math.max(12, Math.min(36, camera.position.z + e.deltaY * 0.02));
    };

    container.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mouseup', onMouseUp);
    window.addEventListener('mousemove', onMouseMove);
    container.addEventListener('wheel', onWheel, { passive: false });

    // Render loop
    let animationFrameId: number;
    let clock = 0;

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      clock += 0.03;

      if (!isDragging) {
        rotY += 0.0025;
      }

      engineGroup.rotation.x = rotX;
      engineGroup.rotation.y = rotY;

      if (propShaftRef.current) {
        propShaftRef.current.rotation.z += 0.08;
      }

      if (warningLightRef.current) {
        warningLightRef.current.intensity = 1.2 + Math.sin(clock * 3) * 0.5;
      }

      if (bearingAlertRef.current) {
        const alertScale = 1.0 + Math.sin(clock * 4) * 0.08;
        bearingAlertRef.current.scale.set(alertScale, alertScale, alertScale);
      }

      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      if (!container) return;
      const w = container.clientWidth || 800;
      const h = container.clientHeight || 480;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      container.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mouseup', onMouseUp);
      window.removeEventListener('mousemove', onMouseMove);
      container.removeEventListener('wheel', onWheel);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
    };
  }, []);

  return (
    <div className="w-full min-h-screen bg-[#0b0e13] text-[#e1e2ea] font-sans select-none flex flex-col">
      {/* ==========================================================================
          HEADER: AERIS-TWIN GCS MISSION AVIONICS COMMAND BAR
          ========================================================================== */}
      <header className="sticky top-0 w-full z-40 bg-[#0b0e13] border-b border-[#1d2025] shadow-lg">
        {/* Tier 1: Main Platform Ribbon */}
        <div className="h-14 w-full px-4 bg-[#191c21] flex items-center justify-between">
          {/* Brand & Tail Info */}
          <div className="flex items-center gap-3">
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="font-tech text-base tracking-wider text-[#4cd7f6] font-bold">AERIS-TWIN</span>
                <span className="font-mono text-[9px] px-1.5 py-0.5 bg-[#32353b] text-[#4cd7f6] font-semibold tracking-widest rounded">
                  PROP-MON-GCS
                </span>
              </div>
              <span className="font-mono text-[10px] text-[#bcc9cd] uppercase">
                AERO ENGINE RELIABILITY &amp; INTELLIGENCE
              </span>
            </div>

            <div className="flex items-center gap-2 px-3 py-1 bg-[#32353b] rounded text-xs">
              <div className="flex flex-col">
                <span className="font-mono text-[9px] text-[#bcc9cd]">TAIL</span>
                <span className="font-mono text-[11px] text-[#e1e2ea] font-semibold">UAV-MALE-TX07</span>
              </div>
              <span className="text-[#3d494c] font-mono">|</span>
              <div className="flex flex-col">
                <span className="font-mono text-[9px] text-[#bcc9cd]">CLASS</span>
                <span className="font-mono text-[11px] text-[#e1e2ea] font-semibold">HERMES / MQ-9</span>
              </div>
              <span className="text-[#3d494c] font-mono">|</span>
              <div className="flex flex-col">
                <span className="font-mono text-[9px] text-[#bcc9cd]">POWERPLANT</span>
                <span className="font-mono text-[11px] text-[#4cd7f6] font-semibold">ROT-915-iS TURBO</span>
              </div>
            </div>
          </div>

          {/* Mode Switcher & HIL Telemetry Feed Status */}
          <div className="hidden xl:flex items-center gap-3">
            {/* Mode Pills */}
            <div className="flex items-center p-1 bg-[#0b0e13] rounded gap-1">
              <button
                onClick={() => handleModeSwitch('LIVE')}
                className={`px-3 py-1 font-mono text-[10px] uppercase rounded transition-all ${
                  operatingMode === 'LIVE' ? 'bg-[#4cd7f6] text-[#003640] font-bold shadow' : 'text-[#bcc9cd] hover:text-white'
                }`}
              >
                LIVE
              </button>
              <button
                onClick={() => handleModeSwitch('SIMULATION')}
                className={`flex items-center gap-1.5 px-3 py-1 font-mono text-[10px] uppercase rounded font-bold transition-all ${
                  operatingMode === 'SIMULATION' ? 'bg-[#ee9800] text-[#5b3800] shadow' : 'text-[#bcc9cd] hover:text-white'
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-[#5b3800] animate-ping" />
                SIMULATION ACTIVE
              </button>
              <button
                onClick={() => handleModeSwitch('REPLAY')}
                className={`px-3 py-1 font-mono text-[10px] uppercase rounded transition-all ${
                  operatingMode === 'REPLAY' ? 'bg-[#4edea3] text-[#003824] font-bold shadow' : 'text-[#bcc9cd] hover:text-white'
                }`}
              >
                REPLAY
              </button>
            </div>

            {/* HIL Status Stats */}
            <div className="flex items-center gap-3 px-3 py-1 bg-[#32353b] rounded font-mono text-[10px]">
              <div className="flex flex-col">
                <span className="text-[#ffb95f] text-[9px]">SOURCE: {streamMetrics.source || 'HIL RIG-04'}</span>
                <span className="text-[#ffb95f] font-bold text-[11px]">{streamMetrics.fps ? `${streamMetrics.fps} Hz` : '42 Hz'}</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[#bcc9cd] text-[9px]">LATENCY</span>
                <span className="text-white font-semibold text-[11px]">{streamMetrics.bus_latency_ms || 1.2} ms (BUS)</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[#bcc9cd] text-[9px]">INJECTION</span>
                <span className="text-[#ffb95f] font-bold text-[11px]">ACTIVE</span>
              </div>
              <div className="flex flex-col">
                <span className="text-[#bcc9cd] text-[9px]">FADEC SYNC</span>
                <span className="text-[#4cd7f6] font-bold text-[11px]">SIM LOCKED</span>
              </div>
            </div>
          </div>

          {/* Right Clock & Annunciators */}
          <div className="flex items-center gap-3">
            <div className="hidden lg:flex items-center gap-3 px-3 py-1 bg-[#32353b] rounded font-mono text-[10px]">
              <div className="flex flex-col text-right">
                <span className="text-[#bcc9cd] text-[9px]">MET</span>
                <span className="text-white font-bold text-[11px]">{metTimeStr}</span>
              </div>
              <div className="flex flex-col text-right">
                <span className="text-[#bcc9cd] text-[9px]">UTC CLOCK</span>
                <span className="text-[#bcc9cd] font-medium text-[11px]">{utcTimeStr}</span>
              </div>
              <div className="flex flex-col text-right">
                <span className="text-[#bcc9cd] text-[9px]">TRUST SCORE</span>
                <span className="text-[#4edea3] font-bold text-[11px]">{sensorTrustScore.toFixed(1)}%</span>
              </div>
            </div>

            {/* Annunciators */}
            <div className="flex items-center gap-1 font-mono text-[9px] font-bold">
              <div className="px-2 py-1 bg-[#0b0e13] text-[#bcc9cd] rounded border border-[#3d494c]">M-WARN</div>
              <div className="px-2 py-1 bg-[#0b0e13] text-[#ffb95f] rounded border border-[#ee9800] animate-pulse">M-CAUT</div>
            </div>

            {/* Audio & Operator Badge */}
            <button
              onClick={handleToggleAudio}
              title={muted ? 'Unmute Audio' : 'Mute Tactical Audio'}
              className="p-1.5 bg-[#32353b] hover:bg-[#3d494c] rounded text-[#4cd7f6] transition-all"
            >
              {muted ? <VolumeX className="w-3.5 h-3.5 text-[#bcc9cd]" /> : <Volume2 className="w-3.5 h-3.5 text-[#4cd7f6]" />}
            </button>

            <div className="flex items-center gap-2 pl-2 border-l border-[#3d494c]">
              <div className="flex flex-col text-right font-mono">
                <span className="text-[#4cd7f6] font-bold text-[10px]">FLT-ENG. J. VANCE</span>
                <span className="text-[#bcc9cd] text-[8px]">TERMINAL GCS-3</span>
              </div>
              <div className="w-7 h-7 rounded-full bg-[#4cd7f6] text-[#003640] flex items-center justify-center font-bold text-xs">
                JV
              </div>
            </div>
          </div>
        </div>

        {/* Tier 2: Navigation Pills Matrix */}
        <div className="h-10 w-full px-4 bg-[#1d2025] flex items-center justify-between font-mono text-xs">
          <nav className="flex items-center gap-1 h-full py-1">
            {[
              { id: 'mission', label: '01 // MISSION DASHBOARD' },
              { id: 'telemetry', label: '02 // 6-CH TELEMETRY' },
              { id: 'twin', label: '03 // 3D DIGITAL TWIN' },
              { id: 'prognostics', label: '04 // AI & PROGNOSTICS' },
              { id: 'pipeline', label: '05 // SYSTEM ARCHITECTURE' },
              { id: 'replay', label: '06 // HISTORY & REPLAY' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  playTacticalClick();
                  setActiveSubTab(tab.id as typeof activeSubTab);
                }}
                className={`h-full px-3 flex items-center rounded transition-all tracking-wider ${
                  activeSubTab === tab.id
                    ? 'bg-[#4cd7f6] text-[#003640] font-bold shadow'
                    : 'text-[#bcc9cd] hover:bg-[#272a30] hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            {onSwitchToCockpit && (
              <button
                onClick={() => {
                  playTacticalClick();
                  onSwitchToCockpit();
                }}
                className="px-3 py-1 bg-[#272a30] hover:bg-[#32353b] border border-[#4cd7f6]/50 text-[#4cd7f6] rounded text-[10px] font-bold flex items-center gap-1.5 transition-all"
              >
                <Compass className="w-3.5 h-3.5" />
                <span>SWITCH TO TACTICAL COCKPIT C2</span>
              </button>
            )}

            <div className="hidden md:flex items-center gap-2 font-mono text-[10px]">
              <span className="text-[#bcc9cd] uppercase tracking-widest">BUS DUAL ACTIVE</span>
              <span className="w-2 h-2 rounded-full bg-[#4edea3] animate-pulse" />
            </div>
          </div>
        </div>
      </header>

      {/* ==========================================================================
          MAIN WORKSPACE BODY
          ========================================================================== */}
      <main className="w-full flex-1 p-3 flex flex-col gap-3 overflow-y-auto">
        {/* TOP STATUS BANNER & STREAM INTEGRITY GUARD */}
        <div className="w-full bg-[#191c21] px-4 py-2 rounded flex flex-wrap items-center justify-between gap-3 shadow border border-[#1d2025]">
          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className={`inline-block w-2.5 h-2.5 rounded-full animate-pulse ${
                operatingMode === 'LIVE' ? (isLiveConnected ? 'bg-[#4cd7f6]' : 'bg-[#ef4444]') : 'bg-[#ffb95f]'
              }`} />
              <span className={`font-bold tracking-widest uppercase ${
                operatingMode === 'LIVE' ? (isLiveConnected ? 'text-[#4cd7f6]' : 'text-[#ef4444]') : 'text-[#ffb95f]'
              }`}>
                {operatingMode === 'LIVE'
                  ? (isLiveConnected ? '▲ MODE: LIVE UAV TELEMETRY STREAM' : '▲ MODE: WAITING FOR LIVE TELEMETRY')
                  : '▲ MODE: SIMULATION RUNNING // BENCHMARK SCENARIO #04: SYNTHETIC SENSOR DRIFT'}
              </span>
            </div>
            <span className="text-[#3d494c]">|</span>
            <div className="flex items-center gap-2">
              <span className="text-[#bcc9cd] uppercase">SIM GUARD:</span>
              <span className="text-white font-semibold">
                RUNTIME: 00:14:22 | INJECTION: +12.4% CALIBRATION DRIFT ON CH-02 (CHT #3) &amp; CH-03 (OIL PRESS)
              </span>
            </div>
            <span className="text-[#3d494c]">|</span>
            <div className="flex items-center gap-2">
              <span className="text-[#bcc9cd] uppercase">DRIFT MAGNITUDE:</span>
              <span className="text-[#ffb95f] font-bold">+0.65 BAR / +8.4°C</span>
            </div>
          </div>

          <div className="flex items-center gap-3 font-mono text-xs">
            <div className="flex items-center gap-1.5 bg-[#32353b] px-2.5 py-1 rounded">
              <Sparkles className="w-3.5 h-3.5 text-[#ffb95f]" />
              <span className="text-[#ffb95f] font-bold text-[10px] tracking-wider">
                SYNTHETIC INJECTION TEST RIG ACTIVE
              </span>
            </div>
            <span className="text-[#bcc9cd] text-[10px]">VIRTUAL REGIME: HIGH-ALT CRUISE / 18,500 FT</span>
          </div>
        </div>

        {/* SECTION 1: MASTER ANNUNCIATOR & EXECUTIVE PROPULSION HEALTH */}
        <section className="w-full bg-[#1d2025] rounded p-4 shadow-md flex flex-col gap-3 border border-[#272a30]">
          <div className="flex items-center justify-between pb-1 border-b border-[#272a30]">
            <div className="flex items-center gap-2">
              <Wrench className="w-4 h-4 text-[#ffb95f]" />
              <h2 className="font-tech text-sm text-white tracking-wide uppercase font-bold">
                01 // EXECUTIVE HEALTH &amp; MASTER ANNUNCIATOR [{operatingMode}]
              </h2>
              <span className="font-mono text-[9px] bg-[#272a30] px-2 py-0.5 text-[#ffb95f] rounded font-bold">
                SENSOR TRUST: {sensorTrustScore.toFixed(1)}%
              </span>
            </div>
            <div className="flex items-center gap-2 font-mono text-[10px] text-[#bcc9cd]">
              <span>FADEC SENSOR CORRELATION CHECK:</span>
              <span className="text-[#ffb95f] font-bold">DISCREPANCY DETECTED</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-3">
            {/* Overall Health Index */}
            <div className="lg:col-span-3 bg-[#191c21] rounded p-4 flex flex-col justify-between relative overflow-hidden border border-[#272a30]">
              <div className="flex items-center justify-between font-mono text-xs">
                <span className="text-[#bcc9cd] text-[10px] uppercase tracking-wider">OVERALL HEALTH INDEX</span>
                <span className="text-[#ffb95f] bg-[#32353b] px-1.5 py-0.5 rounded text-[9px] font-bold">
                  SENSOR ANOMALY
                </span>
              </div>
              <div className="flex items-center justify-center py-2 gap-4">
                <div className="relative w-28 h-28 flex items-center justify-center">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                    <circle className="text-[#32353b] fill-none" cx="50" cy="50" r="42" stroke="currentColor" strokeWidth="8" />
                    <circle
                      className="text-[#ffb95f] fill-none"
                      cx="50"
                      cy="50"
                      r="42"
                      stroke="currentColor"
                      strokeDasharray="264"
                      strokeDashoffset={264 - (264 * healthIndex) / 100}
                      strokeLinecap="round"
                      strokeWidth="8"
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-center font-mono">
                    <span className="text-2xl font-bold text-white leading-none">{healthIndex.toFixed(1)}</span>
                    <span className="text-[9px] text-[#ffb95f] mt-1 font-bold">INDEX / 100</span>
                  </div>
                </div>
                <div className="flex flex-col gap-1.5 font-mono text-[10px]">
                  <div className="flex flex-col">
                    <span className="text-[#bcc9cd] text-[9px]">BASELINE REF</span>
                    <span className="text-white font-semibold">98.5% (T-0)</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[#bcc9cd] text-[9px]">SENSOR TRUST</span>
                    <span className="text-[#ffb95f] font-bold">{sensorTrustScore.toFixed(1)}% (DRIFT)</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[#bcc9cd] text-[9px]">SIM STATUS</span>
                    <span className="text-[#ffb95f] font-bold">INJECT ACTIVE</span>
                  </div>
                </div>
              </div>
              <div className="w-full bg-[#32353b] h-1.5 rounded-full overflow-hidden">
                <div className="bg-[#ffb95f] h-full" style={{ width: `${healthIndex}%` }} />
              </div>
            </div>

            {/* Anomaly & Risk Level */}
            <div className="lg:col-span-4 bg-[#191c21] rounded p-4 flex flex-col justify-between border border-[#272a30]">
              <div className="flex items-center justify-between font-mono text-xs">
                <span className="text-[#bcc9cd] text-[10px] uppercase">ANOMALY &amp; RISK LEVEL</span>
                <span className="text-[#ffb95f] bg-[#32353b] px-1.5 py-0.5 rounded text-[9px] font-bold">
                  DRIFT PROB: {faultConfidence.toFixed(1)}%
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 my-2 font-mono">
                <div className="flex flex-col bg-[#0b0e13] p-2.5 rounded border border-[#272a30]">
                  <span className="text-[#bcc9cd] text-[9px]">ANOMALY SCORE</span>
                  <div className="flex items-baseline gap-1 mt-1">
                    <span className="text-xl font-bold text-[#ffb95f]">{anomalyScore.toFixed(2)}</span>
                    <span className="text-[9px] text-[#bcc9cd]">/ THRESH {anomalyThreshold.toFixed(2)}</span>
                  </div>
                  <span className="text-[9px] text-[#ffb95f] mt-1 font-bold">APPROACHING THRESHOLD</span>
                </div>
                <div className="flex flex-col bg-[#0b0e13] p-2.5 rounded border border-[#272a30]">
                  <span className="text-[#bcc9cd] text-[9px]">DIAGNOSTIC FAULT ID</span>
                  <span className="text-[11px] text-[#ffb95f] font-bold mt-1 leading-tight">
                    {faultClass}
                  </span>
                  <span className="text-[8px] text-[#bcc9cd] mt-1">CHT &amp; OIL PRESS TRANSDUCERS</span>
                </div>
              </div>
              <div className="flex flex-col bg-[#0b0e13] px-3 py-1.5 rounded border border-[#272a30] font-mono text-[10px]">
                <div className="flex items-center justify-between">
                  <span className="text-[#bcc9cd]">SUBSYSTEM LOCATOR:</span>
                  <span className="text-[#ffb95f] font-bold">SENSOR HARNESS BANK-B // DUAL CH</span>
                </div>
              </div>
            </div>

            {/* RUL Projection */}
            <div className="lg:col-span-5 bg-[#191c21] rounded p-4 flex flex-col justify-between border border-[#272a30]">
              <div className="flex items-center justify-between font-mono text-xs">
                <span className="text-[#bcc9cd] text-[10px] uppercase">REMAINING USEFUL LIFE (RUL) PROJECTION</span>
                <span className="text-[#4edea3] bg-[#32353b] px-1.5 py-0.5 rounded text-[9px] font-bold">
                  PHYSICS ENGINE UNCOMPROMISED
                </span>
              </div>
              <div className="flex items-center justify-between my-2 bg-[#0b0e13] p-3 rounded border border-[#272a30] font-mono">
                <div className="flex flex-col">
                  <span className="text-[#bcc9cd] text-[9px]">ESTIMATED MECHANICAL RUL</span>
                  <div className="flex items-baseline gap-1 mt-1">
                    <span className="text-3xl font-bold text-[#4edea3]">{rulHours.toFixed(1)}</span>
                    <span className="text-xs text-[#bcc9cd]">HRS</span>
                    <span className="text-[10px] text-[#4cd7f6] ml-2 font-bold">[HARDWARE NOMINAL]</span>
                  </div>
                </div>
                <div className="text-right flex flex-col text-[10px]">
                  <span className="text-[#bcc9cd] text-[9px]">SENSOR FAULT CONFIDENCE</span>
                  <span className="text-[#ffb95f] font-bold text-xs">{faultConfidence.toFixed(1)}% DECALIBRATION</span>
                  <span className="text-[8px] text-[#bcc9cd]">SYNTHETIC DRIFT INJECTION</span>
                </div>
              </div>
              <div className="bg-[#32353b] px-3 py-1.5 rounded flex items-center justify-between font-mono text-[10px]">
                <div className="flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-[#ffb95f]" />
                  <span className="text-white">ACTION: AUTO-CALIBRATION ROUTINE RECOMMENDED</span>
                </div>
                <span className="text-[#ffb95f] font-bold uppercase text-[9px]">SIM INJECT</span>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 2: 6-CHANNEL TELEMETRY HUD TILES */}
        <section className="w-full bg-[#1d2025] rounded p-4 shadow-md flex flex-col gap-3 border border-[#272a30]">
          <div className="flex items-center justify-between pb-1 border-b border-[#272a30]">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-[#ffb95f]" />
              <h2 className="font-tech text-sm text-white tracking-wide uppercase font-bold">
                02 // 6-CHANNEL FADEC TELEMETRY BUS [SYNTHETIC INJECTION ACTIVE]
              </h2>
            </div>
            <div className="flex items-center gap-3 font-mono text-[10px]">
              <div className="flex items-center gap-1 text-[#bcc9cd]">
                <span className="w-2 h-2 rounded bg-[#4edea3] inline-block" /> 4 CH NOMINAL
                <span className="w-2 h-2 rounded bg-[#ffb95f] inline-block ml-2" /> 2 CH SENSOR DRIFT
              </div>
              <span className="bg-[#32353b] text-[#ffb95f] px-2 py-0.5 rounded font-bold">SIM TEST BUS 42Hz</span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3">
            {/* CH-01 RPM */}
            <div className="bg-[#191c21] rounded p-3 flex flex-col justify-between border border-[#272a30] font-mono">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-[#bcc9cd]">CH-01 // RPM</span>
                <span className="text-[#4edea3] font-bold">NOMINAL</span>
              </div>
              <div className="my-2">
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold text-white">{telemetry.rpm.toLocaleString()}</span>
                  <span className="text-[10px] text-[#bcc9cd]">RPM</span>
                </div>
                <div className="flex items-center justify-between text-[9px] text-[#bcc9cd] mt-0.5">
                  <span>REDLINE: 5,800</span>
                  <span className="text-[#4edea3]">Δ +20 (TGT)</span>
                </div>
              </div>
              <div className="h-8 w-full">
                <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 30">
                  <polyline
                    className="text-[#4cd7f6]"
                    fill="none"
                    points={rpmHistory.map((val, idx) => `${(idx / (rpmHistory.length - 1 || 1)) * 100},${30 - ((val - 5000) / 1000) * 30}`).join(' ')}
                    stroke="currentColor"
                    strokeWidth="1.5"
                  />
                </svg>
              </div>
              <div className="mt-1 bg-[#0b0e13] px-2 py-1 rounded text-[9px] flex justify-between">
                <span className="text-[#bcc9cd]">PHYSICS RESIDUAL:</span>
                <span className="text-[#4cd7f6] font-semibold">{residuals.rpm}</span>
              </div>
            </div>

            {/* CH-02 CHT AVG */}
            <div className="bg-[#191c21] rounded p-3 flex flex-col justify-between border border-[#ee9800]/50 font-mono shadow-[0_0_10px_rgba(238,152,0,0.15)]">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-[#bcc9cd]">CH-02 // CHT AVG</span>
                <span className="text-[#ffb95f] font-bold">DRIFT INJECTED</span>
              </div>
              <div className="my-2">
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold text-[#ffb95f]">{telemetry.temperature.toFixed(1)}</span>
                  <span className="text-[10px] text-[#bcc9cd]">°C</span>
                </div>
                <div className="flex items-center justify-between text-[9px] text-[#bcc9cd] mt-0.5">
                  <span>RAW MODEL: 165.4</span>
                  <span className="text-[#ffb95f]">DRIFT: +8.4°C</span>
                </div>
              </div>
              <div className="h-8 w-full">
                <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 30">
                  <polyline
                    className="text-[#ffb95f]"
                    fill="none"
                    points={chtHistory.map((val, idx) => `${(idx / (chtHistory.length - 1 || 1)) * 100},${30 - ((val - 150) / 40) * 30}`).join(' ')}
                    stroke="currentColor"
                    strokeWidth="1.5"
                  />
                </svg>
              </div>
              <div className="mt-1 bg-[#0b0e13] px-2 py-1 rounded text-[9px] flex justify-between">
                <span className="text-[#bcc9cd]">PHYSICS RESIDUAL:</span>
                <span className="text-[#ffb95f] font-bold">{residuals.temperature}</span>
              </div>
            </div>

            {/* CH-03 OIL PRESS */}
            <div className="bg-[#191c21] rounded p-3 flex flex-col justify-between border border-[#ee9800]/50 font-mono shadow-[0_0_10px_rgba(238,152,0,0.15)]">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-[#bcc9cd]">CH-03 // OIL PRESS</span>
                <span className="text-[#ffb95f] font-bold">TRANSDUCER BIAS</span>
              </div>
              <div className="my-2">
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold text-[#ffb95f]">{telemetry.oilPressure.toFixed(2)}</span>
                  <span className="text-[10px] text-[#bcc9cd]">BAR</span>
                </div>
                <div className="flex items-center justify-between text-[9px] text-[#bcc9cd] mt-0.5">
                  <span>PHYS TRUE: 4.82</span>
                  <span className="text-[#ffb95f]">+0.65 BAR BIAS</span>
                </div>
              </div>
              <div className="h-8 w-full">
                <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 30">
                  <polyline
                    className="text-[#ffb95f]"
                    fill="none"
                    points={oilHistory.map((val, idx) => `${(idx / (oilHistory.length - 1 || 1)) * 100},${30 - ((val - 4.0) / 3.0) * 30}`).join(' ')}
                    stroke="currentColor"
                    strokeWidth="1.5"
                  />
                </svg>
              </div>
              <div className="mt-1 bg-[#0b0e13] px-2 py-1 rounded text-[9px] flex justify-between">
                <span className="text-[#bcc9cd]">SENSOR VARIANCE:</span>
                <span className="text-[#ffb95f] font-bold">{residuals.oilPressure}</span>
              </div>
            </div>

            {/* CH-04 VIB RMS */}
            <div className="bg-[#191c21] rounded p-3 flex flex-col justify-between border border-[#272a30] font-mono">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-[#bcc9cd]">CH-04 // VIB RMS</span>
                <span className="text-[#4edea3] font-bold">NOMINAL</span>
              </div>
              <div className="my-2">
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold text-white">{telemetry.vibration.toFixed(2)}</span>
                  <span className="text-[10px] text-[#bcc9cd]">MM/S</span>
                </div>
                <div className="flex items-center justify-between text-[9px] text-[#bcc9cd] mt-0.5">
                  <span>PEAK @ 142 Hz</span>
                  <span className="text-[#4edea3]">MAX: 3.20</span>
                </div>
              </div>
              <div className="h-8 w-full">
                <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 30">
                  <polyline
                    className="text-[#4edea3]"
                    fill="none"
                    points={vibHistory.map((val, idx) => `${(idx / (vibHistory.length - 1 || 1)) * 100},${30 - (val / 4.0) * 30}`).join(' ')}
                    stroke="currentColor"
                    strokeWidth="1.5"
                  />
                </svg>
              </div>
              <div className="mt-1 bg-[#0b0e13] px-2 py-1 rounded text-[9px] flex justify-between">
                <span className="text-[#bcc9cd]">HARMONIC RESIDUAL:</span>
                <span className="text-[#4cd7f6] font-semibold">{residuals.vibration}</span>
              </div>
            </div>

            {/* CH-05 FUEL FLOW */}
            <div className="bg-[#191c21] rounded p-3 flex flex-col justify-between border border-[#272a30] font-mono">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-[#bcc9cd]">CH-05 // FUEL FLOW</span>
                <span className="text-[#4edea3] font-bold">NOMINAL</span>
              </div>
              <div className="my-2">
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold text-white">{telemetry.fuelFlow.toFixed(1)}</span>
                  <span className="text-[10px] text-[#bcc9cd]">L/HR</span>
                </div>
                <div className="flex items-center justify-between text-[9px] text-[#bcc9cd] mt-0.5">
                  <span>MAP: 36.2 inHg</span>
                  <span className="text-[#4edea3]">STABLE</span>
                </div>
              </div>
              <div className="h-8 w-full">
                <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 30">
                  <polyline
                    className="text-[#4edea3]"
                    fill="none"
                    points={ffHistory.map((val, idx) => `${(idx / (ffHistory.length - 1 || 1)) * 100},${30 - ((val - 15) / 20) * 30}`).join(' ')}
                    stroke="currentColor"
                    strokeWidth="1.5"
                  />
                </svg>
              </div>
              <div className="mt-1 bg-[#0b0e13] px-2 py-1 rounded text-[9px] flex justify-between">
                <span className="text-[#bcc9cd]">BSFC RESIDUAL:</span>
                <span className="text-[#4edea3] font-semibold">{residuals.fuelFlow}</span>
              </div>
            </div>

            {/* CH-06 ENG LOAD */}
            <div className="bg-[#191c21] rounded p-3 flex flex-col justify-between border border-[#272a30] font-mono">
              <div className="flex items-center justify-between text-[10px]">
                <span className="text-[#bcc9cd]">CH-06 // ENG LOAD</span>
                <span className="text-[#4edea3] font-bold">NOMINAL</span>
              </div>
              <div className="my-2">
                <div className="flex items-baseline justify-between">
                  <span className="text-2xl font-bold text-white">{telemetry.engineLoad.toFixed(1)}</span>
                  <span className="text-[10px] text-[#bcc9cd]">%</span>
                </div>
                <div className="flex items-center justify-between text-[9px] text-[#bcc9cd] mt-0.5">
                  <span>THROT: 82.0%</span>
                  <span className="text-[#4edea3]">138 Nm</span>
                </div>
              </div>
              <div className="h-8 w-full">
                <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 30">
                  <polyline
                    className="text-[#4edea3]"
                    fill="none"
                    points={loadHistory.map((val, idx) => `${(idx / (loadHistory.length - 1 || 1)) * 100},${30 - (val / 100) * 30}`).join(' ')}
                    stroke="currentColor"
                    strokeWidth="1.5"
                  />
                </svg>
              </div>
              <div className="mt-1 bg-[#0b0e13] px-2 py-1 rounded text-[9px] flex justify-between">
                <span className="text-[#bcc9cd]">LOAD RESIDUAL:</span>
                <span className="text-[#4edea3] font-semibold">{residuals.engineLoad}</span>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 3: 3D DIGITAL TWIN & SPATIAL DIAGNOSTICS */}
        <section className="w-full bg-[#1d2025] rounded p-4 shadow-md flex flex-col gap-3 border border-[#272a30]">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-1 border-b border-[#272a30]">
            <div className="flex items-center gap-2">
              <Eye className="w-4 h-4 text-[#4cd7f6]" />
              <h2 className="font-tech text-sm text-white tracking-wide uppercase font-bold">
                03 // 3D PROPULSION DIGITAL TWIN
              </h2>
              <span className="font-mono text-[9px] bg-[#272a30] px-2 py-0.5 text-[#4cd7f6] rounded font-bold">
                SPATIAL SYNCED
              </span>
            </div>
            <span className="font-mono text-[10px] text-[#bcc9cd]">
              MODEL: ROTAX-915-iS TURBO DIGITAL ASSEMBLY
            </span>
          </div>

          {/* Subsystem Selection Filter Buttons */}
          <div className="flex flex-wrap items-center gap-1.5 bg-[#191c21] p-1.5 rounded font-mono text-xs border border-[#272a30]">
            <span className="text-[#bcc9cd] px-2 text-[10px] uppercase font-bold">ISOLATE SUBSYSTEM:</span>
            <button
              onClick={() => {
                playTacticalClick();
                setSelectedSubsystem('HARNESS');
              }}
              className={`px-3 py-1 rounded text-[10px] transition-all font-bold ${
                selectedSubsystem === 'HARNESS'
                  ? 'bg-[#ee9800] text-[#5b3800] shadow'
                  : 'bg-[#32353b] hover:bg-[#36393f] text-[#e1e2ea]'
              }`}
            >
              SENSOR HARNESS &amp; TRANSDUCER BUS [DRIFT DETECTED]
            </button>
            <button
              onClick={() => {
                playTacticalClick();
                setSelectedSubsystem('CRANKCASE');
              }}
              className={`px-3 py-1 rounded text-[10px] transition-all ${
                selectedSubsystem === 'CRANKCASE'
                  ? 'bg-[#4cd7f6] text-[#003640] font-bold'
                  : 'bg-[#32353b] hover:bg-[#36393f] text-[#e1e2ea]'
              }`}
            >
              CRANKCASE [OK]
            </button>
            <button
              onClick={() => {
                playTacticalClick();
                setSelectedSubsystem('CYLINDERS');
              }}
              className={`px-3 py-1 rounded text-[10px] transition-all ${
                selectedSubsystem === 'CYLINDERS'
                  ? 'bg-[#4cd7f6] text-[#003640] font-bold'
                  : 'bg-[#32353b] hover:bg-[#36393f] text-[#e1e2ea]'
              }`}
            >
              CYLINDERS 1-4 [OK]
            </button>
            <button
              onClick={() => {
                playTacticalClick();
                setSelectedSubsystem('TURBO');
              }}
              className={`px-3 py-1 rounded text-[10px] transition-all ${
                selectedSubsystem === 'TURBO'
                  ? 'bg-[#4cd7f6] text-[#003640] font-bold'
                  : 'bg-[#32353b] hover:bg-[#36393f] text-[#e1e2ea]'
              }`}
            >
              TURBOCHARGER [OK]
            </button>
            <button
              onClick={() => {
                playTacticalClick();
                setSelectedSubsystem('LUBE');
              }}
              className={`px-3 py-1 rounded text-[10px] transition-all ${
                selectedSubsystem === 'LUBE'
                  ? 'bg-[#4cd7f6] text-[#003640] font-bold'
                  : 'bg-[#32353b] hover:bg-[#36393f] text-[#e1e2ea]'
              }`}
            >
              LUBRICATION CIRCUIT [OK]
            </button>
          </div>

          {/* 3D Viewport with Integrated HUD Overlays */}
          <div className="relative w-full h-[480px] bg-[#0b0e13] rounded overflow-hidden border border-[#272a30]">
            {/* Embedded Three.js Canvas Container */}
            <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

            {/* HUD Corner Reticles */}
            <div className="absolute top-3 left-3 flex flex-col gap-1 pointer-events-none font-mono">
              <span className="text-[10px] text-[#4cd7f6] font-bold">AERIS SPATIAL RESOLVER // AXIS XYZ</span>
              <span className="text-[9px] text-[#bcc9cd]">MESH NODES: 148,290 | THERMAL FEA: ACTIVE</span>
            </div>

            {/* HUD View Controls Top Right */}
            <div className="absolute top-3 right-3 flex items-center gap-1.5 font-mono">
              <button
                onClick={() => {
                  playTacticalClick();
                  setView3DMode(view3DMode === 'HEATMAP' ? 'STANDARD' : 'HEATMAP');
                }}
                className={`px-2.5 py-1 rounded text-[9px] backdrop-blur font-bold transition-all ${
                  view3DMode === 'HEATMAP'
                    ? 'bg-[#ee9800] text-[#5b3800]'
                    : 'bg-[#1d2025]/80 hover:bg-[#1d2025] text-white'
                }`}
              >
                HEATMAP (THERMAL/STRESS)
              </button>
              <button
                onClick={() => {
                  playTacticalClick();
                  setView3DMode(view3DMode === 'EXPLODED' ? 'STANDARD' : 'EXPLODED');
                }}
                className={`px-2.5 py-1 rounded text-[9px] backdrop-blur font-bold transition-all ${
                  view3DMode === 'EXPLODED'
                    ? 'bg-[#4cd7f6] text-[#003640]'
                    : 'bg-[#1d2025]/80 hover:bg-[#1d2025] text-white'
                }`}
              >
                EXPLODED VIEW
              </button>
            </div>

            {/* Spatial Callout Pin 1: Bearing #2 */}
            <div className="absolute top-1/3 left-1/4 bg-[#272a30]/90 border border-[#ee9800]/50 p-2 rounded shadow-xl backdrop-blur flex flex-col gap-1 font-mono text-[10px] pointer-events-auto">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#ee9800] animate-ping" />
                <span className="text-[#ee9800] font-bold">TRANSDUCER CLUSTER DRIFT DELTA</span>
              </div>
              <span className="text-white">OIL PRESS TRANSDUCER: +0.65 bar BIAS</span>
              <span className="text-[#ee9800] text-[9px]">CHT #3 TRANSDUCER: +8.4 °C SYNTHETIC DRIFT</span>
            </div>

            {/* Spatial Callout Pin 2: Cyl #3 Exhaust */}
            <div className="absolute top-1/2 right-1/3 bg-[#272a30]/90 border border-[#4cd7f6]/40 p-2 rounded shadow-xl backdrop-blur flex flex-col gap-1 font-mono text-[10px] pointer-events-auto">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#4cd7f6]" />
                <span className="text-[#4cd7f6] font-bold">CYLINDER #3 HEAD</span>
              </div>
              <span className="text-white">CHT: {telemetry.temperature.toFixed(1)} °C | EGT: 780 °C</span>
              <span className="text-[#bcc9cd] text-[9px]">THERMAL RESIDUAL: +5.7 °C</span>
            </div>

            {/* Disclaimer HUD Footer */}
            <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between pointer-events-none font-mono text-[9px]">
              <div className="bg-[#0b0e13]/80 px-3 py-1 rounded backdrop-blur border border-[#1d2025]">
                <span className="text-[#bcc9cd]">
                  TELEMETRY LINK: PHYSICS-INFORMED RESIDUAL STREAM (REF FREQ: {streamMetrics.fps ? `${streamMetrics.fps} Hz` : '42.0 Hz'})
                </span>
              </div>
              <div className="bg-[#0b0e13]/80 px-3 py-1 rounded backdrop-blur border border-[#1d2025]">
                <span className="text-[#869397]">
                  VISUALIZING DIGITAL TWIN STATE // DOES NOT AUTONOMOUSLY EXECUTE SCRAM
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 4: AI & ML PROGNOSTICS LAB */}
        <section className="w-full bg-[#1d2025] rounded p-4 shadow-md flex flex-col gap-3 border border-[#272a30]">
          <div className="flex items-center justify-between pb-1 border-b border-[#272a30]">
            <div className="flex items-center gap-2">
              <BrainCircuit className="w-4 h-4 text-[#ffb95f]" />
              <h2 className="font-tech text-sm text-white tracking-wide uppercase font-bold">
                04 // AI &amp; MACHINE LEARNING PROGNOSTICS LAB [{operatingMode}]
              </h2>
            </div>
            <span className="font-mono text-[9px] bg-[#32353b] px-2 py-0.5 text-[#ffb95f] rounded font-bold">
              SYNTHETIC DRIFT BENCHMARK ACTIVE
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
            {/* UMAP Latent Feature Projection */}
            <div className="lg:col-span-4 bg-[#191c21] rounded p-4 flex flex-col justify-between border border-[#272a30] font-mono">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[#bcc9cd] text-[10px] uppercase">LATENT FEATURE PROJECTION (UMAP)</span>
                <span className="text-[#ffb95f] bg-[#32353b] px-1.5 py-0.5 rounded text-[9px] font-bold">
                  SENSOR DISTORTION AXIS
                </span>
              </div>
              <div className="w-full h-44 my-2 bg-[#0b0e13] rounded relative flex items-center justify-center p-2 border border-[#272a30]">
                <svg className="w-full h-full" viewBox="0 0 200 120">
                  <line stroke="#1d2025" strokeDasharray="2" x1="0" x2="200" y1="60" y2="60" />
                  <line stroke="#1d2025" strokeDasharray="2" x1="100" x2="100" y1="0" y2="120" />
                  {/* Nominal Cluster */}
                  <ellipse cx="70" cy="60" fill="#4edea3" fillOpacity="0.08" rx="35" ry="25" stroke="#4edea3" strokeDasharray="2" strokeWidth="0.5" />
                  <circle cx="60" cy="55" fill="#4edea3" r="2" />
                  <circle cx="68" cy="50" fill="#4edea3" r="2" />
                  <circle cx="75" cy="58" fill="#4edea3" r="2" />
                  <circle cx="72" cy="65" fill="#4edea3" r="2" />
                  <circle cx="58" cy="68" fill="#4edea3" r="2" />
                  <circle cx="82" cy="52" fill="#4edea3" r="2" />
                  <circle cx="65" cy="62" fill="#4edea3" r="2.5" />
                  {/* Decalibration Cluster */}
                  <ellipse cx="150" cy="75" fill="#ee9800" fillOpacity="0.15" rx="28" ry="20" stroke="#ee9800" strokeDasharray="2" strokeWidth="0.5" />
                  <circle cx="142" cy="78" fill="#ee9800" r="2" />
                  <circle cx="152" cy="70" fill="#ee9800" r="2.5" />
                  <circle cx="158" cy="76" fill="#ee9800" r="2" />
                  <circle cx="145" cy="72" fill="#ee9800" r="2" />
                  <circle className="animate-pulse" cx="155" cy="74" fill="#ee9800" r="4" stroke="#ffffff" strokeWidth="1.5" />
                  <line stroke="#ee9800" strokeDasharray="3" strokeWidth="1" x1="70" x2="155" y1="60" y2="74" />
                </svg>
                <span className="absolute bottom-2 left-2 text-[8px] text-[#4edea3] font-bold">
                  NOMINAL FLIGHT ENVELOPE
                </span>
                <span className="absolute top-2 right-2 text-[8px] text-[#ffb95f] font-bold">
                  SENSOR DECALIBRATION DRIFT VECTOR
                </span>
              </div>
              <div className="flex items-center justify-between text-[10px] bg-[#0b0e13] px-3 py-1.5 rounded border border-[#272a30]">
                <span className="text-[#bcc9cd]">DISTANCE FROM CENTROID:</span>
                <span className="text-[#ffb95f] font-bold">3.18 σ (SENSOR HYPERPLANE)</span>
              </div>
            </div>

            {/* Multi-Head Fault Matrix */}
            <div className="lg:col-span-4 bg-[#191c21] rounded p-4 flex flex-col justify-between border border-[#272a30] font-mono">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[#bcc9cd] text-[10px] uppercase">MULTI-HEAD FAULT MATRIX</span>
                <span className="text-[#ffb95f] bg-[#32353b] px-1.5 py-0.5 rounded text-[9px] font-bold">
                  SOFTMAX OUTPUT
                </span>
              </div>
              <div className="flex flex-col gap-2 my-2 text-xs">
                <div className="flex flex-col gap-1 bg-[#32353b]/40 p-2 rounded border border-[#ee9800]/40">
                  <div className="flex justify-between text-[10px]">
                    <span className="text-[#ffb95f] font-bold">SENSOR DRIFT (SYNTHETIC)</span>
                    <span className="text-[#ffb95f] font-bold">{faultProbs.sensorDrift.toFixed(1)}% [ACTIVE TRACK]</span>
                  </div>
                  <div className="w-full bg-[#0b0e13] h-2 rounded overflow-hidden">
                    <div className="bg-[#ee9800] h-full" style={{ width: `${faultProbs.sensorDrift}%` }} />
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <div className="flex justify-between text-[10px]">
                    <span className="text-[#e1e2ea]">NOMINAL OPERATION</span>
                    <span className="text-[#4edea3] font-bold">{faultProbs.nominal.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-[#0b0e13] h-1.5 rounded overflow-hidden">
                    <div className="bg-[#4edea3] h-full" style={{ width: `${faultProbs.nominal}%` }} />
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <div className="flex justify-between text-[10px]">
                    <span className="text-[#bcc9cd]">BEARING DEGRADATION</span>
                    <span className="text-[#e1e2ea]">{faultProbs.bearing.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-[#0b0e13] h-1.5 rounded overflow-hidden">
                    <div className="bg-[#4cd7f6] h-full" style={{ width: `${faultProbs.bearing}%` }} />
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <div className="flex justify-between text-[10px]">
                    <span className="text-[#bcc9cd]">LUBRICATION DEGRADATION</span>
                    <span className="text-[#e1e2ea]">{faultProbs.lubrication.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-[#0b0e13] h-1.5 rounded overflow-hidden">
                    <div className="bg-[#4cd7f6] h-full" style={{ width: `${faultProbs.lubrication}%` }} />
                  </div>
                </div>

                <div className="flex flex-col gap-1">
                  <div className="flex justify-between text-[10px]">
                    <span className="text-[#bcc9cd]">THERMAL OVERHEAT</span>
                    <span className="text-[#e1e2ea]">{faultProbs.thermal.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-[#0b0e13] h-1.5 rounded overflow-hidden">
                    <div className="bg-[#4cd7f6] h-full" style={{ width: `${faultProbs.thermal}%` }} />
                  </div>
                </div>
              </div>
              <div className="text-[10px] text-[#bcc9cd]">Simulation posterior loss converged at step #1480.</div>
            </div>

            {/* AI Evidence & Attribution */}
            <div className="lg:col-span-4 bg-[#191c21] rounded p-4 flex flex-col justify-between border border-[#272a30] font-mono">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[#bcc9cd] text-[10px] uppercase">AI EVIDENCE &amp; ATTRIBUTION</span>
                <span className="text-[#ffb95f] bg-[#32353b] px-1.5 py-0.5 rounded text-[9px] font-bold">
                  SHAPLEY EXPLAINABILITY
                </span>
              </div>
              <div className="bg-[#0b0e13] p-3 rounded my-2 flex flex-col gap-2 border border-[#272a30]">
                <div className="flex items-center gap-1.5 text-[#ffb95f] font-bold text-[11px]">
                  <Zap className="w-3.5 h-3.5" />
                  <span>AI ATTRIBUTION REPORT:</span>
                </div>
                <p className="text-[11px] text-[#e1e2ea] leading-relaxed">
                  "Injected synthetic bias (+0.65 bar on Oil Press, +8.4°C on CHT #3) decoupled from thermodynamic balance equations. Physics-informed residual flagged sensor decalibration rather than mechanical failure."
                </p>
              </div>
              <div className="flex flex-col gap-1 bg-[#32353b] p-2 rounded text-[10px]">
                <div className="flex justify-between">
                  <span className="text-[#bcc9cd]">PRIMARY DRIFT DRIVER:</span>
                  <span className="text-[#ffb95f] font-bold">OIL_PRESS_TRANSDUCER (+61.5%)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#bcc9cd]">SECONDARY INFLUENCE:</span>
                  <span className="text-[#ffb95f] font-bold">CHT_CYL3_RESIDUAL (+28.4%)</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* SECTION 5: CORE TECHNOLOGY PIPELINE ARCHITECTURE */}
        <section className="w-full bg-[#1d2025] rounded p-4 shadow-md flex flex-col gap-3 border border-[#272a30]">
          <div className="flex items-center justify-between pb-1 border-b border-[#272a30]">
            <div className="flex items-center gap-2">
              <Workflow className="w-4 h-4 text-[#4cd7f6]" />
              <h2 className="font-tech text-sm text-white tracking-wide uppercase font-bold">
                05 // AERIS END-TO-END DATA &amp; INFERENCE PIPELINE
              </h2>
            </div>
            <span className="font-mono text-[9px] text-[#4edea3] bg-[#32353b] px-2 py-0.5 rounded font-bold">
              LATENCY BUDGET: 24ms &lt; 50ms REQ
            </span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 font-mono">
            {[
              { idx: '01', title: 'REAL TELEMETRY', sub: `${streamMetrics.fps || 42} Hz CAN downlink`, badge: 'RATE: 1.2 MB/s', color: '#4cd7f6' },
              { idx: '02', title: 'DATA VALIDATION', sub: 'Packet drop & CRC check', badge: 'CRC: 100% PASS', color: '#4cd7f6' },
              { idx: '03', title: 'SENSOR TRUST', sub: 'Dual cross-correlation', badge: `${sensorTrustScore.toFixed(1)}% TRUST`, color: sensorTrustScore < 85 ? '#ffb95f' : '#4edea3' },
              { idx: '04', title: 'PHYSICS TWIN', sub: 'Thermodynamic solver', badge: 'SOLVER: OK', color: '#4cd7f6' },
              { idx: '05', title: 'RESIDUAL DELTA', sub: 'Model vs synthetic bias', badge: 'RMS: 0.184 BIAS', color: '#ffb95f' },
              { idx: '06', title: 'AI ENSEMBLE', sub: 'Temporal CNN+Transformer', badge: 'INFER: 8.2ms', color: '#4cd7f6' },
              { idx: '07', title: 'RUL ESTIMATION', sub: 'Weibull degradation fit', badge: `${rulHours.toFixed(1)} HRS`, color: '#4edea3' },
              { idx: '08', title: 'DECISION SUPPORT', sub: 'M-12 action dispatch', badge: 'ACTIVE', color: '#4cd7f6' },
            ].map((step) => (
              <div
                key={step.idx}
                className="bg-[#191c21] p-2.5 rounded flex flex-col justify-between hover:bg-[#272a30] transition-all border border-[#272a30]"
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold" style={{ color: step.color }}>{step.idx}</span>
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: step.color }} />
                </div>
                <div className="my-2">
                  <span className="text-[10px] text-white font-bold block">{step.title}</span>
                  <span className="text-[8px] text-[#bcc9cd]">{step.sub}</span>
                </div>
                <span className="text-[8px] font-bold" style={{ color: step.color }}>{step.badge}</span>
              </div>
            ))}
          </div>
        </section>

        {/* SECTION 6: OPERATING MODES & TIMELINE REPLAY SCRUBBER */}
        <section className="w-full bg-[#1d2025] rounded p-4 shadow-md flex flex-col gap-3 border border-[#272a30]">
          <div className="flex flex-wrap items-center justify-between gap-2 pb-1 border-b border-[#272a30]">
            <div className="flex items-center gap-2">
              <History className="w-4 h-4 text-[#4cd7f6]" />
              <h2 className="font-tech text-sm text-white tracking-wide uppercase font-bold">
                06 // OPERATING MODE &amp; HISTORICAL FLIGHT REPLAY
              </h2>
            </div>
            <div className="flex items-center bg-[#0b0e13] p-1 rounded gap-1 font-mono text-[10px]">
              <button
                onClick={() => handleModeSwitch('LIVE')}
                className={`px-3 py-1 rounded transition-all uppercase ${
                  operatingMode === 'LIVE' ? 'bg-[#4cd7f6] text-[#003640] font-bold' : 'text-[#bcc9cd]'
                }`}
              >
                LIVE FLIGHT
              </button>
              <button
                onClick={() => handleModeSwitch('SIMULATION')}
                className={`px-3 py-1 rounded flex items-center gap-1 font-bold transition-all uppercase ${
                  operatingMode === 'SIMULATION' ? 'bg-[#ee9800] text-[#5b3800]' : 'text-[#bcc9cd]'
                }`}
              >
                <span className="w-2 h-2 rounded-full bg-[#5b3800] animate-pulse" />
                SIMULATION ACTIVE
              </button>
              <button
                onClick={() => handleModeSwitch('REPLAY')}
                className={`px-3 py-1 rounded transition-all uppercase ${
                  operatingMode === 'REPLAY' ? 'bg-[#4edea3] text-[#003824] font-bold' : 'text-[#bcc9cd]'
                }`}
              >
                SESSION REPLAY
              </button>
            </div>
          </div>

          <div className="bg-[#191c21] p-4 rounded flex flex-col gap-3 border border-[#272a30] font-mono">
            <div className="flex flex-wrap items-center justify-between text-xs text-[#bcc9cd]">
              <div className="flex items-center gap-1.5">
                <span className="uppercase text-[#ffb95f] font-bold text-[10px]">ACTIVE SIMULATION:</span>
                <span className="text-[#ffb95f] font-bold text-[11px]">
                  BENCHMARK_SCENARIO_04_SYNTHETIC_DRIFT_RUNNING
                </span>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1">
                  <span>REPLAY SPEED:</span>
                  <span className="text-[#4cd7f6] font-bold">{playbackSpeed.toFixed(1)}x REALTIME</span>
                </div>
                <div className="flex items-center gap-1">
                  <span>MET:</span>
                  <span className="text-white font-bold">{metTimeStr}</span>
                </div>
              </div>
            </div>

            {/* Visual Interactive Timeline Bar */}
            <div className="relative w-full py-2">
              <div
                onClick={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const clickPct = ((e.clientX - rect.left) / rect.width) * 100;
                  const clamped = Math.max(0, Math.min(100, clickPct));
                  setProgressPct(clamped);

                  const isDevPort = window.location.port === '3000' || window.location.port === '5173';
                  const host = isDevPort
                    ? `${window.location.hostname || 'localhost'}:8000`
                    : window.location.host;
                  const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';

                  fetch(`${protocol}//${host}/replay/seek`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ position: clamped }),
                  }).catch(() => {});
                }}
                className="w-full bg-[#32353b] h-3.5 rounded relative cursor-pointer"
              >
                {/* Progress Bar */}
                <div className="bg-[#4cd7f6] h-full rounded transition-all" style={{ width: `${progressPct}%` }} />

                {/* Event Markers */}
                <div className="absolute top-0 bottom-0 left-[8%] w-0.5 bg-[#4edea3] flex flex-col items-center">
                  <span className="absolute -top-5 text-[8px] text-[#4edea3] font-bold">TAKEOFF</span>
                </div>
                <div className="absolute top-0 bottom-0 left-[24%] w-0.5 bg-[#4edea3] flex flex-col items-center">
                  <span className="absolute -top-5 text-[8px] text-[#4edea3] font-bold">CLIMB</span>
                </div>
                <div className="absolute top-0 bottom-0 left-[48%] w-0.5 bg-[#4cd7f6] flex flex-col items-center">
                  <span className="absolute -top-5 text-[8px] text-[#4cd7f6] font-bold">CRUISE</span>
                </div>
                <div className="absolute top-0 bottom-0 left-[68%] w-1 bg-[#ee9800] flex flex-col items-center">
                  <span className="absolute -top-5 text-[8px] text-[#ee9800] font-bold">ANOMALY DETECT</span>
                </div>

                {/* Scrubber Pin */}
                <div
                  className="absolute -top-1.5 w-4 h-6 bg-white rounded flex items-center justify-center shadow-lg -translate-x-1/2"
                  style={{ left: `${progressPct}%` }}
                >
                  <div className="w-1 h-3 bg-[#0b0e13]" />
                </div>
              </div>
            </div>

            {/* Scrubber Playback Controls */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => {
                    playTacticalClick();
                    setProgressPct(0);
                    const isDevPort = window.location.port === '3000' || window.location.port === '5173';
                    const host = isDevPort
                      ? `${window.location.hostname || 'localhost'}:8000`
                      : window.location.host;
                    const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
                    fetch(`${protocol}//${host}/replay/reset`, { method: 'POST' }).catch(() => {});
                  }}
                  className="w-8 h-8 bg-[#32353b] hover:bg-[#36393f] rounded flex items-center justify-center text-white"
                >
                  <Rewind className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={handleReplayToggle}
                  className="w-8 h-8 bg-[#4cd7f6] hover:bg-[#06b6d4] text-[#003640] rounded flex items-center justify-center font-bold shadow"
                >
                  {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </button>
                <button
                  onClick={handleSpeedCycle}
                  className="px-2.5 h-8 bg-[#32353b] hover:bg-[#36393f] rounded text-[10px] font-bold text-white flex items-center gap-1"
                >
                  <FastForward className="w-3 h-3 text-[#4cd7f6]" />
                  <span>{playbackSpeed.toFixed(1)}x</span>
                </button>
              </div>

              <div className="flex items-center gap-3">
                <span className="text-[10px] text-[#bcc9cd]">
                  FLIGHT DURATION: 05:38:00 (EST. REMAINING: 01:19:38)
                </span>
                <button
                  onClick={handleExportBlackbox}
                  className="px-3 py-1.5 bg-[#32353b] hover:bg-[#36393f] text-[#4cd7f6] font-bold text-[10px] rounded transition-all flex items-center gap-1.5"
                >
                  <Download className="w-3 h-3" />
                  <span>EXPORT BLACKBOX (HDF5)</span>
                </button>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* ==========================================================================
          FOOTER: TACTICAL CLASSIFICATION & DATA INTEGRITY BAR
          ========================================================================== */}
      <footer className="w-full h-8 px-4 bg-[#0b0e13] border-t border-[#1d2025] flex items-center justify-between text-[#bcc9cd] font-mono text-[9px]">
        <div className="flex items-center gap-2">
          <span className="text-[#869397]">AERIS-TWIN GCS v2.5.0-PROD</span>
          <span className="text-[#869397]">//</span>
          <span className="text-[#ffb95f] font-bold">CLASSIFICATION: NATO RESTRICTED / RESEARCH DEMONSTRATOR</span>
        </div>

        <div className="hidden md:flex items-center gap-2">
          <span>DATA INTEGRITY ENGINE: ACTIVE</span>
          <span className="text-[#869397]">//</span>
          <span className="text-[#4cd7f6]">DIGITAL TWIN RESIDUAL: RMS 0.042</span>
          <span className="text-[#869397]">//</span>
          <span className="text-[#4edea3]">FADEC DUAL CHANNEL A+B</span>
        </div>

        <span className="text-[#869397] uppercase">
          DISCLAIMER: DEMONSTRATOR — NOT CERTIFIED FOR FLIGHT SAFETY SIGN-OFF
        </span>
      </footer>
    </div>
  );
};
