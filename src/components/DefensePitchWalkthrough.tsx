import React, { useState } from 'react';
import { 
  Award, 
  ChevronRight, 
  ChevronLeft, 
  ShieldCheck, 
  Cpu, 
  Crosshair, 
  Binary, 
  Activity, 
  Sliders, 
  Zap, 
  CheckCircle2 
} from 'lucide-react';
import { playTacticalClick } from '../utils/tacticalAudio';

interface DefensePitchWalkthroughProps {
  onOpenAnomalyInjector: () => void;
  onOpenPacketInspector: () => void;
  onOpenScorecard: () => void;
}

export const DefensePitchWalkthrough: React.FC<DefensePitchWalkthroughProps> = ({
  onOpenAnomalyInjector,
  onOpenPacketInspector,
  onOpenScorecard,
}) => {
  const [currentSlide, setCurrentSlide] = useState(0);

  const slides = [
    {
      stage: '01',
      title: 'OPERATIONAL CHALLENGE & DRDO MANDATE',
      subtitle: 'Next-Gen MALE UAV Command & Control for Contested Borders',
      icon: <ShieldCheck className="w-8 h-8 text-[#00F2FF]" />,
      summary:
        'Tactical deployment of MALE UAVs (DRDO TAPAS-BH-201 class) across high-altitude LAC Himalayan frontiers faces acute challenges: GPS spoofing, thermal engine strain at 25,000+ ft MSL, telemetry latency spikes, and fragmented operator workflows.',
      points: [
        'High-altitude thin air operation requires real-time Rotax 914 turbo boost & CHT monitoring.',
        'Electronic Warfare threats demand automated Dead-Reckoning & autonomous RTH failsafes.',
        'Swarm coordination necessitates STANAG 4586 DLI datalink compliance.',
      ],
      action: null,
    },
    {
      stage: '02',
      title: 'PHYSICS-INFORMED DIGITAL TWIN ARCHITECTURE',
      subtitle: 'Real-Time Propulsion Prognostics & Health Monitoring',
      icon: <Cpu className="w-8 h-8 text-[#10B981]" />,
      summary:
        'Our system couples 5Hz telemetry with a physics-informed propulsion digital twin model, simulating thermodynamics, manifold boost regulation, and Remaining Useful Life (RUL) estimation for critical flight components.',
      points: [
        'Real-time CHT/EGT/MAP telemetry with threshold alerts before redline overheat.',
        'Quad-redundant fly-by-wire surface deflection tracking & 3-green gear annunciators.',
        'Dual 28V DC power bus monitoring with instant LiFePO4 battery switchover.',
      ],
      action: {
        label: 'TEST ENGINE OVERHEAT ANOMALY',
        onClick: onOpenAnomalyInjector,
      },
    },
    {
      stage: '03',
      title: 'MULTI-SPECTRAL ATR & TARGET ACQUISITION',
      subtitle: '5 Sensor Palettes + MIL-STD-2525 Symbology + STANAG 3733 LTD',
      icon: <Crosshair className="w-8 h-8 text-[#EF4444]" />,
      summary:
        'Operators can seamlessly cycle through Day EO, FLIR White-Hot, FLIR Black-Hot, Ironbow, and SAR GMTI radar scans with edge neural network bounding boxes and pulse-coded laser designator locks.',
      points: [
        'YOLOv9-Aero neural target detection with confidence scoring & slant range estimation.',
        'Single-click gimbal target slaving with Kalman predictive velocity tracking.',
        'STANAG 3733 pulse repetition frequency code (PRFC 1688) laser targeting.',
      ],
      action: null,
    },
    {
      stage: '04',
      title: 'STANAG 4586 / MISB ST 0601 PROTOCOL SUITE',
      subtitle: 'Interoperable NATO & Indian Armed Forces DLI Compliance',
      icon: <Binary className="w-8 h-8 text-[#38BDF8]" />,
      summary:
        'Full compliance with STANAG 4586 Data Link Interface (DLI) messages #2000/#3000 and MISB ST 0601 KLV metadata streaming with SMPTE 16-byte universal keys and CRC-16 checksums.',
      points: [
        'Live MISB ST 0601 KLV packet decoding for sensor telemetry & target coordinates.',
        'Raw byte hex dump inspector for communications engineers & verification audit.',
        'Zero-trust packet integrity with Bit Error Rate (BER) monitoring.',
      ],
      action: {
        label: 'LAUNCH STANAG PACKET INSPECTOR',
        onClick: onOpenPacketInspector,
      },
    },
    {
      stage: '05',
      title: 'HACKATHON EVALUATION & TECHNICAL EXCELLENCE',
      subtitle: 'SIH 2026 Ready — Tactical Ergonomics & Defense Grade Engineering',
      icon: <Award className="w-8 h-8 text-[#F59E0B]" />,
      summary:
        'Engineered from the ground up without external map tile dependencies, featuring zero-latency synthesized audio, WCAG AA high-contrast tactical palettes, and military-grade high density C2 layouts.',
      points: [
        '100% vector SVG GIS map with SAM threat envelopes & DEM terrain clearance.',
        'Interactive red-team anomaly injector for live evaluator stress-testing.',
        'Production-grade TypeScript architecture with strict safety invariant guarantees.',
      ],
      action: {
        label: 'VIEW DRDO SIH 2026 SCORECARD',
        onClick: onOpenScorecard,
      },
    },
  ];

  const slide = slides[currentSlide];

  const handleNext = () => {
    playTacticalClick();
    setCurrentSlide((prev) => (prev + 1) % slides.length);
  };

  const handlePrev = () => {
    playTacticalClick();
    setCurrentSlide((prev) => (prev - 1 + slides.length) % slides.length);
  };

  return (
    <div className="w-full h-full bg-[#070A0F] border border-[#1E2C3D] rounded-md p-4 flex flex-col justify-between font-mono select-none shadow-inner text-xs">
      {/* Deck Header */}
      <div className="flex items-center justify-between border-b border-[#1E2C3D] pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-[#111A26] border border-[#F59E0B]/50 text-[#F59E0B] rounded">
            <Award className="w-5 h-5" />
          </div>
          <div>
            <div className="text-white font-bold text-sm tracking-wider">
              SIH 2026 DEFENSE EVALUATION BRIEFING DECK
            </div>
            <div className="text-[10px] text-[#F59E0B]">
              DRDO TAPAS-BH-201 MALE UAV GROUND CONTROL STATION ARCHITECTURE
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-slate-400 text-[10px]">STAGE:</span>
          <span className="text-[#00F2FF] font-bold text-sm">
            {slide.stage} / {slides.length.toString().padStart(2, '0')}
          </span>
        </div>
      </div>

      {/* Main Slide Presentation Stage */}
      <div className="flex-1 my-4 bg-[#0B111A] border border-[#1E2C3D] rounded-lg p-6 flex flex-col justify-between shadow-xl">
        <div>
          {/* Slide Title & Subtitle */}
          <div className="flex items-center gap-4 mb-4">
            <div className="p-3 bg-[#070A0F] border border-[#1E2C3D] rounded-lg shadow">
              {slide.icon}
            </div>
            <div>
              <div className="text-lg font-bold text-white tracking-wide">{slide.title}</div>
              <div className="text-xs text-[#38BDF8] font-semibold">{slide.subtitle}</div>
            </div>
          </div>

          {/* Slide Narrative Summary */}
          <div className="bg-[#070A0F] border border-[#1E2C3D] p-3.5 rounded-md text-slate-300 text-xs leading-relaxed mb-4">
            {slide.summary}
          </div>

          {/* Key Engineering Pillars */}
          <div className="space-y-2">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider">Key Architectural Pillars:</div>
            {slide.points.map((pt, idx) => (
              <div key={idx} className="flex items-center gap-2.5 text-xs text-slate-200">
                <CheckCircle2 className="w-4 h-4 text-[#10B981] flex-shrink-0" />
                <span>{pt}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Slide Action Button if present */}
        {slide.action && (
          <div className="mt-4 pt-3 border-t border-[#1E2C3D] flex justify-end">
            <button
              onClick={() => {
                playTacticalClick();
                slide.action?.onClick();
              }}
              className="px-4 py-2 bg-[#111A26] hover:bg-[#1E2C3D] border border-[#00F2FF] text-[#00F2FF] rounded font-bold text-xs flex items-center gap-2 shadow-[0_0_10px_rgba(0,242,255,0.3)] transition-all"
            >
              <Zap className="w-4 h-4 text-[#00F2FF]" />
              <span>{slide.action.label}</span>
            </button>
          </div>
        )}
      </div>

      {/* Deck Navigation Controls */}
      <div className="flex items-center justify-between border-t border-[#1E2C3D] pt-3">
        <div className="flex items-center gap-1.5">
          {slides.map((_, idx) => (
            <button
              key={idx}
              onClick={() => {
                playTacticalClick();
                setCurrentSlide(idx);
              }}
              className={`h-2 rounded-full transition-all ${
                idx === currentSlide ? 'w-8 bg-[#00F2FF]' : 'w-2 bg-[#1E2C3D] hover:bg-slate-500'
              }`}
            />
          ))}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handlePrev}
            className="px-3 py-1.5 bg-[#0B111A] hover:bg-[#111A26] border border-[#1E2C3D] text-slate-300 rounded flex items-center gap-1 text-xs"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>PREV STAGE</span>
          </button>
          <button
            onClick={handleNext}
            className="px-4 py-1.5 bg-[#00F2FF] hover:bg-[#00D8E6] text-black font-bold rounded flex items-center gap-1 text-xs shadow-[0_0_10px_rgba(0,242,255,0.4)]"
          >
            <span>NEXT STAGE</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
