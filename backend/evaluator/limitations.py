"""
System Limitations & Scientific Integrity Disclosures for AERIS-TWIN
Explicitly documents airworthiness scope, model assumptions, data origin, and validation roadmap.
Addresses the 7 Critical Technical Limitations for SIH Evaluators.
"""
from typing import Dict, Any, List

SYSTEM_LIMITATIONS: Dict[str, Any] = {
    "system_name": "AERIS-TWIN — Aero Engine Reliability & Intelligence System",
    "version": "2.5.0-ResearchPrototype",
    "project_class": "RESEARCH_AND_TECHNOLOGY_DEMONSTRATOR",
    "decision_support_mode": "DECISION_SUPPORT_ONLY",
    "flight_qualification": "NON_FLIGHT_QUALIFIED_PROTOTYPE",
    "autonomous_control": "NO_AUTONOMOUS_AIRCRAFT_CONTROL",
    "critical_safety_rule": "AERIS-TWIN provides predictive health monitoring and decision support advisories to UAV operators and supervisory maintenance systems. It MUST NOT directly actuate flight surfaces, engine throttles, or autopilot commands.",
    
    # ─── 7 CRITICAL EVALUATOR QUESTIONS & DISCLOSURES ───
    "evaluator_disclosures": {
        "1_flight_qualified": {
            "question": "Is this flight qualified?",
            "answer": "NO. AERIS-TWIN is a Research Prototype and Technology Demonstrator for decision support. It has not undergone DO-178C (Software) or DO-254 (Hardware) civil/military airworthiness certification.",
            "status": "RESEARCH_PROTOTYPE_ONLY"
        },
        "2_autonomous_flight_controller": {
            "question": "Is this an autonomous flight controller?",
            "answer": "NO. AERIS-TWIN is an advisory decision support system. It provides diagnostic insights, remaining useful life estimates, and recommended operator actions. It does not exert closed-loop autonomous control over engine or flight surfaces.",
            "status": "ADVISORY_DECISION_SUPPORT"
        },
        "3_rul_guarantee": {
            "question": "Is RUL guaranteed?",
            "answer": "NO. RUL is an engineering estimate with dynamic confidence intervals [lower_bound, upper_bound] conditioned on data sufficiency and sensor trust. It is NOT a guaranteed countdown clock.",
            "status": "ENGINEERING_ESTIMATE_WITH_UNCERTAINTY"
        },
        "4_motor_prototype_equivalence": {
            "question": "Is the physical prototype a real aircraft engine?",
            "answer": "NO. The physical benchtop hardware (ESP32 + ACS712 + 3x18650 + L298N + DC motor) is an electromechanical technology demonstrator. The Rotax 914 F aero-engine is modeled computationally. Missing aero-engine parameters (oil pressure, CHT, EGT, fuel flow) are NEVER fabricated for the motor prototype.",
            "status": "TESTBED_DEMONSTRATOR_NOT_FLIGHT_ENGINE"
        },
        "5_real_data": {
            "question": "What data is real?",
            "answer": "Real data comprises physical telemetry acquired live from the ESP32 prototype testbed: ACS712 current (A), battery bus voltage (V), optical/hall RPM pulse counts, thermistor temperature (°C), computed electrical power (W), and Wi-Fi link diagnostics.",
            "status": "PHYSICAL_SENSOR_TELEMETRY"
        },
        "6_simulated_data": {
            "question": "What data is simulated?",
            "answer": "Simulated data includes full-scale Rotax 914 F aerodynamic and thermodynamic mission trajectories, barometric altitude lapse profiles, and synthetic progressive mechanical bearing spalling / cylinder head overheat fault injection scenarios.",
            "status": "CALIBRATED_PHYSICS_SIMULATION"
        },
        "7_remaining_validation": {
            "question": "What remains to be validated?",
            "answer": "Future validation requirements: 1) Full-scale aero dynamometer ground test runs with calibrated physical wear; 2) Long-duration fleet run-to-failure teardown logs; 3) Dual-redundant CAN-bus / ARINC-429 avionics hardware-in-the-loop (HIL) rig integration; 4) DO-178C Level C software safety qualification.",
            "status": "PHASE_2_ROADMAP"
        }
    },

    "documented_limitations": [
        {
            "area": "Training & Degradation Data",
            "limitation": "Aero-engine degradation trajectories are generated via calibrated physics-informed simulation. While dynamic parameters match certified Rotax 914 specifications, empirical run-to-failure fleet records are required for production deployment.",
            "mitigation": "Modular model registry allows immediate drop-in replacement with dyno test-bench calibration weights."
        },
        {
            "area": "Physics Model Fidelity",
            "limitation": "The thermodynamic and mechanical models utilize 0-dimensional mean-value lumped parameter formulations rather than full 3D transient CFD/FEM solvers to achieve real-time 10Hz edge execution.",
            "mitigation": "Physics residual normalization and statistical filters compensate for high-order unmodeled dynamics."
        },
        {
            "area": "Sensor Redundancy",
            "limitation": "If all redundant sensors on a single physical channel fail concurrently, the system relies on state-estimation holdover which degrades after 30 seconds.",
            "mitigation": "Sensor Trust Engine explicitly transitions link and twin confidence to DEGRADED / DISCONNECTED."
        },
        {
            "area": "Instantaneous Foreign Object Damage",
            "limitation": "Sudden instantaneous catastrophic failures (e.g. bird strike, propeller blade loss) occur faster than predictive degradation velocity extrapolation.",
            "mitigation": "Threshold alarms and Isolation Forest immediately trigger emergency critical flags."
        }
    ],

    "validation_roadmap": [
        "Phase 1: Deterministic Physics Simulation & Benchmark Validation (COMPLETE)",
        "Phase 2: CAN-bus Hardware-In-The-Loop (HIL) Flight Log Replay (NEXT)",
        "Phase 3: Aero Engine Dynamometer Test-Bench Calibration",
        "Phase 4: Shadow-Mode Flight Testing on MALE UAV Airframe"
    ]
}
