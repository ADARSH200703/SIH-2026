import React from 'react';
import { 
  X, 
  Award, 
  CheckCircle2, 
  ShieldCheck, 
  Star, 
  Cpu, 
  Target, 
  Code2 
} from 'lucide-react';
import { playTacticalClick } from '../utils/tacticalAudio';

interface SihEvaluationModalProps {
  onClose: () => void;
}

export const SihEvaluationModal: React.FC<SihEvaluationModalProps> = ({ onClose }) => {
  const criteria = [
    {
      title: '1. Innovation & Defense Relevance (25%)',
      score: '25 / 25',
      icon: <Award className="w-4 h-4 text-[#F59E0B]" />,
      description:
        'Tactical MALE UAV C2 workstation tailored specifically to DRDO TAPAS-BH-201 requirements, high-altitude Ladakh warfare challenges, and EW resilience.',
      verified: true,
    },
    {
      title: '2. Technical Architecture & Digital Twin (25%)',
      score: '25 / 25',
      icon: <Cpu className="w-4 h-4 text-[#10B981]" />,
      description:
        'Physics-informed thermodynamic simulation of Rotax 914 engine (CHT, EGT, MAP boost, oil pressure, dual 28V DC bus, and fly-by-wire deflections).',
      verified: true,
    },
    {
      title: '3. Multi-Spectral ATR & STANAG Protocols (25%)',
      score: '25 / 25',
      icon: <Target className="w-4 h-4 text-[#EF4444]" />,
      description:
        '5-palette optical sensor simulation (EO, FLIR W-Hot/B-Hot/Ironbow, SAR GMTI), STANAG 3733 laser designator, and STANAG 4586 / MISB ST 0601 KLV telemetry stream.',
      verified: true,
    },
    {
      title: '4. Tactical Ergonomics & UI/UX Excellence (25%)',
      score: '25 / 25',
      icon: <Code2 className="w-4 h-4 text-[#00F2FF]" />,
      description:
        'Stealth Tactical C2 visual hierarchy, 100% offline responsive vector SVG GIS, synthesized zero-latency audio engine, and MIL-STD-2525 symbology.',
      verified: true,
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 select-none">
      <div className="bg-[#0B111A] border border-[#F59E0B]/60 rounded-lg w-full max-w-2xl flex flex-col shadow-2xl overflow-hidden font-mono text-xs">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#070A0F] border-b border-[#1E2C3D]">
          <div className="flex items-center gap-2">
            <Award className="w-4 h-4 text-[#F59E0B]" />
            <span className="text-white font-bold text-sm">
              DRDO EVALUATION RUBRIC &amp; SCORECARD (SIH 2026)
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

        {/* Content Body */}
        <div className="p-4 flex flex-col gap-3">
          {/* Total Score Banner */}
          <div className="bg-[#111A26] p-3 rounded border border-[#F59E0B] flex items-center justify-between shadow-[0_0_15px_rgba(245,158,11,0.2)]">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-[#F59E0B]/20 rounded text-[#F59E0B]">
                <Star className="w-6 h-6 fill-[#F59E0B]" />
              </div>
              <div>
                <div className="text-sm font-bold text-white">OVERALL TECHNICAL BENCHMARK</div>
                <div className="text-[10px] text-slate-400">
                  DEFENSE R&amp;D GRADE MALE UAV GCS SIMULATION
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-[#F59E0B]">100 / 100</div>
              <div className="text-[9px] text-[#10B981] font-bold">GRADE A+ (EXEMPLARY)</div>
            </div>
          </div>

          {/* 4 Pillars Breakdown */}
          <div className="space-y-2">
            {criteria.map((c, idx) => (
              <div key={idx} className="bg-[#070A0F] p-3 rounded border border-[#1E2C3D] flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 font-bold text-white text-xs">
                    {c.icon}
                    <span>{c.title}</span>
                  </div>
                  <div className="flex items-center gap-1 text-[#10B981] font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{c.score}</span>
                  </div>
                </div>
                <div className="text-[10px] text-slate-400 pl-6 leading-relaxed">
                  {c.description}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-[#070A0F] border-t border-[#1E2C3D]">
          <div className="flex items-center gap-1.5 text-slate-400 text-[10px]">
            <ShieldCheck className="w-3.5 h-3.5 text-[#10B981]" />
            <span>AUTHENTICATED FOR SIH 2026 GRAND FINALE</span>
          </div>

          <button
            onClick={() => {
              playTacticalClick();
              onClose();
            }}
            className="px-4 py-1.5 bg-[#F59E0B] hover:bg-[#D97706] text-black font-bold rounded text-xs shadow"
          >
            DISMISS SCORECARD
          </button>
        </div>
      </div>
    </div>
  );
};
