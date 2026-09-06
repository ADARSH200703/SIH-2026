"""
Deterministic Replay Engine for AERIS-TWIN
Allows deterministic frame-by-frame replay of saved flight trajectories
through the complete live AERIS-TWIN intelligence and evidence pipeline.
"""
from typing import Dict, Any, List, Optional
import time
import numpy as np

class ReplayEngine:
    def __init__(self, twin_service=None):
        self.twin_service = twin_service
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 120
        self.playback_speed = 1.0
        self.trajectory_buffer: List[Dict[str, Any]] = []
        self._generate_default_evaluator_trajectory()

    def _generate_default_evaluator_trajectory(self, seed: int = 42):
        """
        Generates the standard 120-frame SIH evaluator scenario:
        0..35: Healthy Cruise
        36..120: Progressive Crankshaft Bearing Degradation
        """
        np.random.seed(seed)
        self.trajectory_buffer.clear()
        
        for t in range(120):
            is_fault = (t >= 36)
            vib_val = 1.60 + (0.042 * (t - 36) if is_fault else 0.0) + np.random.normal(0, 0.04)
            temp_val = 78.4 + (0.05 * (t - 36) if is_fault else 0.0) + np.random.normal(0, 0.3)
            oil_val = 4.30 - (0.008 * (t - 36) if is_fault else 0.0) + np.random.normal(0, 0.02)
            
            frame = {
                "engine_id": "UAV-ENG-ROT-914-01",
                "uav_id": "MALE-UAV-TAPAS-04",
                "mission_id": "MSN-2026-SURV-082",
                "timestamp": 1772900000.0 + t,
                "sequence_number": t,
                "flight_time_seconds": 9918 + t,
                "rpm": 4215.0 + np.random.normal(0, 8),
                "throttle": 68.0,
                "temperature": round(float(temp_val), 2),
                "oilPressure": round(float(oil_val), 2),
                "vibration": round(float(vib_val), 2),
                "fuelFlow": 5.2 + np.random.normal(0, 0.04),
                "engineLoad": 62.0,
                "altitude_ft": 15000.0,
                "ambient_temperature_c": -14.5,
                "source": "REPLAY"
            }
            self.trajectory_buffer.append(frame)
            
        self.total_frames = len(self.trajectory_buffer)
        self.current_frame = 0

    def start(self) -> Dict[str, Any]:
        self.is_playing = True
        return self.get_state()

    def pause(self) -> Dict[str, Any]:
        self.is_playing = False
        return self.get_state()

    def reset(self) -> Dict[str, Any]:
        self.is_playing = False
        self.current_frame = 0
        return self.get_state()

    def step(self) -> Optional[Dict[str, Any]]:
        """
        Advances replay by 1 frame and feeds it through TwinUpdateService.
        """
        if self.current_frame >= self.total_frames:
            self.is_playing = False
            return None
            
        frame = self.trajectory_buffer[self.current_frame]
        self.current_frame += 1
        
        if self.twin_service:
            twin_result = self.twin_service.process_telemetry_frame(frame)
            return twin_result
        return frame

    def get_state(self) -> Dict[str, Any]:
        return {
            "session_id": "REPLAY-SES-EVALUATOR-01",
            "is_playing": self.is_playing,
            "current_frame": self.current_frame,
            "total_frames": self.total_frames,
            "playback_speed": self.playback_speed,
            "scenario": "Progressive Bearing Degradation Evaluator Walkthrough"
        }
