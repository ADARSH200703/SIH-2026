import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

/**
 * AERIS-TWIN 3D Interactive UAV & Aero Piston Engine Digital Twin
 * Real-time physics synchronization, component inspection, exploded cutaway,
 * interactive sensor markers, smooth camera transitions, and fault visualization.
 */
export class ThreeDigitalTwin {
  constructor(containerElement, onComponentSelect) {
    this.container = containerElement;
    this.onComponentSelect = onComponentSelect;
    
    // Component Registries & Groups
    this.components = {};
    this.sensorNodes = {};
    this.meshToComponent = new Map();
    
    // Dynamic Animation Elements
    this.propellerGroup = null;
    this.crankshaftGroup = null;
    this.pistonMeshes = [];
    this.cylinderHeads = [];
    this.bearingMeshes = [];
    this.sensorMarkers = [];
    
    // Visualization States
    this.currentMode = 'solid';       // 'solid' | 'hologram' | 'thermal'
    this.isEngineInspection = false;
    this.explodedFactor = 0.0;
    this.targetExplodedFactor = 0.0;
    this.showSensors = true;
    this.showLabels = true;
    
    // Live Telemetry Cache
    this.rpm = 4215.0;
    this.temperature = 78.4;
    this.vibration = 1.6;
    this.oilPressure = 4.3;
    this.fuelFlow = 5.2;
    this.engineHealth = 92.0;
    this.activeFault = 'NOMINAL';
    
    // Camera Tweening State
    this.cameraTween = {
      active: false,
      startPos: new THREE.Vector3(),
      targetPos: new THREE.Vector3(),
      startLookAt: new THREE.Vector3(),
      targetLookAt: new THREE.Vector3(),
      progress: 0.0,
      duration: 45 // frames
    };
    this.currentLookAt = new THREE.Vector3(0, 0, 0);
    
    // Raycasting & Interaction
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
    this.selectedComponentId = 'engine';
    this.hoveredComponentId = null;

    this._init();
    this._animate();
  }

  _init() {
    const w = this.container.clientWidth || 900;
    const h = this.container.clientHeight || 550;

    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x0B1120, 0.025);

    this.camera = new THREE.PerspectiveCamera(42, w / h, 0.1, 1000);
    this.camera.position.set(0, 3.8, 8.5);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.35;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.container.appendChild(this.renderer.domElement);

    // Dynamic Lighting
    this.ambientLight = new THREE.AmbientLight(0xE5E7EB, 0.70);
    this.scene.add(this.ambientLight);

    this.sunLight = new THREE.DirectionalLight(0xF8FAFC, 1.6);
    this.sunLight.position.set(8, 14, 10);
    this.sunLight.castShadow = true;
    this.sunLight.shadow.mapSize.width = 2048;
    this.sunLight.shadow.mapSize.height = 2048;
    this.scene.add(this.sunLight);

    this.rimLight = new THREE.DirectionalLight(0x38BDF8, 0.85);
    this.rimLight.position.set(-10, -5, -8);
    this.scene.add(this.rimLight);
    
    this.engineSpot = new THREE.PointLight(0x38BDF8, 1.1, 15);
    this.engineSpot.position.set(0, 2.5, 0.5);
    this.scene.add(this.engineSpot);

    // Grid Floor
    const grid = new THREE.GridHelper(30, 50, 0x263449, 0x172033);
    grid.position.y = -2.8;
    this.scene.add(grid);

    // OrbitControls
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.06;
    this.controls.minDistance = 1.2;
    this.controls.maxDistance = 35.0;
    this.controls.autoRotate = false;
    this.controls.autoRotateSpeed = 0.4;
    this.controls.target.set(0, 0, 0);

    this._buildMaterials();
    this._buildUAVModel();
    this._setupInteraction();
    
    window.addEventListener('resize', () => this.onResize());
  }

  _buildMaterials() {
    this.mats = {
      // Solid Aerospace Alloys
      carbonAirframe: new THREE.MeshStandardMaterial({
        color: 0x1E293B, metalness: 0.85, roughness: 0.35, transparent: true, opacity: 0.96
      }),
      wingAlloy: new THREE.MeshStandardMaterial({
        color: 0x334155, metalness: 0.80, roughness: 0.35, transparent: true, opacity: 0.96
      }),
      cowlingAlloy: new THREE.MeshStandardMaterial({
        color: 0x1E293B, metalness: 0.88, roughness: 0.28, transparent: true, opacity: 0.92
      }),
      engineBlock: new THREE.MeshStandardMaterial({
        color: 0x475569, metalness: 0.90, roughness: 0.25
      }),
      cylinderAlloy: new THREE.MeshStandardMaterial({
        color: 0x64748B, metalness: 0.88, roughness: 0.28, emissive: 0x111827, emissiveIntensity: 0.2
      }),
      crankshaftSteel: new THREE.MeshStandardMaterial({
        color: 0x94A3B8, metalness: 0.95, roughness: 0.15
      }),
      bearingBronze: new THREE.MeshStandardMaterial({
        color: 0xCBD5E1, metalness: 0.92, roughness: 0.20, emissive: 0x1E293B, emissiveIntensity: 0.2
      }),
      propellerCarbon: new THREE.MeshStandardMaterial({
        color: 0x0F172A, metalness: 0.90, roughness: 0.20
      }),
      propellerHub: new THREE.MeshStandardMaterial({
        color: 0x94A3B8, metalness: 0.95, roughness: 0.15
      }),
      exhaustTitanium: new THREE.MeshStandardMaterial({
        color: 0x64748B, metalness: 0.88, roughness: 0.3
      }),
      fuelRail: new THREE.MeshStandardMaterial({
        color: 0x2DD4BF, metalness: 0.75, roughness: 0.25, emissive: 0x0F766E, emissiveIntensity: 0.3
      }),
      coolingFins: new THREE.MeshStandardMaterial({
        color: 0x38BDF8, metalness: 0.80, roughness: 0.3, emissive: 0x0369A1, emissiveIntensity: 0.25
      }),
      ecuModule: new THREE.MeshStandardMaterial({
        color: 0x172033, metalness: 0.7, roughness: 0.4, emissive: 0x0B1120, emissiveIntensity: 0.4
      }),

      // Status Indicator Materials
      healthyMat: new THREE.MeshStandardMaterial({
        color: 0x22C55E, metalness: 0.6, roughness: 0.3, emissive: 0x22C55E, emissiveIntensity: 0.5
      }),
      warningMat: new THREE.MeshStandardMaterial({
        color: 0xF59E0B, metalness: 0.6, roughness: 0.3, emissive: 0xF59E0B, emissiveIntensity: 0.6
      }),
      faultMat: new THREE.MeshStandardMaterial({
        color: 0xEF4444, metalness: 0.6, roughness: 0.2, emissive: 0xEF4444, emissiveIntensity: 0.7
      }),
      unknownMat: new THREE.MeshStandardMaterial({
        color: 0x64748B, metalness: 0.6, roughness: 0.3, emissive: 0x64748B, emissiveIntensity: 0.3
      }),
      
      // Wireframe / Hologram Materials
      hologramWire: new THREE.MeshStandardMaterial({
        color: 0x38BDF8, wireframe: true, transparent: true, opacity: 0.35, emissive: 0x0284C7, emissiveIntensity: 0.3
      }),
      hologramGhost: new THREE.MeshStandardMaterial({
        color: 0x2DD4BF, transparent: true, opacity: 0.12, wireframe: false, depthWrite: false
      }),
      
      // Selected Highlight Glow
      selectedGlow: new THREE.MeshStandardMaterial({
        color: 0x38BDF8, metalness: 0.8, roughness: 0.2, emissive: 0x38BDF8, emissiveIntensity: 0.6
      })
    };
  }

  _registerPart(mesh, componentId, name, type, explosionOffset = new THREE.Vector3(0, 0, 0)) {
    mesh.userData = {
      componentId,
      name,
      type,
      originalPosition: mesh.position.clone(),
      explosionOffset: explosionOffset.clone(),
      originalMaterial: mesh.material
    };
    this.meshToComponent.set(mesh, componentId);
    if (!this.components[componentId]) {
      this.components[componentId] = { id: componentId, name, type, meshes: [] };
    }
    this.components[componentId].meshes.push(mesh);
  }

  _buildUAVModel() {
    this.uavRoot = new THREE.Group();
    this.scene.add(this.uavRoot);

    this.airframeGroup = new THREE.Group();
    this.engineGroup    = new THREE.Group();
    this.propellerGroup = new THREE.Group();
    this.sensorsGroup   = new THREE.Group();

    this.uavRoot.add(this.airframeGroup);
    this.uavRoot.add(this.engineGroup);
    this.uavRoot.add(this.propellerGroup);
    this.uavRoot.add(this.sensorsGroup);

    // ─────────────────────────────────────────────────────────────────────────
    // 1. AIRFRAME HIERARCHY (Fuselage, High-Aspect Wings, V-Tail, Nose Dome)
    // ─────────────────────────────────────────────────────────────────────────
    
    // Main Fuselage
    const fuseGeo = new THREE.CylinderGeometry(0.72, 0.42, 6.8, 32, 8);
    fuseGeo.rotateX(Math.PI / 2);
    const fuselage = new THREE.Mesh(fuseGeo, this.mats.carbonAirframe);
    fuselage.position.set(0, 0.15, -0.4);
    this.airframeGroup.add(fuselage);
    this._registerPart(fuselage, 'airframe', 'UAV Composite Fuselage', 'STRUCTURE', new THREE.Vector3(0, 0.6, 0));

    // Nose Cone Payload Dome (EO/IR Sensor Dome)
    const domeGeo = new THREE.SphereGeometry(0.70, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2);
    domeGeo.rotateX(-Math.PI / 2);
    const noseDome = new THREE.Mesh(domeGeo, this.mats.carbonAirframe);
    noseDome.position.set(0, 0.15, 3.0);
    this.airframeGroup.add(noseDome);
    this._registerPart(noseDome, 'airframe', 'Payload Nose Dome', 'STRUCTURE', new THREE.Vector3(0, 0, 1.2));

    // Wings (Left & Right High-Aspect Ratio Swept Wings)
    const wingShape = new THREE.Shape();
    wingShape.moveTo(0, 0);
    wingShape.lineTo(9.5, -0.6);
    wingShape.lineTo(9.2, -1.5);
    wingShape.lineTo(0, -1.8);
    wingShape.closePath();
    const extrudeSettings = { depth: 0.14, bevelEnabled: true, bevelSegments: 3, steps: 1, bevelSize: 0.04, bevelThickness: 0.04 };
    
    const leftWingGeo = new THREE.ExtrudeGeometry(wingShape, extrudeSettings);
    leftWingGeo.rotateX(Math.PI / 2);
    const leftWing = new THREE.Mesh(leftWingGeo, this.mats.wingAlloy);
    leftWing.position.set(0.65, 0.35, 0.4);
    this.airframeGroup.add(leftWing);
    this._registerPart(leftWing, 'airframe', 'Left Main Wing Assembly', 'STRUCTURE', new THREE.Vector3(1.8, 0, 0));

    const rightWingGeo = leftWingGeo.clone();
    rightWingGeo.scale(-1, 1, 1);
    const rightWing = new THREE.Mesh(rightWingGeo, this.mats.wingAlloy);
    rightWing.position.set(-0.65, 0.35, 0.4);
    this.airframeGroup.add(rightWing);
    this._registerPart(rightWing, 'airframe', 'Right Main Wing Assembly', 'STRUCTURE', new THREE.Vector3(-1.8, 0, 0));

    // V-Tail Empennage (Twin Cantilever Stabilizers)
    const tailGeo = new THREE.BoxGeometry(0.12, 1.9, 1.1);
    const leftTail = new THREE.Mesh(tailGeo, this.mats.wingAlloy);
    leftTail.position.set(0.7, 1.0, -3.5);
    leftTail.rotation.z = -0.42;
    this.airframeGroup.add(leftTail);
    this._registerPart(leftTail, 'airframe', 'Left V-Tail Stabilizer', 'STRUCTURE', new THREE.Vector3(0.8, 0.6, -0.6));

    const rightTail = new THREE.Mesh(tailGeo, this.mats.wingAlloy);
    rightTail.position.set(-0.7, 1.0, -3.5);
    rightTail.rotation.z = 0.42;
    this.airframeGroup.add(rightTail);
    this._registerPart(rightTail, 'airframe', 'Right V-Tail Stabilizer', 'STRUCTURE', new THREE.Vector3(-0.8, 0.6, -0.6));

    // Removable Engine Nacelle Cowling
    const cowlGeo = new THREE.CylinderGeometry(0.82, 0.76, 2.2, 24, 4, true);
    cowlGeo.rotateX(Math.PI / 2);
    this.nacelleCowl = new THREE.Mesh(cowlGeo, this.mats.cowlingAlloy);
    this.nacelleCowl.position.set(0, 0.22, -1.8);
    this.airframeGroup.add(this.nacelleCowl);
    this._registerPart(this.nacelleCowl, 'airframe', 'Engine Nacelle Cowling', 'STRUCTURE', new THREE.Vector3(0, 1.6, 0));

    // ─────────────────────────────────────────────────────────────────────────
    // 2. ROTAX 914 AERO PISTON ENGINE ASSEMBLY
    // ─────────────────────────────────────────────────────────────────────────

    // Engine Crankcase Core
    const crankcaseGeo = new THREE.BoxGeometry(1.25, 0.85, 1.6);
    this.crankcaseMesh = new THREE.Mesh(crankcaseGeo, this.mats.engineBlock);
    this.crankcaseMesh.position.set(0, 0.2, -1.8);
    this.engineGroup.add(this.crankcaseMesh);
    this._registerPart(this.crankcaseMesh, 'engine', 'Rotax 914 Engine Crankcase', 'POWERPLANT', new THREE.Vector3(0, 0, 0));

    // 4 Opposed Cylinders (Horizontally Opposed Layout)
    const cylOffsets = [
      { id: 'cylinder_1', name: 'Cylinder #1 (Front-Right)', pos: [0.95, 0.32, -1.35], rotZ: -Math.PI / 2, exp: [1.4, 0.2, 0.3] },
      { id: 'cylinder_2', name: 'Cylinder #2 (Front-Left)',  pos: [-0.95, 0.32, -1.35], rotZ: Math.PI / 2, exp: [-1.4, 0.2, 0.3] },
      { id: 'cylinder_3', name: 'Cylinder #3 (Rear-Right)',  pos: [0.95, 0.32, -2.15], rotZ: -Math.PI / 2, exp: [1.4, 0.2, -0.3] },
      { id: 'cylinder_4', name: 'Cylinder #4 (Rear-Left)',   pos: [-0.95, 0.32, -2.15], rotZ: Math.PI / 2, exp: [-1.4, 0.2, -0.3] },
    ];

    cylOffsets.forEach(cfg => {
      const cylGroup = new THREE.Group();
      cylGroup.position.set(...cfg.pos);
      
      // Cylinder Barrel with Cooling Ribs
      const barrelGeo = new THREE.CylinderGeometry(0.36, 0.36, 0.72, 20);
      barrelGeo.rotateZ(cfg.rotZ);
      const barrel = new THREE.Mesh(barrelGeo, this.mats.cylinderAlloy);
      cylGroup.add(barrel);
      
      // Cooling Rib Disks
      for (let r = -0.22; r <= 0.22; r += 0.11) {
        const ribGeo = new THREE.CylinderGeometry(0.42, 0.42, 0.03, 20);
        ribGeo.rotateZ(cfg.rotZ);
        const rib = new THREE.Mesh(ribGeo, this.mats.coolingFins);
        if (cfg.rotZ > 0) rib.position.x = r; else rib.position.x = -r;
        cylGroup.add(rib);
      }

      // Spark Plug Tip
      const plugGeo = new THREE.CylinderGeometry(0.06, 0.06, 0.22, 10);
      const plug = new THREE.Mesh(plugGeo, this.mats.bearingBronze);
      plug.position.set(cfg.rotZ > 0 ? -0.42 : 0.42, 0.28, 0);
      cylGroup.add(plug);

      this.engineGroup.add(cylGroup);
      this.cylinderHeads.push(cylGroup);
      this._registerPart(barrel, cfg.id, cfg.name, 'COMBUSTION', new THREE.Vector3(...cfg.exp));
    });

    // Crankshaft & Connecting Rods Assembly
    const crankGeo = new THREE.CylinderGeometry(0.12, 0.12, 1.8, 16);
    crankGeo.rotateX(Math.PI / 2);
    this.crankshaftMesh = new THREE.Mesh(crankGeo, this.mats.crankshaftSteel);
    this.crankshaftMesh.position.set(0, 0.2, -1.8);
    this.engineGroup.add(this.crankshaftMesh);
    this._registerPart(this.crankshaftMesh, 'crankshaft', 'Alloy Crankshaft & Con-Rods', 'MECHANICAL', new THREE.Vector3(0, -0.6, 0));

    // Main Journal Bearings
    const bearingGeo = new THREE.TorusGeometry(0.24, 0.08, 12, 24);
    bearingGeo.rotateY(Math.PI / 2);
    const bearingFront = new THREE.Mesh(bearingGeo, this.mats.bearingBronze);
    bearingFront.position.set(0, 0.2, -1.1);
    const bearingRear = new THREE.Mesh(bearingGeo, this.mats.bearingBronze);
    bearingRear.position.set(0, 0.2, -2.5);
    this.engineGroup.add(bearingFront, bearingRear);
    this.bearingMeshes.push(bearingFront, bearingRear);
    this._registerPart(bearingFront, 'bearings', 'Main Journal Crankshaft Bearings', 'MECHANICAL', new THREE.Vector3(0, 0.6, 0.8));
    this._registerPart(bearingRear, 'bearings', 'Main Journal Crankshaft Bearings', 'MECHANICAL', new THREE.Vector3(0, 0.6, -0.8));

    // Liquid Cooling Radiator & Heat Exchanger
    const radGeo = new THREE.BoxGeometry(1.1, 0.45, 0.25);
    const radiator = new THREE.Mesh(radGeo, this.mats.coolingFins);
    radiator.position.set(0, -0.45, -1.8);
    this.engineGroup.add(radiator);
    this._registerPart(radiator, 'cooling_system', 'Ram-Air Liquid Cooling Radiator', 'COOLING', new THREE.Vector3(0, -1.5, 0));

    // Common-Rail Fuel Injection & Spark Module
    const fuelGeo = new THREE.CylinderGeometry(0.06, 0.06, 1.4, 12);
    fuelGeo.rotateX(Math.PI / 2);
    const fuelRail = new THREE.Mesh(fuelGeo, this.mats.fuelRail);
    fuelRail.position.set(0, 0.72, -1.8);
    this.engineGroup.add(fuelRail);
    this._registerPart(fuelRail, 'fuel_system', 'Common-Rail Fuel Injection & Magneto', 'FUEL_IGNITION', new THREE.Vector3(0, 1.4, 0));

    // Dry Sump Pressurized Lubrication Pan
    const sumpGeo = new THREE.BoxGeometry(0.9, 0.28, 1.2);
    const sump = new THREE.Mesh(sumpGeo, this.mats.engineBlock);
    sump.position.set(0, -0.26, -1.8);
    this.engineGroup.add(sump);
    this._registerPart(sump, 'oil_system', 'Dry Sump Pressurized Lubrication Sump', 'LUBRICATION', new THREE.Vector3(0, -1.0, 0));

    // Dual-Redundant Electronic Engine Controller (ECU)
    const ecuGeo = new THREE.BoxGeometry(0.65, 0.35, 0.5);
    const ecu = new THREE.Mesh(ecuGeo, this.mats.ecuModule);
    ecu.position.set(0, 0.65, -0.85);
    this.engineGroup.add(ecu);
    this._registerPart(ecu, 'ecu', 'Dual-Redundant Electronic Engine Controller (ECU)', 'AVIONICS', new THREE.Vector3(0, 1.2, 0.8));

    // Edge IoT Telemetry Transceiver
    const telemGeo = new THREE.BoxGeometry(0.45, 0.25, 0.35);
    const telem = new THREE.Mesh(telemGeo, this.mats.ecuModule);
    telem.position.set(0, 0.65, -0.35);
    this.engineGroup.add(telem);
    this._registerPart(telem, 'telemetry_gateway', 'Edge 10Hz CAN-bus Telemetry Gateway', 'TELEMETRY', new THREE.Vector3(0, 1.2, 1.4));

    // ─────────────────────────────────────────────────────────────────────────
    // 3. 3-BLADE PUSHER PROPELLER ASSEMBLY
    // ─────────────────────────────────────────────────────────────────────────
    this.propellerGroup.position.set(0, 0.2, -3.85);

    // Propeller Spinner Hub
    const hubGeo = new THREE.ConeGeometry(0.32, 0.75, 24);
    hubGeo.rotateX(-Math.PI / 2);
    const hub = new THREE.Mesh(hubGeo, this.mats.propellerHub);
    this.propellerGroup.add(hub);
    this._registerPart(hub, 'propeller', 'Titanium Constant-Speed Propeller Hub', 'PROPULSION', new THREE.Vector3(0, 0, -2.0));

    // 3 Aerodynamic Blades
    for (let i = 0; i < 3; i++) {
      const angle = (i * Math.PI * 2) / 3;
      const bladeGeo = new THREE.BoxGeometry(0.18, 2.3, 0.04);
      const blade = new THREE.Mesh(bladeGeo, this.mats.propellerCarbon);
      blade.position.set(Math.cos(angle) * 1.15, Math.sin(angle) * 1.15, 0);
      blade.rotation.z = angle + Math.PI / 2;
      blade.rotation.y = 0.22; // Aerodynamic pitch angle
      this.propellerGroup.add(blade);
      this._registerPart(blade, 'propeller', 'Carbon Fiber Propeller Blade', 'PROPULSION', new THREE.Vector3(0, 0, -2.0));
    }

    // ─────────────────────────────────────────────────────────────────────────
    // 4. INTERACTIVE SENSOR TRANSDUCER NODES
    // ─────────────────────────────────────────────────────────────────────────
    const SENSOR_DEFINITIONS = [
      { id: 'sensor_vib', name: 'Tri-Axial Vibration Accelerometer', pos: [0.65, 0.65, -1.8], color: 0xF59E0B, param: 'vibration' },
      { id: 'sensor_cht', name: 'Cylinder Head Thermocouple (CHT)',  pos: [1.15, 0.45, -1.35], color: 0xEF4444, param: 'temperature' },
      { id: 'sensor_oil', name: 'Oil Pressure Transducer (Bar)',     pos: [-0.65, -0.15, -1.8], color: 0x38BDF8, param: 'oilPressure' },
      { id: 'sensor_rpm', name: 'Optical Crankshaft RPM Sensor',     pos: [0, 0.45, -1.05], color: 0x2DD4BF, param: 'rpm' },
      { id: 'sensor_fuel', name: 'Fuel Mass Flow Sensor (L/h)',      pos: [0.35, 0.82, -1.6], color: 0xF59E0B, param: 'fuelFlow' },
    ];

    SENSOR_DEFINITIONS.forEach(s => {
      const sGroup = new THREE.Group();
      sGroup.position.set(...s.pos);
      
      // Sensor Sphere Core
      const markerGeo = new THREE.SphereGeometry(0.11, 16, 16);
      const markerMat = new THREE.MeshStandardMaterial({
        color: s.color, emissive: s.color, emissiveIntensity: 0.9, roughness: 0.2
      });
      const marker = new THREE.Mesh(markerGeo, markerMat);
      sGroup.add(marker);

      // Pulsing Outer Ring
      const ringGeo = new THREE.RingGeometry(0.14, 0.18, 20);
      const ringMat = new THREE.MeshBasicMaterial({ color: s.color, side: THREE.DoubleSide, transparent: true, opacity: 0.8 });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.rotation.x = Math.PI / 2;
      sGroup.add(ring);

      this.sensorsGroup.add(sGroup);
      this.sensorMarkers.push({ group: sGroup, ring, ringMat, baseColor: s.color });
      this.sensorNodes[s.id] = sGroup;
      
      this._registerPart(marker, s.id, s.name, 'SENSOR', new THREE.Vector3(s.pos[0] * 1.5, s.pos[1] * 1.5, 0));
    });
  }

  _setupInteraction() {
    let isDragging = false;
    let downX = 0;
    let downY = 0;

    this.renderer.domElement.addEventListener('pointerdown', (e) => {
      isDragging = false;
      downX = e.clientX;
      downY = e.clientY;
    });

    this.renderer.domElement.addEventListener('pointermove', (e) => {
      if (Math.hypot(e.clientX - downX, e.clientY - downY) > 6) {
        isDragging = true;
      }
    });

    this.renderer.domElement.addEventListener('pointerup', (e) => {
      // If user was dragging / orbiting, do not raycast or select
      if (isDragging) return;

      const rect = this.renderer.domElement.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      
      this.raycaster.setFromCamera(this.mouse, this.camera);
      const intersects = this.raycaster.intersectObjects(this.uavRoot.children, true);
      
      if (intersects.length > 0) {
        for (let i = 0; i < intersects.length; i++) {
          let hitMesh = intersects[i].object;
          let compId = hitMesh.userData?.componentId || this.meshToComponent.get(hitMesh);
          if (compId) {
            this.selectComponent(compId, true, true); // focus camera & userTriggered
            break;
          }
        }
      }
    });

    // Cancel automatic camera tweens whenever the user manually controls the camera
    this.controls.addEventListener('start', () => {
      this.cameraTween.active = false;
    });
  }

  // ───────────────────────────────────────────────────────────────────────────
  // CAMERA PRESETS & SMOOTH TWEENING
  // ─────────────────────────────────────────────────────────────────────────
  setCameraPreset(presetName) {
    const PRESETS = {
      front:     { pos: new THREE.Vector3(0, 0.5, 9.5),   lookAt: new THREE.Vector3(0, 0.1, 0) },
      rear:      { pos: new THREE.Vector3(0, 1.2, -9.5),  lookAt: new THREE.Vector3(0, 0.1, -1.5) },
      left:      { pos: new THREE.Vector3(-10.5, 0.6, 0), lookAt: new THREE.Vector3(0, 0.1, 0) },
      right:     { pos: new THREE.Vector3(10.5, 0.6, 0),  lookAt: new THREE.Vector3(0, 0.1, 0) },
      top:       { pos: new THREE.Vector3(0, 13.5, 0.1),  lookAt: new THREE.Vector3(0, 0, 0) },
      bottom:    { pos: new THREE.Vector3(0, -13.5, 0.1), lookAt: new THREE.Vector3(0, 0, 0) },
      isometric: { pos: new THREE.Vector3(6.5, 4.2, 8.5), lookAt: new THREE.Vector3(0, 0, 0) },
      engine:    { pos: new THREE.Vector3(1.8, 1.4, -0.6), lookAt: new THREE.Vector3(0, 0.2, -1.8) },
    };

    const target = PRESETS[presetName.toLowerCase()] || PRESETS.isometric;
    this.tweenCameraTo(target.pos, target.lookAt);
  }

  tweenCameraTo(targetPos, targetLookAt, duration = 40) {
    this.cameraTween.startPos.copy(this.camera.position);
    this.cameraTween.targetPos.copy(targetPos);
    this.cameraTween.startLookAt.copy(this.controls.target);
    this.cameraTween.targetLookAt.copy(targetLookAt);
    this.cameraTween.progress = 0.0;
    this.cameraTween.duration = duration;
    this.cameraTween.active = true;
  }

  // ───────────────────────────────────────────────────────────────────────────
  // COMPONENT SELECTION & FOCUS
  // ─────────────────────────────────────────────────────────────────────────
  selectComponent(componentId, focusCamera = false, userTriggered = false) {
    this.selectedComponentId = componentId;
    
    // Focus camera ONLY if explicitly requested by user interaction
    if (focusCamera) {
      const comp = this.components[componentId];
      if (comp && comp.meshes.length > 0) {
        const box = new THREE.Box3();
        comp.meshes.forEach(m => box.expandByObject(m));
        const center = new THREE.Vector3();
        box.getCenter(center);
        
        const size = new THREE.Vector3();
        box.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z, 0.8);
        
        // Calculate smooth view distance along current viewing angle
        const distance = Math.max(maxDim * 2.4, 2.2);
        let direction = this.camera.position.clone().sub(this.controls.target);
        if (direction.lengthSq() < 0.01) {
          direction.set(1.5, 1.2, 1.5);
        }
        direction.normalize();
        
        const newCameraPos = center.clone().add(direction.multiplyScalar(distance));
        this.tweenCameraTo(newCameraPos, center, 35);
      }
    }

    if (this.onComponentSelect) {
      this.onComponentSelect(componentId, userTriggered);
    }
  }

  // ───────────────────────────────────────────────────────────────────────────
  // ENGINE INSPECTION & EXPLODED VIEW MODES
  // ─────────────────────────────────────────────────────────────────────────
  toggleEngineInspection(enable) {
    this.isEngineInspection = enable !== undefined ? enable : !this.isEngineInspection;
    
    if (this.isEngineInspection) {
      // Make airframe translucent / ghost
      this.airframeGroup.traverse(child => {
        if (child.isMesh) {
          child.material = this.mats.hologramGhost;
        }
      });
      if (this.nacelleCowl) this.nacelleCowl.visible = false;
      this.setCameraPreset('engine');
    } else {
      // Restore solid airframe
      this.airframeGroup.traverse(child => {
        if (child.isMesh && child.userData.originalMaterial) {
          child.material = child.userData.originalMaterial;
        }
      });
      if (this.nacelleCowl) this.nacelleCowl.visible = true;
    }
  }

  setExplodedView(factor) {
    this.targetExplodedFactor = Math.max(0.0, Math.min(1.0, factor));
  }

  setRenderMode(mode) {
    this.currentMode = mode;
    this.uavRoot.traverse(child => {
      if (child.isMesh && child.userData.componentId) {
        if (mode === 'hologram') {
          child.material = this.mats.hologramWire;
        } else if (mode === 'thermal') {
          // Heatmap based on CHT
          const heatCol = this.temperature > 85 ? 0xEF4444 : (this.temperature > 78 ? 0xF59E0B : 0x22C55E);
          child.material = new THREE.MeshStandardMaterial({ color: heatCol, emissive: heatCol, emissiveIntensity: 0.6, wireframe: false });
        } else {
          child.material = child.userData.originalMaterial || this.mats.carbonAirframe;
        }
      }
    });
  }

  toggleSensors(show) {
    this.showSensors = show !== undefined ? show : !this.showSensors;
    this.sensorsGroup.visible = this.showSensors;
  }

  // ───────────────────────────────────────────────────────────────────────────
  // LIVE TELEMETRY & DIGITAL TWIN STATE SYNCHRONIZATION
  // ─────────────────────────────────────────────────────────────────────────
  updateState(state) {
    if (!state) return;
    this.rpm = Number(state.rpm) || 4215.0;
    this.temperature = Number(state.temperature) || 78.4;
    this.vibration = Number(state.vibration) || 1.6;
    this.oilPressure = Number(state.oilPressure) || 4.3;
    this.fuelFlow = Number(state.fuelFlow) || 5.2;
    this.engineHealth = Number(state.engineHealth) || 92.0;
    this.activeFault = state.fault_class || (state.activeScenario !== 'cruise' ? state.activeScenario : 'NOMINAL');
    
    this._updateComponentVisualHealth();
  }

  _updateComponentVisualHealth() {
    // Dynamic status color calculation
    const isBearingFault = this.activeFault.includes('bearing') || this.vibration > 3.5;
    const isThermalFault = this.activeFault.includes('thermal') || this.temperature > 90.0;
    const isLubeFault    = this.activeFault.includes('lubrication') || this.oilPressure < 3.0;

    this.bearingMeshes.forEach(m => {
      if (isBearingFault) {
        m.material = this.mats.faultMat;
      } else if (this.currentMode === 'solid') {
        m.material = this.mats.bearingBronze;
      }
    });

    this.cylinderHeads.forEach(g => {
      g.traverse(c => {
        if (c.isMesh && isThermalFault) {
          c.material = this.mats.faultMat;
        } else if (c.isMesh && this.currentMode === 'solid') {
          c.material = c.userData.originalMaterial || this.mats.cylinderAlloy;
        }
      });
    });
  }

  // ───────────────────────────────────────────────────────────────────────────
  // ANIMATION & RENDER LOOP
  // ─────────────────────────────────────────────────────────────────────────
  _animate() {
    requestAnimationFrame(() => this._animate());

    const delta = 0.016; // ~60fps step
    
    // 1. Smooth Camera Interpolation
    if (this.cameraTween.active) {
      this.cameraTween.progress += 1.0 / this.cameraTween.duration;
      const t = Math.min(1.0, this.cameraTween.progress);
      // Smooth cubic easing
      const easeT = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
      
      this.camera.position.lerpVectors(this.cameraTween.startPos, this.cameraTween.targetPos, easeT);
      this.controls.target.lerpVectors(this.cameraTween.startLookAt, this.cameraTween.targetLookAt, easeT);
      
      if (t >= 1.0) {
        this.cameraTween.active = false;
      }
    }

    // 2. Propeller & Kinematic Motion matching live RPM
    if (this.propellerGroup) {
      const rotSpeed = (this.rpm / 60.0) * (Math.PI * 2) * delta;
      this.propellerGroup.rotation.z += rotSpeed;
    }
    if (this.crankshaftMesh) {
      const crankSpeed = (this.rpm / 60.0) * (Math.PI * 2) * delta;
      this.crankshaftMesh.rotation.z += crankSpeed;
    }

    // 3. Smooth Exploded View Transition
    if (Math.abs(this.explodedFactor - this.targetExplodedFactor) > 0.001) {
      this.explodedFactor += (this.targetExplodedFactor - this.explodedFactor) * 0.10;
      
      this.uavRoot.traverse(child => {
        if (child.isMesh && child.userData.originalPosition && child.userData.explosionOffset) {
          const orig = child.userData.originalPosition;
          const off = child.userData.explosionOffset;
          child.position.set(
            orig.x + off.x * this.explodedFactor,
            orig.y + off.y * this.explodedFactor,
            orig.z + off.z * this.explodedFactor
          );
        }
      });
    }

    // 4. Sensor Ring Pulse Animation
    const timeSec = performance.now() * 0.003;
    this.sensorMarkers.forEach(s => {
      const scale = 1.0 + Math.sin(timeSec * 2.5) * 0.25;
      s.ring.scale.set(scale, scale, 1);
      s.ringMat.opacity = 0.4 + Math.cos(timeSec * 2.5) * 0.35;
    });

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  onResize() {
    if (!this.container || !this.renderer || !this.camera) return;
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    if (w > 0 && h > 0) {
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    }
  }

  dispose() {
    this.renderer.dispose();
    if (this.renderer.domElement && this.renderer.domElement.parentNode) {
      this.renderer.domElement.parentNode.removeChild(this.renderer.domElement);
    }
  }
}
