import React, { useState } from 'react';
import { 
  Terminal, 
  Search, 
  Download, 
  Trash2, 
  Filter, 
  CheckCircle2 
} from 'lucide-react';
import { TelemetryLogEntry, Subsystem, LogLevel } from '../types/uav';
import { playTacticalClick } from '../utils/tacticalAudio';

interface TelemetryLogStreamProps {
  logs: TelemetryLogEntry[];
  onClearLogs: () => void;
}

export const TelemetryLogStream: React.FC<TelemetryLogStreamProps> = ({ logs, onClearLogs }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSubsystem, setSelectedSubsystem] = useState<Subsystem | 'ALL'>('ALL');
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  const filteredLogs = logs.filter((log) => {
    const matchesSubsystem = selectedSubsystem === 'ALL' || log.subsystem === selectedSubsystem;
    const matchesSearch =
      searchTerm === '' ||
      log.message.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.subsystem.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.level.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSubsystem && matchesSearch;
  });

  const handleExportJson = () => {
    playTacticalClick();
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(logs, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `DRDO_TAPAS_TELEMETRY_${Date.now()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();

    setDownloadSuccess(true);
    setTimeout(() => setDownloadSuccess(false), 2000);
  };

  const getLevelBadgeClass = (level: LogLevel) => {
    switch (level) {
      case 'EMERGENCY':
        return 'bg-[#EF4444]/20 text-[#EF4444] border border-[#EF4444]/50 font-bold';
      case 'WARNING':
        return 'bg-[#F59E0B]/20 text-[#F59E0B] border border-[#F59E0B]/50 font-bold';
      case 'CAUTION':
        return 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/50';
      case 'SUCCESS':
        return 'bg-[#10B981]/20 text-[#10B981] border border-[#10B981]/50';
      case 'INFO':
      default:
        return 'bg-[#00F2FF]/15 text-[#00F2FF] border border-[#00F2FF]/40';
    }
  };

  return (
    <div className="w-full h-full bg-[#070A0F] border border-[#1E2C3D] rounded-md p-2.5 flex flex-col font-mono text-xs select-none shadow-inner">
      {/* Header Bar */}
      <div className="flex items-center justify-between border-b border-[#1E2C3D] pb-2 mb-2">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-[#00F2FF]" />
          <span className="text-white font-bold text-[11px]">AUDIT TELEMETRY STREAM</span>
          <span className="text-[9px] px-1.5 py-0.2 bg-[#1E2C3D] text-slate-300 rounded font-semibold">
            {filteredLogs.length} EVENTS
          </span>
        </div>

        {/* Search & Export Actions */}
        <div className="flex items-center gap-2">
          {/* Search Box */}
          <div className="relative flex items-center">
            <Search className="w-3 h-3 text-slate-400 absolute left-2" />
            <input
              type="text"
              placeholder="Search audit logs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-[#0B111A] border border-[#1E2C3D] focus:border-[#00F2FF] text-white text-[10px] pl-6 pr-2 py-0.5 rounded outline-none w-36"
            />
          </div>

          {/* Subsystem Filters */}
          <div className="flex items-center gap-1">
            {(['ALL', 'NAV', 'AVIONICS', 'PAYLOAD', 'ATR', 'DATALINK'] as const).map((sub) => (
              <button
                key={sub}
                onClick={() => {
                  playTacticalClick();
                  setSelectedSubsystem(sub);
                }}
                className={`px-1.5 py-0.5 rounded text-[9px] transition-all ${
                  selectedSubsystem === sub
                    ? 'bg-[#00F2FF]/20 text-[#00F2FF] border border-[#00F2FF]/50 font-bold'
                    : 'text-slate-400 hover:text-white bg-[#0B111A] border border-[#1E2C3D]'
                }`}
              >
                {sub}
              </button>
            ))}
          </div>

          {/* Export JSON Button */}
          <button
            onClick={handleExportJson}
            className="px-2 py-0.5 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#00F2FF]/40 text-[#00F2FF] rounded text-[10px] font-bold flex items-center gap-1 transition-all"
          >
            {downloadSuccess ? (
              <>
                <CheckCircle2 className="w-3 h-3 text-[#10B981]" />
                <span className="text-[#10B981]">EXPORTED</span>
              </>
            ) : (
              <>
                <Download className="w-3 h-3" />
                <span>JSON</span>
              </>
            )}
          </button>

          <button
            onClick={() => {
              playTacticalClick();
              onClearLogs();
            }}
            title="Clear Log Stream"
            className="p-1 bg-[#0B111A] hover:bg-[#1E2C3D] text-slate-400 hover:text-white rounded border border-[#1E2C3D]"
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Terminal Log Output Window */}
      <div className="flex-1 bg-[#040609] border border-[#1E2C3D] rounded p-2 overflow-y-auto space-y-1 font-mono text-[10px]">
        {filteredLogs.length === 0 ? (
          <div className="text-center text-slate-500 py-6">NO LOG ENTRIES MATCH CURRENT FILTER CRITERIA</div>
        ) : (
          filteredLogs.map((log) => (
            <div
              key={log.id}
              className="flex items-start gap-2 hover:bg-[#0B111A]/80 p-1 rounded transition-all leading-tight border-b border-[#111A26]"
            >
              {/* Timestamp */}
              <span className="text-slate-500 whitespace-nowrap text-[9px]">{log.timestamp}</span>

              {/* Level Badge */}
              <span className={`px-1 py-0.2 rounded text-[8px] whitespace-nowrap ${getLevelBadgeClass(log.level)}`}>
                {log.level}
              </span>

              {/* Subsystem */}
              <span className="text-slate-400 font-bold whitespace-nowrap text-[9px]">[{log.subsystem}]</span>

              {/* Message */}
              <span className="text-slate-200 flex-1">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
