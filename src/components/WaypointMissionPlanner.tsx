import React, { useState } from 'react';
import { 
  X, 
  Route, 
  CheckCircle2, 
  AlertTriangle, 
  Trash2, 
  Plus, 
  Navigation, 
  Gauge, 
  Mountain, 
  Fuel, 
  Clock 
} from 'lucide-react';
import { Waypoint } from '../types/uav';
import { playTacticalClick } from '../utils/tacticalAudio';

interface WaypointMissionPlannerProps {
  waypoints: Waypoint[];
  onUpdateWaypoints: (waypoints: Waypoint[]) => void;
  onClose: () => void;
}

export const WaypointMissionPlanner: React.FC<WaypointMissionPlannerProps> = ({
  waypoints,
  onUpdateWaypoints,
  onClose,
}) => {
  const [localWaypoints, setLocalWaypoints] = useState<Waypoint[]>([...waypoints]);

  // Calculate mission metrics
  const totalDistanceKm = localWaypoints.length * 34.5;
  const avgSpeedKts = localWaypoints.reduce((acc, wp) => acc + wp.speedKts, 0) / (localWaypoints.length || 1);
  const totalTimeMin = (totalDistanceKm / (avgSpeedKts * 1.852)) * 60;
  const estimatedFuelBurnLiters = (totalTimeMin / 60) * 22.4;
  const terrainSafe = localWaypoints.every((wp) => wp.altFt > wp.demElevationFt + 2000);

  const handleAltChange = (id: string, newAlt: number) => {
    setLocalWaypoints((prev) =>
      prev.map((wp) => (wp.id === id ? { ...wp, altFt: newAlt } : wp))
    );
  };

  const handleSpeedChange = (id: string, newSpeed: number) => {
    setLocalWaypoints((prev) =>
      prev.map((wp) => (wp.id === id ? { ...wp, speedKts: newSpeed } : wp))
    );
  };

  const handleActionChange = (id: string, newAction: Waypoint['action']) => {
    setLocalWaypoints((prev) =>
      prev.map((wp) => (wp.id === id ? { ...wp, action: newAction } : wp))
    );
  };

  const handleDelete = (id: string) => {
    playTacticalClick();
    setLocalWaypoints((prev) => prev.filter((wp) => wp.id !== id).map((wp, i) => ({ ...wp, index: i + 1 })));
  };

  const handleAddWaypoint = () => {
    playTacticalClick();
    const lastWp = localWaypoints[localWaypoints.length - 1];
    const newWp: Waypoint = {
      id: `WP_NEW_${Date.now()}`,
      index: localWaypoints.length + 1,
      name: `WP-0${localWaypoints.length + 1} PATROL WAYPOINT`,
      lat: lastWp ? lastWp.lat + 0.05 : 34.2,
      lng: lastWp ? lastWp.lng + 0.05 : 77.8,
      altFt: 24000,
      speedKts: 125,
      action: 'SURVEILLANCE',
      demElevationFt: 14200,
      passed: false,
    };
    setLocalWaypoints((prev) => [...prev, newWp]);
  };

  const handleSaveAndUpload = () => {
    playTacticalClick();
    onUpdateWaypoints(localWaypoints);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 select-none">
      <div className="bg-[#0B111A] border border-[#00F2FF]/50 rounded-lg w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden font-mono">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#070A0F] border-b border-[#1E2C3D]">
          <div className="flex items-center gap-2">
            <Route className="w-4 h-4 text-[#00F2FF]" />
            <span className="text-white font-bold text-sm">MISSION FLIGHT PLANNER & DEM CLEARANCE</span>
            <span className="text-[10px] px-2 py-0.5 bg-[#1E2C3D] text-[#00F2FF] rounded font-semibold">
              STANAG 4586 ROUTE MATRIX
            </span>
          </div>
          <button
            onClick={() => {
              playTacticalClick();
              onClose();
            }}
            className="p-1 text-slate-400 hover:text-white rounded hover:bg-[#1E2C3D]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Mission Summary Metrics Ribbon */}
        <div className="grid grid-cols-4 gap-3 p-3 bg-[#070A0F]/60 border-b border-[#1E2C3D] text-xs">
          <div className="bg-[#111A26] p-2 rounded border border-[#1E2C3D] flex items-center gap-2.5">
            <Navigation className="w-4 h-4 text-[#00F2FF]" />
            <div>
              <div className="text-[9px] text-slate-400">TOTAL DISTANCE</div>
              <div className="font-bold text-white text-sm">{totalDistanceKm.toFixed(1)} km</div>
            </div>
          </div>

          <div className="bg-[#111A26] p-2 rounded border border-[#1E2C3D] flex items-center gap-2.5">
            <Clock className="w-4 h-4 text-[#38BDF8]" />
            <div>
              <div className="text-[9px] text-slate-400">ESTIMATED TIME (ETE)</div>
              <div className="font-bold text-white text-sm">{totalTimeMin.toFixed(0)} min</div>
            </div>
          </div>

          <div className="bg-[#111A26] p-2 rounded border border-[#1E2C3D] flex items-center gap-2.5">
            <Fuel className="w-4 h-4 text-[#F59E0B]" />
            <div>
              <div className="text-[9px] text-slate-400">TOTAL FUEL BURN</div>
              <div className="font-bold text-white text-sm">{estimatedFuelBurnLiters.toFixed(1)} L</div>
            </div>
          </div>

          <div className="bg-[#111A26] p-2 rounded border border-[#1E2C3D] flex items-center gap-2.5">
            <Mountain className={`w-4 h-4 ${terrainSafe ? 'text-[#10B981]' : 'text-[#EF4444]'}`} />
            <div>
              <div className="text-[9px] text-slate-400">DEM TERRAIN CLEARANCE</div>
              <div className={`font-bold text-xs ${terrainSafe ? 'text-[#10B981]' : 'text-[#EF4444]'}`}>
                {terrainSafe ? 'ALL WPS SAFE (>2k FT)' : 'TERRAIN WARNING!'}
              </div>
            </div>
          </div>
        </div>

        {/* Waypoints Table */}
        <div className="flex-1 overflow-y-auto p-3">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-[#1E2C3D] text-[10px] text-slate-400 uppercase">
                <th className="pb-2">Idx</th>
                <th className="pb-2">Waypoint Name</th>
                <th className="pb-2">Coordinates</th>
                <th className="pb-2">Altitude (MSL)</th>
                <th className="pb-2">Speed (IAS)</th>
                <th className="pb-2">Action / Mode</th>
                <th className="pb-2">DEM Ground</th>
                <th className="pb-2 text-right">Delete</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1E2C3D]">
              {localWaypoints.map((wp) => {
                const isClear = wp.altFt >= wp.demElevationFt + 2000;

                return (
                  <tr key={wp.id} className="hover:bg-[#111A26]/50 transition-all">
                    <td className="py-2.5 text-[#00F2FF] font-bold">WP-{wp.index}</td>
                    <td className="py-2.5 text-white font-semibold">{wp.name}</td>
                    <td className="py-2.5 text-slate-300 text-[10px]">
                      {wp.lat.toFixed(4)}°N, {wp.lng.toFixed(4)}°E
                    </td>
                    <td className="py-2.5">
                      <input
                        type="number"
                        step="500"
                        value={wp.altFt}
                        onChange={(e) => handleAltChange(wp.id, parseInt(e.target.value) || 10000)}
                        className="bg-[#070A0F] border border-[#1E2C3D] px-2 py-0.5 rounded text-white text-xs w-24"
                      />
                      <span className="text-[9px] text-slate-400 ml-1">FT</span>
                    </td>
                    <td className="py-2.5">
                      <input
                        type="number"
                        step="5"
                        value={wp.speedKts}
                        onChange={(e) => handleSpeedChange(wp.id, parseInt(e.target.value) || 80)}
                        className="bg-[#070A0F] border border-[#1E2C3D] px-2 py-0.5 rounded text-white text-xs w-20"
                      />
                      <span className="text-[9px] text-slate-400 ml-1">KT</span>
                    </td>
                    <td className="py-2.5">
                      <select
                        value={wp.action}
                        onChange={(e) => handleActionChange(wp.id, e.target.value as Waypoint['action'])}
                        className="bg-[#070A0F] border border-[#1E2C3D] px-2 py-0.5 rounded text-white text-xs"
                      >
                        <option value="FLYOVER">FLYOVER</option>
                        <option value="SURVEILLANCE">SURVEILLANCE</option>
                        <option value="LOITER">LOITER</option>
                        <option value="STRIKE_COORDINATE">STRIKE</option>
                        <option value="TOUCHDOWN">TOUCHDOWN</option>
                      </select>
                    </td>
                    <td className="py-2.5">
                      <span className={`text-[10px] ${isClear ? 'text-[#10B981]' : 'text-[#EF4444] font-bold'}`}>
                        {wp.demElevationFt.toLocaleString()} FT {isClear ? '✓' : '⚠'}
                      </span>
                    </td>
                    <td className="py-2.5 text-right">
                      <button
                        onClick={() => handleDelete(wp.id)}
                        className="p-1 text-slate-400 hover:text-[#EF4444] hover:bg-[#1E2C3D] rounded"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#070A0F] border-t border-[#1E2C3D]">
          <button
            onClick={handleAddWaypoint}
            className="px-3 py-1.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#00F2FF]/40 text-[#00F2FF] rounded text-xs font-bold flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>ADD WAYPOINT</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                playTacticalClick();
                onClose();
              }}
              className="px-3 py-1.5 bg-[#111A26] hover:bg-[#1E2C3D] text-slate-300 rounded text-xs"
            >
              CANCEL
            </button>
            <button
              onClick={handleSaveAndUpload}
              className="px-4 py-1.5 bg-[#00F2FF] hover:bg-[#00D8E6] text-black rounded text-xs font-bold shadow-[0_0_12px_rgba(0,242,255,0.4)] flex items-center gap-1.5"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>UPLOAD FLIGHT PLAN TO UAV FCS</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
