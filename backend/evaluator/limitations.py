"""
System Limitations & Engineering Disclosures for AERIS-TWIN
Explicitly documents technical scope, model assumptions, and validation roadmap.
"""
from typing import Dict, Any, List

SYSTEM_LIMITATIONS = {
    "system_name": "AERIS-TWIN Digital Twin Intelligence Layer",
    "version": "2.4.0-ResearchPrototype",
    "airworthiness_status": "PROTOTYPE_DECISION_SUPPORT_ONLY",
    "flight_criticality": "NON_FLIGHT_CRITICAL_ADVISORY",
    "critical_safety_rule": "AERIS-TWIN provides predictive health advisories to UAV operators and supervisory systems. It MUST NOT directly command flight controls, engine throttles, or autopilot actuation.",
    "documented_limitations": [
        {
            "area": "Training & Degradation Data",
            "limitation": "Degradation trajectories are generated via calibrated physics-informed simulation. While dynamic parameters match certified Rotax 914 specs, empirical run-to-failure fleet data is required for production certification.",
            "mitigation": "Modular model registry allows immediate drop-in replacement with dyno test-bench weights."
        },
        {
            "area": "Physics Model Fidelity",
            "limitation": "The thermodynamic and mechanical models utilize 0-dimensional mean-value formulations rather than full 3D finite-element or CFD fluid solvers to achieve real-time 10Hz edge execution.",
            "mitigation": "Residual normalization and statistical filters compensate for high-order unmodeled dynamics."
        },
        {
            "area": "Sensor Redundancy",
            "limitation": "If all redundant sensors on a single physical channel (e.g. all oil pressure transducers) fail concurrently, the system relies on state-estimation holdover which degrades after 30 seconds.",
            "mitigation": "Sensor Trust Engine explicitly transitions link and twin confidence to DEGRADED/DISCONNECTED."
        },
        {
            "area": "Unmodeled Foreign Object Damage",
            "limitation": "Sudden instantaneous catastrophic failures (e.g. bird strike, propeller blade loss) occur faster than predictive degradation modeling.",
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
