"use client";

import React from "react";
import { Mic, Radio, Volume2, ShieldAlert, Zap, Cpu, Sparkles } from "lucide-react";
import { HolographicWaveform } from "./HolographicWaveform";
import { soundFx } from "../utils/audioEffects";

interface ArcReactorHUDProps {
  voiceState: string;
  voiceDetail: string;
  voiceRunning: boolean;
  isLocalRecording: boolean;
  onMicClick: () => void;
  onToggleVoice: () => void;
}

export const ArcReactorHUD: React.FC<ArcReactorHUDProps> = ({
  voiceState,
  voiceDetail,
  voiceRunning,
  isLocalRecording,
  onMicClick,
  onToggleVoice,
}) => {
  const isListening = voiceState === "LISTENING" || isLocalRecording;
  const isSpeaking = voiceState === "SPEAKING";
  const isPlanning = voiceState === "PLANNING" || voiceState === "UNDERSTANDING" || voiceState === "EXECUTING";
  const isWaitingPerm = voiceState === "WAITING_FOR_PERMISSION";

  const handleCoreClick = () => {
    soundFx.playButtonClick();
    if (!isListening) {
      soundFx.playWakeChime();
    }
    onMicClick();
  };

  return (
    <div className="relative flex flex-col items-center justify-center p-4 select-none">
      
      {/* BACKGROUND ROTATING HUD RINGS (Inspired by Stark Industries Arc Reactor) */}
      <div className="relative w-84 h-84 flex items-center justify-center">
        
        {/* Outer Ring with Compass Ticks */}
        <div className="absolute inset-0 rounded-full border border-cyan-500/25 animate-[spin_80s_linear_infinite] pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1 text-[9px] font-mono text-cyan-400/70 font-bold tracking-wider">000° // N</div>
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1 text-[9px] font-mono text-cyan-400/70 font-bold tracking-wider">180° // S</div>
          <div className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1 text-[9px] font-mono text-cyan-400/70 font-bold tracking-wider">270° // W</div>
          <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1 text-[9px] font-mono text-cyan-400/70 font-bold tracking-wider">090° // E</div>
        </div>

        {/* Outer Glowing Dashed Ring */}
        <div className="absolute inset-3 rounded-full border-2 border-dashed border-cyan-400/30 animate-[spin_35s_linear_infinite_reverse] pointer-events-none" />

        {/* Holographic Radar Sweep Beam */}
        <div className="absolute inset-5 rounded-full overflow-hidden pointer-events-none opacity-40">
          <div className="w-full h-full animate-radar origin-center bg-[conic-gradient(from_0deg,transparent_0deg,transparent_270deg,rgba(0,240,255,0.25)_360deg)]" />
        </div>

        {/* Secondary Segmented Ring with Corner Brackets */}
        <div className="absolute inset-9 rounded-full border border-cyan-400/40 shadow-[0_0_25px_rgba(0,240,255,0.2)] pointer-events-none" />

        {/* Arc Reactor Core Glow Backdrop */}
        <div className={`absolute inset-14 rounded-full transition-all duration-700 pointer-events-none ${
          isListening 
            ? "bg-cyan-500/25 shadow-[0_0_70px_#00f0ff90] scale-110" 
            : isSpeaking
            ? "bg-purple-500/25 shadow-[0_0_70px_#c084fc90] scale-105"
            : isWaitingPerm
            ? "bg-amber-500/25 shadow-[0_0_70px_#f59e0b90] scale-105 animate-pulse"
            : isPlanning
            ? "bg-blue-500/20 shadow-[0_0_50px_#38bdf860] scale-100"
            : "bg-cyan-950/40 shadow-[0_0_30px_#00f0ff20]"
        }`} />

        {/* Center Interactive Microphone Arc Core */}
        <button
          type="button"
          onClick={handleCoreClick}
          className={`relative z-10 w-36 h-36 rounded-full border-2 flex flex-col items-center justify-center transition-all duration-300 group cursor-pointer ${
            isListening
              ? "border-cyan-300 bg-cyan-950/90 shadow-[0_0_50px_#00f0ff] scale-105"
              : isSpeaking
              ? "border-purple-400 bg-purple-950/90 shadow-[0_0_50px_#c084fc]"
              : isWaitingPerm
              ? "border-amber-400 bg-amber-950/90 shadow-[0_0_50px_#f59e0b] animate-bounce"
              : isPlanning
              ? "border-sky-400 bg-[#071733]/90 shadow-[0_0_40px_#38bdf8]"
              : "border-cyan-500/60 bg-[#040f21]/95 hover:border-cyan-300 hover:shadow-[0_0_35px_rgba(0,240,255,0.45)] hover:scale-102"
          }`}
          title="Click to speak command to NOVA"
        >
          {/* Internal Arc Core Concentric Lines */}
          <div className="absolute inset-2 rounded-full border border-cyan-400/35 pointer-events-none" />
          <div className="absolute inset-4 rounded-full border border-cyan-400/25 pointer-events-none" />

          {/* Center Icon */}
          <div className="relative z-20 flex flex-col items-center space-y-1">
            {isSpeaking ? (
              <Volume2 className="h-10 w-10 text-purple-300 animate-bounce" />
            ) : isWaitingPerm ? (
              <ShieldAlert className="h-10 w-10 text-amber-400 animate-pulse" />
            ) : isPlanning ? (
              <Cpu className="h-10 w-10 text-sky-300 animate-spin" />
            ) : (
              <Mic className={`h-10 w-10 transition-transform group-hover:scale-110 ${
                isListening ? "text-cyan-200 animate-pulse scale-110" : "text-cyan-400"
              }`} />
            )}
            <span className={`text-[10px] font-mono font-black tracking-widest uppercase ${
              isListening ? "text-cyan-200" : isSpeaking ? "text-purple-200" : isWaitingPerm ? "text-amber-300" : "text-cyan-300/90"
            }`}>
              {isListening ? "LISTENING" : isSpeaking ? "SPEAKING" : isWaitingPerm ? "CLEARANCE" : isPlanning ? "PLANNING" : "NOVA CORE"}
            </span>
          </div>
        </button>

      </div>

      {/* ELECTRIC BLUE AUDIO WAVEFORM VISUALIZER (IMAGE 1) */}
      <div className="w-full max-w-xl -mt-5 z-10 flex flex-col items-center">
        <HolographicWaveform active={isListening || isSpeaking} state={voiceState} />
        
        {/* HUD Subtitle & Live Speech Telemetry */}
        <div className="flex items-center space-x-3 -mt-2 bg-[#040e20]/80 px-5 py-2 rounded-full border border-cyan-500/30 backdrop-blur-md shadow-[0_0_15px_rgba(0,240,255,0.15)]">
          <span className={`h-2.5 w-2.5 rounded-full ${
            isListening ? "bg-cyan-400 animate-ping shadow-[0_0_10px_#00f0ff]" :
            isSpeaking ? "bg-purple-400 animate-bounce shadow-[0_0_10px_#c084fc]" :
            isWaitingPerm ? "bg-amber-400 animate-ping shadow-[0_0_10px_#f59e0b]" :
            voiceRunning ? "bg-emerald-400 shadow-[0_0_8px_#34d399]" : "bg-slate-600"
          }`} />
          <span className="text-xs font-bold text-cyan-200 tracking-wider">
            {voiceDetail}
          </span>
        </div>
      </div>

    </div>
  );
};
