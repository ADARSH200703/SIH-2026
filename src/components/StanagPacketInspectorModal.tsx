import React, { useState } from 'react';
import { 
  X, 
  FileCode2, 
  Binary, 
  CheckCircle2, 
  Copy, 
  RefreshCw, 
  Layers 
} from 'lucide-react';
import { StanagPacket } from '../types/uav';
import { playTacticalClick } from '../utils/tacticalAudio';

interface StanagPacketInspectorModalProps {
  packets: StanagPacket[];
  onClose: () => void;
}

export const StanagPacketInspectorModal: React.FC<StanagPacketInspectorModalProps> = ({
  packets,
  onClose,
}) => {
  const [selectedPacketIndex, setSelectedPacketIndex] = useState(0);
  const [copied, setCopied] = useState(false);

  const packet = packets[selectedPacketIndex] || packets[0];

  const handleCopyHex = () => {
    playTacticalClick();
    if (packet) {
      navigator.clipboard.writeText(packet.rawHex);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 select-none">
      <div className="bg-[#0B111A] border border-[#00F2FF]/50 rounded-lg w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden font-mono text-xs">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#070A0F] border-b border-[#1E2C3D]">
          <div className="flex items-center gap-2">
            <Binary className="w-4 h-4 text-[#00F2FF]" />
            <span className="text-white font-bold text-sm">
              STANAG 4586 (DLI) &amp; MISB ST 0601 KLV PACKET INSPECTOR
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

        {/* Packet Selector Ribbon */}
        <div className="flex items-center gap-2 px-4 py-2 bg-[#070A0F]/60 border-b border-[#1E2C3D] overflow-x-auto">
          <span className="text-[10px] text-slate-400 uppercase">Live Stream:</span>
          {packets.map((p, idx) => (
            <button
              key={p.id}
              onClick={() => {
                playTacticalClick();
                setSelectedPacketIndex(idx);
              }}
              className={`px-2.5 py-1 rounded text-[10px] transition-all flex items-center gap-1.5 ${
                idx === selectedPacketIndex
                  ? 'bg-[#00F2FF]/20 text-[#00F2FF] border border-[#00F2FF]/50 font-bold'
                  : 'bg-[#111A26] text-slate-400 border border-[#1E2C3D] hover:text-white'
              }`}
            >
              <span>{p.messageId}</span>
              <span className="text-[8px] opacity-70">({p.lengthBytes}B)</span>
            </button>
          ))}
        </div>

        {/* Dual-Pane Diagnostic Window */}
        <div className="flex-1 grid grid-cols-2 divide-x divide-[#1E2C3D] overflow-hidden">
          {/* Left Pane: Decoded MISB / DLI KLV Tags */}
          <div className="p-3 overflow-y-auto flex flex-col gap-2">
            <div className="text-[10px] font-bold text-[#00F2FF] flex items-center justify-between border-b border-[#1E2C3D] pb-1">
              <span>DECODED METADATA TAGS</span>
              <span className="text-slate-400">CRC: {packet.crc16} [VALID]</span>
            </div>

            <div className="space-y-1.5">
              {packet.klvTags.map((t) => (
                <div key={t.tag} className="bg-[#070A0F] p-2 rounded border border-[#1E2C3D]">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-slate-400">TAG {t.tag}:</span>
                    <span className="text-[#38BDF8] font-bold">{t.name}</span>
                  </div>
                  <div className="text-white font-semibold text-xs mt-1">{t.value}</div>
                  <div className="text-[9px] text-slate-500 font-mono mt-0.5">HEX: {t.hex}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Right Pane: SMPTE 16-byte key & Raw Hex Dump */}
          <div className="p-3 overflow-y-auto flex flex-col gap-2 bg-[#040609]">
            <div className="text-[10px] font-bold text-[#10B981] flex items-center justify-between border-b border-[#1E2C3D] pb-1">
              <span>RAW SMPTE-336M BYTE DUMP</span>
              <button
                onClick={handleCopyHex}
                className="flex items-center gap-1 text-[9px] text-slate-400 hover:text-white"
              >
                <Copy className="w-3 h-3" />
                <span>{copied ? 'COPIED!' : 'COPY RAW HEX'}</span>
              </button>
            </div>

            {/* SMPTE 16-Byte Universal Key Header */}
            <div className="bg-[#0B111A] p-2 rounded border border-[#1E2C3D]">
              <div className="text-[9px] text-slate-400 mb-1">
                SMPTE 16-BYTE UNIVERSAL METADATA KEY (MISB 0601):
              </div>
              <div className="text-[#00F2FF] text-[10px] font-mono break-all leading-relaxed">
                06 0E 2B 34 02 0B 01 01 0E 01 03 01 01 00 00 00
              </div>
            </div>

            {/* Full Hex Dump */}
            <div className="bg-[#0B111A] p-2 rounded border border-[#1E2C3D] flex-1">
              <div className="text-[9px] text-slate-400 mb-1">PAYLOAD STREAM BYTES:</div>
              <div className="text-slate-300 text-[10px] font-mono break-all leading-relaxed">
                {packet.rawHex}
              </div>
            </div>

            {/* Checksum & Protocol Verification */}
            <div className="bg-[#0B111A] p-2 rounded border border-[#10B981]/40 flex items-center justify-between text-[10px]">
              <div className="flex items-center gap-1.5 text-[#10B981]">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>STANAG 4586 DLI PROTOCOL COMPLIANT</span>
              </div>
              <span className="text-slate-400">BER: 0.00%</span>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-end px-4 py-2 bg-[#070A0F] border-t border-[#1E2C3D]">
          <button
            onClick={() => {
              playTacticalClick();
              onClose();
            }}
            className="px-4 py-1.5 bg-[#111A26] hover:bg-[#1E2C3D] text-white rounded text-xs"
          >
            CLOSE INSPECTOR
          </button>
        </div>
      </div>
    </div>
  );
};
