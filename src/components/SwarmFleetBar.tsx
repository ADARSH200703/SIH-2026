import React from 'react';
import { Plane, Shield, Wifi, Fuel, Gauge, Navigation } from 'lucide-react';
import { FleetUav } from '../types/uav';
import { playTacticalClick } from '../utils/tacticalAudio';

interface SwarmFleetBarProps {
  fleet: FleetUav[];
  activeUavId: string;
  onSelectUav: (uavId: string) => void;
}

export const SwarmFleetBar: React.FC<SwarmFleetBarProps> = ({
  fleet,
  activeUavId,
  onSelectUav,
}) => {
  return (
    <div className="w-full bg-[#070A0F] border-b border-[#1E2C3D] px-3 py-1 flex items-center justify-between text-xs select-none">
      {/* Formation Ribbon Left Label */}
      <div className="flex items-center gap-2 pr-3 border-r border-[#1E2C3D]">
        <div className="w-2 h-2 rounded-full bg-[#00F2FF] animate-ping" />
        <span className="font-mono text-[10px] text-slate-400 font-bold uppercase tracking-wider">
          SQUADRON FORMATION DLI:
        </span>
      </div>

      {/* Fleet UAV Cards Matrix */}
      <div className="flex-1 flex items-center gap-2 px-3 overflow-x-auto">
        {fleet.map((uav) => {
          const isActive = uav.id === activeUavId;
          const flNumber = Math.round(uav.altFt / 100);

          return (
            <button
              key={uav.id}
              onClick={() => {
                playTacticalClick();
                onSelectUav(uav.id);
              }}
              className={`flex items-center gap-3 px-3 py-1 rounded transition-all text-left ${
                isActive
                  ? 'bg-[#111A26] border border-[#00F2FF] shadow-[0_0_12px_rgba(0,242,255,0.25)] ring-1 ring-[#00F2FF]/40'
                  : 'bg-[#0B111A] border border-[#1E2C3D] hover:border-[#2A3E54] hover:bg-[#111A26]/60 opacity-80 hover:opacity-100'
              }`}
            >
              {/* Aircraft Icon & Callsign */}
              <div className="flex items-center gap-1.5">
                <div
                  className={`p-1 rounded ${
                    isActive ? 'bg-[#00F2FF]/20 text-[#00F2FF]' : 'bg-[#1E2C3D] text-slate-400'
                  }`}
                >
                  <Plane className="w-3.5 h-3.5 transform -rotate-45" />
                </div>
                <div>
                  <div className="flex items-center gap-1">
                    <span className="font-bold text-[11px] text-white tracking-wide">{uav.callsign}</span>
                    {uav.isLeader && (
                      <span className="text-[8px] font-mono px-1 py-0.2 bg-[#00F2FF]/20 text-[#00F2FF] border border-[#00F2FF]/40 rounded font-semibold">
                        PRIMARY DLI
                      </span>
                    )}
                  </div>
                  <div className="text-[9px] text-slate-400 font-mono">{uav.model}</div>
                </div>
              </div>

              {/* Status Telemetry Pills */}
              <div className="flex items-center gap-2 border-l border-[#1E2C3D] pl-2.5 font-mono text-[10px]">
                {/* Altitude FL */}
                <div className="flex items-center gap-1 text-slate-300">
                  <Navigation className="w-3 h-3 text-[#38BDF8]" />
                  <span className="font-bold text-[#38BDF8]">FL{flNumber}</span>
                </div>

                {/* Airspeed */}
                <div className="flex items-center gap-1 text-slate-300">
                  <Gauge className="w-3 h-3 text-[#10B981]" />
                  <span>{uav.speedKts} KT</span>
                </div>

                {/* Fuel Mini-Bar */}
                <div className="flex items-center gap-1 text-slate-300">
                  <Fuel className="w-3 h-3 text-[#F59E0B]" />
                  <div className="w-10 h-1.5 bg-[#1E2C3D] rounded-full overflow-hidden flex">
                    <div
                      className={`h-full ${
                        uav.fuelPct > 35 ? 'bg-[#10B981]' : uav.fuelPct > 20 ? 'bg-[#F59E0B]' : 'bg-[#EF4444]'
                      }`}
                      style={{ width: `${uav.fuelPct}%` }}
                    />
                  </div>
                  <span className="text-[9px] text-slate-400">{Math.round(uav.fuelPct)}%</span>
                </div>

                {/* Datalink */}
                <div className="flex items-center gap-1 text-slate-300">
                  <Wifi className="w-3 h-3 text-[#00F2FF]" />
                  <span className="text-[#00F2FF] font-semibold">{uav.linkStrengthPct.toFixed(0)}%</span>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Autonomous Swarm Formation Mode Indicator */}
      <div className="hidden lg:flex items-center gap-2 pl-3 border-l border-[#1E2C3D] font-mono text-[10px]">
        <Shield className="w-3.5 h-3.5 text-[#10B981]" />
        <span className="text-slate-400">SWARM SYNC:</span>
        <span className="text-[#10B981] font-bold tracking-wider">MESH_ENCRYPTED_256</span>
      </div>
    </div>
  );
};
