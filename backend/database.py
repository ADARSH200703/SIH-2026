"""
SQLite Database Layer for AERIS-TWIN
Implements all 26 tables for full auditability, time-series telemetry,
state tracking, experiments, model registries, and evaluator evidence.
"""
import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

DB_PATH = Path(__file__).parent / "aeris_twin.db"

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Engines
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS engines (
            engine_id TEXT PRIMARY KEY,
            model_name TEXT,
            displacement_cc REAL,
            rated_power_hp REAL,
            max_rpm REAL,
            cooling_type TEXT,
            manufacture_date TEXT,
            total_flight_hours REAL
        )
    """)

    # 2. Engine Configurations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS engine_configurations (
            config_id TEXT PRIMARY KEY,
            engine_id TEXT,
            bore_mm REAL,
            stroke_mm REAL,
            compression_ratio REAL,
            oil_nominal_bar REAL,
            cht_nominal_c REAL,
            vibration_nominal_mms REAL,
            created_at REAL
        )
    """)

    # 3. UAVs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS uavs (
            uav_id TEXT PRIMARY KEY,
            model TEXT,
            class TEXT,
            max_takeoff_weight_kg REAL,
            service_ceiling_ft REAL,
            endurance_hours REAL
        )
    """)

    # 4. Missions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            mission_id TEXT PRIMARY KEY,
            uav_id TEXT,
            engine_id TEXT,
            start_time REAL,
            planned_duration_hours REAL,
            target_altitude_ft REAL,
            status TEXT
        )
    """)

    # 5. Telemetry Time-Series
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            sequence_number INTEGER,
            engine_id TEXT,
            mission_id TEXT,
            rpm REAL,
            throttle REAL,
            map_kpa REAL,
            fuel_flow REAL,
            egt_c REAL,
            cht_c REAL,
            oil_pressure_bar REAL,
            oil_temperature_c REAL,
            vibration_mms REAL,
            engine_load REAL,
            altitude_ft REAL,
            airspeed_kts REAL,
            ambient_temperature_c REAL,
            ambient_pressure_kpa REAL,
            power_setting REAL,
            flight_phase TEXT,
            source TEXT
        )
    """)

    # 6. Sensor Health & Trust
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            engine_id TEXT,
            sensor_name TEXT,
            status TEXT,
            trust_score REAL,
            confidence REAL,
            reason TEXT
        )
    """)

    # 7. Physics Predictions (Mean-Value Expected)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS physics_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            engine_id TEXT,
            exp_rpm REAL,
            exp_map_kpa REAL,
            exp_fuel_flow REAL,
            exp_egt_c REAL,
            exp_cht_c REAL,
            exp_oil_pressure_bar REAL,
            exp_oil_temperature_c REAL,
            exp_vibration_mms REAL,
            model_assumptions TEXT
        )
    """)

    # 8. Residuals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS residuals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            engine_id TEXT,
            parameter TEXT,
            measured REAL,
            expected REAL,
            residual REAL,
            normalized_residual REAL,
            rolling_mean REAL,
            rolling_std REAL,
            residual_slope REAL,
            trend TEXT
        )
    """)

    # 9. Twin States
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS twin_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            engine_id TEXT,
            operating_state_json TEXT,
            thermal_state_json TEXT,
            mechanical_state_json TEXT,
            combustion_state_json TEXT,
            lubrication_state_json TEXT,
            degradation_state_json TEXT,
            overall_confidence REAL
        )
    """)

    # 10. Degradation States
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS degradation_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            engine_id TEXT,
            total_degradation REAL,
            bearing_degradation REAL,
            thermal_degradation REAL,
            combustion_degradation REAL,
            lubrication_degradation REAL,
            degradation_velocity REAL,
            velocity_trend TEXT
        )
    """)

    # 11. Health States
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_states (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            engine_id TEXT,
            health_index REAL,
            normalized_degradation REAL,
            confidence REAL,
            interpretation TEXT
        )
    """)

    # 12. Fault Predictions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fault_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            engine_id TEXT,
            fault_class TEXT,
            probability REAL,
            confidence REAL,
            severity TEXT,
            evidence_json TEXT
        )
    """)

    # 13. RUL Predictions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rul_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            engine_id TEXT,
            rul_estimate_hours REAL,
            lower_bound_hours REAL,
            upper_bound_hours REAL,
            confidence REAL,
            degradation_velocity REAL,
            endpoint_definition TEXT,
            model_validity TEXT
        )
    """)

    # 14. Mission Risk
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mission_risk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            engine_id TEXT,
            mission_id TEXT,
            risk_index REAL,
            completion_probability REAL,
            confidence REAL,
            risk_factors_json TEXT
        )
    """)

    # 15. Mission Scenarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mission_scenarios (
            scenario_id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            initial_parameters_json TEXT
        )
    """)

    # 16. Mission Decisions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mission_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            engine_id TEXT,
            decision TEXT,
            reason TEXT,
            risk_before REAL,
            risk_after REAL,
            confidence REAL,
            evidence_json TEXT
        )
    """)

    # 17. Simulation Runs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_runs (
            run_id TEXT PRIMARY KEY,
            seed INTEGER,
            scenario TEXT,
            parameters_json TEXT,
            start_timestamp REAL,
            end_timestamp REAL
        )
    """)

    # 18. Fault Injections
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fault_injections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            fault_type TEXT,
            severity REAL,
            start_time_offset REAL,
            progression_rate REAL,
            injected_at REAL
        )
    """)

    # 19. Replay Sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS replay_sessions (
            session_id TEXT PRIMARY KEY,
            source_dataset TEXT,
            current_frame INTEGER,
            total_frames INTEGER,
            status TEXT,
            created_at REAL
        )
    """)

    # 20. Experiments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            experiment_id TEXT PRIMARY KEY,
            dataset_version TEXT,
            engine_configuration TEXT,
            simulation_seed INTEGER,
            scenario TEXT,
            model_versions TEXT,
            parameters_json TEXT,
            timestamp REAL
        )
    """)

    # 21. Experiment Metrics
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS experiment_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id TEXT,
            system_type TEXT, -- AERIS_TWIN vs THRESHOLD_BASELINE
            accuracy REAL,
            precision_score REAL,
            recall_score REAL,
            f1_score REAL,
            false_positive_rate REAL,
            false_negative_rate REAL,
            detection_delay_sec REAL,
            rul_mae_hours REAL,
            rul_rmse_hours REAL,
            prediction_interval_coverage REAL
        )
    """)

    # 22. Model Registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS model_registry (
            model_id TEXT PRIMARY KEY,
            model_name TEXT,
            model_type TEXT,
            version TEXT,
            trained_on_dataset TEXT,
            hyperparameters_json TEXT,
            created_at REAL
        )
    """)

    # 23. Dataset Registry
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dataset_registry (
            dataset_id TEXT PRIMARY KEY,
            name TEXT,
            version TEXT,
            total_trajectories INTEGER,
            train_split_pct REAL,
            val_split_pct REAL,
            test_split_pct REAL,
            description TEXT
        )
    """)

    # 24. Evidence Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            engine_id TEXT,
            entity_type TEXT, -- FAULT, HEALTH, RUL, RISK, DECISION
            evidence_type TEXT,
            parameter TEXT,
            observation TEXT,
            confidence REAL,
            details_json TEXT
        )
    """)

    # 25. Evaluator Questions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS evaluator_questions (
            question_id TEXT PRIMARY KEY,
            category TEXT,
            question TEXT,
            answer TEXT,
            technical_evidence_json TEXT,
            related_modules_json TEXT,
            demo_action TEXT,
            limitations_json TEXT
        )
    """)

    # 26. System Events & Audit Integrity
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            time_str TEXT,
            level TEXT,
            component TEXT,
            message TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS data_integrity_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            sequence_number INTEGER,
            engine_id TEXT,
            checksum TEXT,
            integrity_status TEXT
        )
    """)

    # Seed core metadata
    _seed_initial_data(cursor)

    conn.commit()
    conn.close()

def _seed_initial_data(cursor: sqlite3.Cursor):
    # Seed Engine & Configuration
    cursor.execute("""
        INSERT OR IGNORE INTO engines (
            engine_id, model_name, displacement_cc, rated_power_hp, max_rpm, cooling_type, manufacture_date, total_flight_hours
        ) VALUES ('UAV-ENG-ROT-914-01', 'Rotax 914 F Aero Turbo Piston', 1211.2, 115.0, 5800.0, 'Liquid/Air Hybrid', '2025-06-15', 142.5)
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO engine_configurations (
            config_id, engine_id, bore_mm, stroke_mm, compression_ratio, oil_nominal_bar, cht_nominal_c, vibration_nominal_mms, created_at
        ) VALUES ('CFG-ROT914-001', 'UAV-ENG-ROT-914-01', 79.5, 61.0, 9.0, 4.3, 78.4, 1.6, 1772900000.0)
    """)

    # Seed UAV & Mission
    cursor.execute("""
        INSERT OR IGNORE INTO uavs (
            uav_id, model, class, max_takeoff_weight_kg, service_ceiling_ft, endurance_hours
        ) VALUES ('MALE-UAV-TAPAS-04', 'TAPAS-BH-201 MALE UAV', 'Tactical Long Endurance', 1800.0, 30000.0, 24.0)
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO missions (
            mission_id, uav_id, engine_id, start_time, planned_duration_hours, target_altitude_ft, status
        ) VALUES ('MSN-2026-SURV-082', 'MALE-UAV-TAPAS-04', 'UAV-ENG-ROT-914-01', 1772901000.0, 6.0, 15000.0, 'ACTIVE')
    """)

    # Seed Model Registry
    models = [
        ('MOD-MV-PHYS-01', 'AeroPistonMeanValuePhysics', 'Physics', 'v1.8.2', 'N/A (Thermodynamic Formulation)', '{"bore": 79.5, "stroke": 61.0, "displacement": 1.211}'),
        ('MOD-IF-ANOM-01', 'IsolationForestResidualDetector', 'Anomaly Detection', 'v2.1.0', 'UAV-ROT914-SIM-CORPUS-2026.1', '{"n_estimators": 100, "contamination": 0.05}'),
        ('MOD-GBM-FLT-01', 'GradientBoostingFaultClassifier', 'Fault Classification', 'v2.4.0', 'UAV-ROT914-SIM-CORPUS-2026.1', '{"n_estimators": 80, "max_depth": 4, "learning_rate": 0.1}'),
        ('MOD-RUL-TRAJ-01', 'PolynomialDegradationRUL', 'Prognostics', 'v1.5.0', 'UAV-ROT914-SIM-CORPUS-2026.1', '{"endpoint_deg": 0.75, "min_window": 30}')
    ]
    for m in models:
        cursor.execute("""
            INSERT OR IGNORE INTO model_registry (
                model_id, model_name, model_type, version, trained_on_dataset, hyperparameters_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (*m, time.time()))

    # Seed Dataset Registry
    cursor.execute("""
        INSERT OR IGNORE INTO dataset_registry (
            dataset_id, name, version, total_trajectories, train_split_pct, val_split_pct, test_split_pct, description
        ) VALUES ('UAV-ROT914-SIM-CORPUS-2026.1', 'MALE UAV Aero Piston Multi-Mission Trajectory Corpus', '2026.1', 120, 70.0, 15.0, 15.0,
        'Physics-grounded trajectory splits separated by engine flight runs without row-level leakage.')
    """)

def log_event(message: str, level: str = "info", component: str = "System"):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        time_str = time.strftime("%H:%M:%S")
        cursor.execute("""
            INSERT INTO system_events (timestamp, time_str, level, component, message)
            VALUES (?, ?, ?, ?, ?)
        """, (time.time(), time_str, level, component, message))
        conn.commit()
        conn.close()
    except Exception:
        pass

def log_telemetry_packet(data: Dict[str, Any]):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO telemetry (
                timestamp, sequence_number, engine_id, mission_id,
                rpm, throttle, map_kpa, fuel_flow, egt_c, cht_c,
                oil_pressure_bar, oil_temperature_c, vibration_mms,
                engine_load, altitude_ft, airspeed_kts, ambient_temperature_c,
                ambient_pressure_kpa, power_setting, flight_phase, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("timestamp", time.time()),
            data.get("sequence_number", 0),
            data.get("engine_id", "UAV-ENG-ROT-914-01"),
            data.get("mission_id", "MSN-2026-SURV-082"),
            data.get("rpm", 4215.0),
            data.get("throttle", 68.0),
            data.get("map_kpa", 96.4),
            data.get("fuel_flow", 5.2),
            data.get("egt_c", 645.0),
            data.get("cht_c", 78.4),
            data.get("oil_pressure_bar", 4.3),
            data.get("oil_temperature_c", 82.1),
            data.get("vibration_mms", 1.6),
            data.get("engine_load", 62.0),
            data.get("altitude_ft", 15000.0),
            data.get("airspeed_kts", 85.0),
            data.get("ambient_temperature_c", -14.5),
            data.get("ambient_pressure_kpa", 57.2),
            data.get("power_setting", 0.72),
            data.get("flight_phase", "CRUISE"),
            data.get("source", "SIMULATOR")
        ))
        conn.commit()
        conn.close()
    except Exception:
        pass

def log_twin_execution(engine_id: str, twin_state: Dict[str, Any], evidence_items: List[Dict[str, Any]]):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        now = time.time()
        
        # Log Twin state snapshot
        cursor.execute("""
            INSERT INTO twin_states (
                timestamp, engine_id, operating_state_json, thermal_state_json,
                mechanical_state_json, combustion_state_json, lubrication_state_json,
                degradation_state_json, overall_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now, engine_id,
            json.dumps(twin_state.get("operating_state", {})),
            json.dumps(twin_state.get("thermal_state", {})),
            json.dumps(twin_state.get("mechanical_state", {})),
            json.dumps(twin_state.get("combustion_state", {})),
            json.dumps(twin_state.get("lubrication_state", {})),
            json.dumps(twin_state.get("degradation_state", {})),
            twin_state.get("confidence", {}).get("overall", 0.9)
        ))
        
        # Log Evidence
        for ev in evidence_items:
            cursor.execute("""
                INSERT INTO evidence (
                    timestamp, engine_id, entity_type, evidence_type, parameter, observation, confidence, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now, engine_id,
                ev.get("entity_type", "TWIN"),
                ev.get("type", "UNKNOWN"),
                ev.get("parameter", ""),
                ev.get("observation", ""),
                ev.get("confidence", 1.0),
                json.dumps(ev.get("details", {}))
            ))
            
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_recent_telemetry_rows(limit: int = 60) -> List[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM telemetry ORDER BY id DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows[::-1]
    except Exception:
        return []
