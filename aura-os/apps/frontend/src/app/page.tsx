"use client";

import { useState, useEffect, useRef } from "react";
import {
  Terminal,
  Play,
  CheckCircle2,
  XCircle,
  Cpu,
  Layers,
  Activity,
  ShieldAlert,
  Eye,
  RefreshCw,
  Mic,
  Volume2,
  VolumeX,
  Radio,
  Sparkles,
  Zap,
  HardDrive,
  Wifi,
  Globe,
  Sliders,
  ShieldCheck,
  FolderTree,
  FileCode,
  Search,
  Trash2,
  Clock,
  Check
} from "lucide-react";
import { ArcReactorHUD } from "../components/ArcReactorHUD";
import { soundFx } from "../utils/audioEffects";

interface Step {
  step_number: number;
  description: string;
  tool_name: string | null;
  tool_args: Record<string, any> | null;
  status: "PENDING" | "EXECUTING" | "COMPLETED" | "FAILED";
  result: string | null;
  verification_result: string | null;
}

interface TaskDetails {
  task_id: string;
  user_request: string;
  state: string;
  created_at: string;
  steps: Step[];
}

interface ToolInfo {
  name: string;
  description: string;
  risk_level: string;
  required_permission: string;
  parameters: Record<string, any>;
}

interface AuditLog {
  id: number;
  timestamp: string;
  task_id: string | null;
  tool_name: string;
  arguments: string;
  result: string | null;
  risk_level: string;
  permission_status: string;
}

interface TaskSummary {
  id: string;
  user_request: string;
  state: string;
  created_at: string;
}

interface MemoryItem {
  id?: number;
  key: string;
  value: string;
  category: string;
  created_at: string;
}

const API_BASE = "http://127.0.0.1:8000";
const WS_URL = "ws://127.0.0.1:8000/api/ws";

export default function Home() {
  // App States
  const [commandInput, setCommandInput] = useState("");
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [taskDetails, setTaskDetails] = useState<TaskDetails | null>(null);
  const [wsStatus, setWsStatus] = useState<"connecting" | "connected" | "disconnected">("disconnected");
  
  // Voice States
  const [voiceRunning, setVoiceRunning] = useState(true);
  const [voiceState, setVoiceState] = useState<string>("IDLE");
  const [voiceDetail, setVoiceDetail] = useState<string>("SAY \"NOVA\" TO ENGAGE");
  const [isLocalRecording, setIsLocalRecording] = useState(false);
  const [isAudioMuted, setIsAudioMuted] = useState(false);

  // Lists & Tabs
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [recentTasks, setRecentTasks] = useState<TaskSummary[]>([]);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [systemInfo, setSystemInfo] = useState<any>(null);
  const [rightPanelTab, setRightPanelTab] = useState<"tools" | "audit" | "memory" | "archive">("tools");
  const [toolSearch, setToolSearch] = useState("");
  
  // Security Checks
  const [pendingPermission, setPendingPermission] = useState<any>(null);
  
  // UI Telemetry & Clock
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [cpuLoad, setCpuLoad] = useState(16);
  const [ramUsage, setRamUsage] = useState(4.3);
  const [currentTime, setCurrentTime] = useState<string>("");

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Update Clock & Mock Telemetry
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString("en-US", { hour12: false }));
    };
    updateTime();
    const clockInterval = setInterval(updateTime, 1000);

    const telemetryInterval = setInterval(() => {
      setCpuLoad(Math.floor(Math.random() * 16) + 12);
      setRamUsage(parseFloat((4.1 + Math.random() * 0.4).toFixed(1)));
    }, 3000);

    return () => {
      clearInterval(clockInterval);
      clearInterval(telemetryInterval);
    };
  }, []);

  // Fetch REST data & sync with backend
  const fetchData = async () => {
    try {
      const statusRes = await fetch(`${API_BASE}/`, { cache: "no-store" });
      if (!statusRes.ok) return;
      const statusData = await statusRes.json();
      setSystemInfo(statusData);

      const [toolsRes, tasksRes, auditRes, memRes, voiceRes] = await Promise.allSettled([
        fetch(`${API_BASE}/api/tools`, { cache: "no-store" }),
        fetch(`${API_BASE}/api/tasks`, { cache: "no-store" }),
        fetch(`${API_BASE}/api/audit`, { cache: "no-store" }),
        fetch(`${API_BASE}/api/memory`, { cache: "no-store" }),
        fetch(`${API_BASE}/api/voice/status`, { cache: "no-store" })
      ]);

      if (toolsRes.status === "fulfilled" && toolsRes.value.ok) {
        setTools(await toolsRes.value.json());
      }
      if (tasksRes.status === "fulfilled" && tasksRes.value.ok) {
        setRecentTasks(await tasksRes.value.json());
      }
      if (auditRes.status === "fulfilled" && auditRes.value.ok) {
        setAuditLogs(await auditRes.value.json());
      }
      if (memRes.status === "fulfilled" && memRes.value.ok) {
        setMemories(await memRes.value.json());
      }
      if (voiceRes.status === "fulfilled" && voiceRes.value.ok) {
        const voiceData = await voiceRes.value.json();
        setVoiceRunning(voiceData.running);
        if (voiceData.state) setVoiceState(voiceData.state);
      }
    } catch (e) {
      // Backend starting up or transient offline
    }
  };

  useEffect(() => {
    fetchData();
    connectWebSocket();

    // Periodic live sync every 4 seconds
    const syncInterval = setInterval(fetchData, 4000);

    return () => {
      clearInterval(syncInterval);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, []);

  // Establish WebSocket Connection with automatic recovery
  const connectWebSocket = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    try {
      setWsStatus("connecting");
      const ws = new WebSocket(WS_URL);
      socketRef.current = ws;

      ws.onopen = () => {
        setWsStatus("connected");
        console.log("[WebSocket] Connected successfully to NOVA OS backend.");
        fetchData();
      };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.event === "task_update") {
          const updatedTask = payload.data as TaskDetails;
          setTaskDetails(updatedTask);
          setCurrentTaskId(updatedTask.task_id);

          if (updatedTask.state === "WAITING_FOR_PERMISSION") {
            soundFx.playWarningHum();
            fetchPendingPermission(updatedTask.task_id);
          } else {
            setPendingPermission(null);
          }

          if (updatedTask.state === "COMPLETED") {
            soundFx.playSuccessChime();
            fetchData();
          } else if (["FAILED", "CANCELLED"].includes(updatedTask.state)) {
            fetchData();
          }
        } else if (payload.event === "voice_state") {
          setVoiceState(payload.state);
          if (payload.detail) setVoiceDetail(payload.detail);

          if (payload.state === "LISTENING") {
            soundFx.playWakeChime();
          }
        }
      } catch (err) {
        console.error("Failed to parse websocket payload:", err);
      }
    };

      ws.onclose = () => {
        setWsStatus("disconnected");
        console.log("[WebSocket] Connection closed. Reconnecting in 3s...");
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch (err) {
      setWsStatus("disconnected");
      reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
    }
  };

  const fetchPendingPermission = async (taskId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/permissions/pending/${taskId}`);
      const data = await res.json();
      if (data.pending) {
        setPendingPermission(data.details);
      }
    } catch (e) {
      console.error("Failed to fetch pending permission:", e);
    }
  };

  const submitCommandWithText = async (text: string) => {
    if (!text.trim()) return;
    soundFx.playDirectiveEngage();

    try {
      const res = await fetch(`${API_BASE}/api/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: text })
      });
      const data = await res.json();
      
      setCurrentTaskId(data.task_id);
      setTaskDetails({
        task_id: data.task_id,
        user_request: text,
        state: "PLANNING",
        created_at: new Date().toISOString(),
        steps: []
      });
      setCommandInput("");
      setPendingPermission(null);
    } catch (err) {
      console.error("Failed to submit command:", err);
    }
  };

  const submitCommand = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    submitCommandWithText(commandInput);
  };

  const triggerBackendVoice = async () => {
    try {
      soundFx.playWakeChime();
      setVoiceState("LISTENING");
      setVoiceDetail("NOVA LISTENING... SPEAK NOW");
      await fetch(`${API_BASE}/api/voice/trigger`, { method: "POST" });
    } catch (e) {
      console.error("Failed to trigger voice:", e);
    }
  };

  const toggleVoiceMode = async () => {
    soundFx.playButtonClick();
    try {
      const res = await fetch(`${API_BASE}/api/voice/toggle`, { method: "POST" });
      const data = await res.json();
      setVoiceRunning(data.running);
      setVoiceState(data.state);
      setVoiceDetail(data.running ? "SAY \"NOVA\" TO ENGAGE" : "VOICE ENGINE PAUSED");
    } catch (e) {
      console.error("Failed to toggle voice mode:", e);
    }
  };

  const handleMicrophoneClick = () => {
    if (typeof window !== "undefined") {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        soundFx.playWakeChime();
        const recognition = new SpeechRecognition();
        recognition.lang = "en-US";
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        
        setIsLocalRecording(true);
        setVoiceState("LISTENING");
        setVoiceDetail("LISTENING... SPEAK NOW");
        
        recognition.onresult = (event: any) => {
          const speechResult = event.results[0][0].transcript;
          setCommandInput(speechResult);
          setIsLocalRecording(false);
          setVoiceState("UNDERSTANDING");
          setVoiceDetail(`TRANSCRIPTION: "${speechResult.toUpperCase()}"`);
          submitCommandWithText(speechResult);
        };
        
        recognition.onerror = () => {
          setIsLocalRecording(false);
          setVoiceState("IDLE");
          setVoiceDetail("SAY \"NOVA\" TO ENGAGE");
        };
        
        recognition.onend = () => {
          setIsLocalRecording(false);
        };
        
        recognition.start();
        return;
      }
    }
    
    // Fallback to backend sounddevice listener
    triggerBackendVoice();
  };

  const handlePermissionDecision = async (approved: boolean) => {
    if (!currentTaskId) return;
    soundFx.playButtonClick();
    try {
      await fetch(`${API_BASE}/api/permissions/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_id: currentTaskId,
          approved
        })
      });
      setPendingPermission(null);
    } catch (e) {
      console.error("Failed to resolve permission:", e);
    }
  };

  const deleteMemoryItem = async (key: string) => {
    soundFx.playButtonClick();
    try {
      await fetch(`${API_BASE}/api/memory/${key}`, { method: "DELETE" });
      fetchData();
    } catch (e) {
      console.error("Failed to delete memory:", e);
    }
  };

  const toggleSoundMute = () => {
    const nextMute = !isAudioMuted;
    setIsAudioMuted(nextMute);
    soundFx.setMuted(nextMute);
    if (!nextMute) {
      soundFx.playButtonClick();
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk?.toUpperCase()) {
      case "SAFE": return "text-cyan-400 bg-cyan-950/60 border-cyan-800/50 shadow-[0_0_10px_#00f0ff30]";
      case "MODERATE": return "text-blue-400 bg-blue-950/60 border-blue-800/50";
      case "DANGEROUS": return "text-amber-400 bg-amber-950/60 border-amber-800/50";
      case "CRITICAL": return "text-red-400 bg-red-950/60 border-red-800/50 shadow-[0_0_12px_#ef444450]";
      default: return "text-slate-400 bg-slate-900 border-slate-700";
    }
  };

  const filteredTools = tools.filter(t => 
    t.name.toLowerCase().includes(toolSearch.toLowerCase()) || 
    t.description.toLowerCase().includes(toolSearch.toLowerCase())
  );

  return (
    <div className="flex flex-col h-screen bg-[#020610] text-cyan-100 overflow-hidden font-mono select-none relative">
      
      {/* BACKGROUND SCI-FI HUD GRID & RADIAL VIGNETTE */}
      <div className="absolute inset-0 bg-[radial-gradient(#00f0ff10_1px,transparent_1px)] [background-size:24px_24px] pointer-events-none opacity-40" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_900px_at_50%_40%,rgba(0,140,255,0.08),transparent_80%)] pointer-events-none" />
      <div className="absolute inset-0 crt-scanlines opacity-30" />

      {/* TOP HUD BAR (STARK INDUSTRIES THEMED) */}
      <header className="relative z-20 h-16 border-b border-cyan-500/30 bg-[#040d1c]/90 px-8 flex items-center justify-between backdrop-blur-md shadow-[0_4px_25px_rgba(0,240,255,0.12)]">
        {/* Left branding */}
        <div className="flex items-center space-x-4">
          <div className="p-2 bg-cyan-950/90 border border-cyan-400/60 rounded-lg shadow-[0_0_18px_rgba(0,240,255,0.35)]">
            <Zap className="h-5 w-5 text-cyan-300 animate-pulse" />
          </div>
          <div>
            <h1 className="text-lg font-black tracking-widest text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-sky-300 to-cyan-100">
              STARK INDUSTRIES // NOVA OS
            </h1>
            <p className="text-[10px] text-cyan-500/90 tracking-widest">AI-NATIVE HOLOGRAPHIC COMPUTER AGENT</p>
          </div>
        </div>

        {/* Center HUD status */}
        <div className="hidden md:flex items-center space-x-6 text-xs text-cyan-400/80">
          <div className="flex items-center space-x-2">
            <span className="text-slate-500">PROTOCOL:</span>
            <span className="text-cyan-300 font-bold tracking-wider">MARK VIII</span>
          </div>
          <div className="h-4 w-px bg-cyan-500/30" />
          <div className="flex items-center space-x-2">
            <span className="text-slate-500">CORE:</span>
            <span className="text-emerald-400 font-bold tracking-wider">100% ONLINE</span>
          </div>
          <div className="h-4 w-px bg-cyan-500/30" />
          <div className="flex items-center space-x-2">
            <span className="text-slate-500">WAKE WORD:</span>
            <span className="text-cyan-300 font-bold tracking-widest bg-cyan-950 px-2.5 py-0.5 rounded border border-cyan-500/50 shadow-[0_0_10px_rgba(0,240,255,0.25)]">"NOVA"</span>
          </div>
        </div>

        {/* Right HUD telemetry & Controls */}
        <div className="flex items-center space-x-5">
          {/* Mute Audio FX toggle */}
          <button
            onClick={toggleSoundMute}
            className={`p-2 rounded-lg border transition ${
              isAudioMuted 
                ? "bg-slate-900 border-slate-700 text-slate-500" 
                : "bg-cyan-950/80 border-cyan-500/40 text-cyan-400 hover:shadow-[0_0_12px_rgba(0,240,255,0.3)]"
            }`}
            title={isAudioMuted ? "Unmute HUD Audio" : "Mute HUD Audio"}
          >
            {isAudioMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </button>

          <div className="text-right hidden sm:block">
            <div className="text-sm font-bold text-cyan-300 tracking-widest">{currentTime || "20:45:00"}</div>
            <div className="text-[9px] text-slate-500">HUD TELEMETRY ACTIVE</div>
          </div>
          
          <div className={`px-3 py-1 rounded-full text-xs font-bold border flex items-center space-x-2 ${
            wsStatus === "connected" 
              ? "bg-cyan-950/80 text-cyan-300 border-cyan-500/50 shadow-[0_0_12px_#00f0ff50]" 
              : "bg-red-950/80 text-red-400 border-red-500/50"
          }`}>
            <span className={`h-2 w-2 rounded-full ${wsStatus === "connected" ? "bg-cyan-400 animate-ping" : "bg-red-500"}`} />
            <span className="uppercase text-[10px] tracking-wider">{wsStatus}</span>
          </div>
        </div>
      </header>

      {/* MAIN 3-COLUMN TACTICAL VIEWPORT */}
      <div className="relative z-10 flex-1 flex overflow-hidden">
        
        {/* LEFT PANEL: System Diagnostics & Tactical Protocols */}
        <aside className="w-80 border-r border-cyan-500/20 bg-[#030914]/85 p-5 flex flex-col justify-between overflow-y-auto backdrop-blur-md">
          <div className="space-y-6">
            
            {/* System Diagnostics Box */}
            <div className="p-4 rounded-xl bg-[#051124]/90 border border-cyan-500/35 shadow-[0_0_20px_rgba(0,240,255,0.09)] space-y-4">
              <div className="flex items-center justify-between border-b border-cyan-500/20 pb-2">
                <span className="text-xs font-bold text-cyan-300 uppercase tracking-wider flex items-center space-x-2">
                  <Activity className="h-4 w-4 text-cyan-400" />
                  <span>SYSTEM DIAGNOSTICS</span>
                </span>
                <span className="text-[10px] text-cyan-400 font-bold">OPTIMAL</span>
              </div>

              {/* CPU Load Gauge */}
              <div>
                <div className="flex justify-between text-[11px] text-cyan-400 mb-1">
                  <span className="flex items-center space-x-1.5">
                    <Cpu className="h-3.5 w-3.5 text-cyan-400" />
                    <span>AGENT NEURAL LOAD</span>
                  </span>
                  <span className="font-bold">{cpuLoad}%</span>
                </div>
                <div className="w-full bg-cyan-950/60 rounded-full h-1.5 overflow-hidden border border-cyan-800/40">
                  <div className="bg-gradient-to-r from-cyan-500 to-sky-400 h-1.5 rounded-full transition-all duration-500 shadow-[0_0_8px_#00f0ff]" style={{ width: `${cpuLoad}%` }} />
                </div>
              </div>

              {/* Memory Allocation Gauge */}
              <div>
                <div className="flex justify-between text-[11px] text-cyan-400 mb-1">
                  <span className="flex items-center space-x-1.5">
                    <Layers className="h-3.5 w-3.5 text-cyan-400" />
                    <span>RAM ALLOCATION</span>
                  </span>
                  <span className="font-bold">{ramUsage} GB</span>
                </div>
                <div className="w-full bg-cyan-950/60 rounded-full h-1.5 overflow-hidden border border-cyan-800/40">
                  <div className="bg-gradient-to-r from-cyan-400 to-indigo-500 h-1.5 rounded-full transition-all duration-500 shadow-[0_0_8px_#818cf8]" style={{ width: `${(ramUsage / 16) * 100}%` }} />
                </div>
              </div>

              {/* Storage and Network Metrics */}
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-cyan-500/20 text-[10px] text-cyan-400/80">
                <div className="p-2 bg-cyan-950/40 rounded border border-cyan-800/30">
                  <div className="text-slate-500">STORAGE</div>
                  <div className="font-bold text-cyan-300 mt-0.5">512 GB NVMe</div>
                </div>
                <div className="p-2 bg-cyan-950/40 rounded border border-cyan-800/30">
                  <div className="text-slate-500">UPLINK SPEED</div>
                  <div className="font-bold text-cyan-300 mt-0.5">94.5 MB/s</div>
                </div>
              </div>
            </div>

            {/* Quick Tactical Protocols */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold text-cyan-400/80 uppercase tracking-wider flex items-center space-x-1.5">
                <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                <span>TACTICAL PROTOCOLS</span>
              </h3>
              <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
                {[
                  { label: "LAUNCH NOTEPAD", cmd: "Open Notepad.", cat: "SYSTEM" },
                  { label: "ANALYZE SCREEN (AI VISION)", cmd: "Analyze what is currently visible on the screen.", cat: "VISION" },
                  { label: "PLAY / PAUSE MEDIA", cmd: "pause music", cat: "MEDIA" },
                  { label: "NEXT MEDIA TRACK", cmd: "next track", cat: "MEDIA" },
                  { label: "PLAY SYNTHWAVE ON YOUTUBE", cmd: "Play some synthwave music on YouTube.", cat: "MEDIA" },
                  { label: "MAXIMIZE ACTIVE WINDOW", cmd: "maximize window", cat: "WINDOW" },
                  { label: "SNAP WINDOW LEFT", cmd: "snap left", cat: "WINDOW" },
                  { label: "SNAP WINDOW RIGHT", cmd: "snap right", cat: "WINDOW" },
                  { label: "TURN OFF MONITOR DISPLAY", cmd: "turn off screen", cat: "DEVICE" },
                  { label: "DIM SCREEN (30%)", cmd: "dim screen", cat: "DEVICE" },
                  { label: "LIST BLUETOOTH DEVICES", cmd: "list bluetooth devices", cat: "DEVICE" },
                  { label: "TAKE SCREENSHOT", cmd: "Take a screenshot.", cat: "VISION" },
                  { label: "BATTERY & POWER METRICS", cmd: "Get battery status.", cat: "SYSTEM" },
                  { label: "NETWORK UPLINK CHECK", cmd: "Get network status.", cat: "SYSTEM" },
                  { label: "INSPECT ACTIVE WINDOW", cmd: "Get active window info.", cat: "GUI" },
                  { label: "SHOW DESKTOP (WIN+D)", cmd: "Press keyboard shortcut 'win+d'.", cat: "GUI" },
                  { label: "TOP ACTIVE PROCESSES", cmd: "List top active processes.", cat: "SYSTEM" },
                  { label: "ORGANIZE DOWNLOADS", cmd: "Organize directory 'Downloads'.", cat: "ORGANIZER" },
                  { label: "LOCK WORKSTATION", cmd: "Manage power action 'lock'.", cat: "SECURITY" }
                ].map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      if (item.cat === "VISION") soundFx.playScanSweep();
                      else soundFx.playButtonClick();
                      submitCommandWithText(item.cmd);
                    }}
                    className="w-full text-left p-2 rounded-lg bg-[#051124]/75 hover:bg-cyan-950/90 border border-cyan-500/25 hover:border-cyan-400/70 text-[11px] text-cyan-300 hover:text-white transition group flex items-center justify-between shadow-sm"
                  >
                    <div className="flex items-center space-x-2 truncate">
                      <span className="text-[8px] font-mono font-bold px-1 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/40">{item.cat}</span>
                      <span className="truncate">{item.label}</span>
                    </div>
                    <Play className="h-3 w-3 text-cyan-400 opacity-0 group-hover:opacity-100 transition shrink-0" />
                  </button>
                ))}
              </div>
            </div>

          </div>

          {/* Bottom AI Model Specs */}
          <div className="pt-4 border-t border-cyan-500/20 text-[11px] text-cyan-500/80 space-y-1">
            <div className="flex justify-between">
              <span>NEURAL ENGINE:</span>
              <span className="text-cyan-300 font-bold">{systemInfo?.model || "gemini-3.5-flash"}</span>
            </div>
            <div className="flex justify-between">
              <span>SECURITY PROTOCOL:</span>
              <span className="text-emerald-400 font-bold">LEVEL 4 GATED</span>
            </div>
          </div>
        </aside>

        {/* CENTER VIEWPORT: Arc Reactor Hologram & Mission Execution Matrix */}
        <main className="flex-1 p-6 flex flex-col justify-between overflow-y-auto">
          <div className="space-y-5">
            
            {/* ARC REACTOR HUD HERO COMPONENT */}
            <ArcReactorHUD
              voiceState={voiceState}
              voiceDetail={voiceDetail}
              voiceRunning={voiceRunning}
              isLocalRecording={isLocalRecording}
              onMicClick={handleMicrophoneClick}
              onToggleVoice={toggleVoiceMode}
            />

            {/* ACTIVE MISSION EXECUTION TERMINAL */}
            {taskDetails ? (
              <div className="p-5 rounded-2xl bg-[#040e22]/90 border border-cyan-500/40 shadow-[0_0_30px_rgba(0,240,255,0.12)] backdrop-blur-md space-y-4">
                {/* Directive Title & Header */}
                <div className="flex items-center justify-between border-b border-cyan-500/20 pb-3">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 rounded-lg bg-cyan-950/80 border border-cyan-400/40">
                      <Terminal className="h-4 w-4 text-cyan-400" />
                    </div>
                    <div>
                      <div className="text-[10px] text-cyan-500 tracking-wider">ACTIVE DIRECTIVE</div>
                      <div className="text-sm font-bold text-white tracking-wide">"{taskDetails.user_request}"</div>
                    </div>
                  </div>
                  <div className={`px-3 py-1 rounded-full text-xs font-bold border flex items-center space-x-2 ${
                    taskDetails.state === "COMPLETED" ? "bg-emerald-950 text-emerald-400 border-emerald-500/40 shadow-[0_0_12px_#34d39940]" :
                    taskDetails.state === "FAILED" ? "bg-red-950 text-red-400 border-red-500/40" :
                    taskDetails.state === "WAITING_FOR_PERMISSION" ? "bg-amber-950 text-amber-300 border-amber-500/40 animate-pulse" :
                    "bg-cyan-950 text-cyan-300 border-cyan-500/40 shadow-[0_0_12px_#00f0ff40]"
                  }`}>
                    <span className={`h-2 w-2 rounded-full ${
                      taskDetails.state === "COMPLETED" ? "bg-emerald-400" :
                      taskDetails.state === "FAILED" ? "bg-red-500" :
                      taskDetails.state === "WAITING_FOR_PERMISSION" ? "bg-amber-400 animate-ping" :
                      "bg-cyan-400 animate-ping"
                    }`} />
                    <span>{taskDetails.state}</span>
                  </div>
                </div>

                {/* Step Execution Sequence */}
                <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
                  {taskDetails.steps.length === 0 ? (
                    <div className="p-4 text-center text-xs text-cyan-400/60 border border-dashed border-cyan-500/20 rounded-xl flex items-center justify-center space-x-2">
                      <RefreshCw className="h-4 w-4 animate-spin text-cyan-400" />
                      <span>NOVA NEURAL PLANNER FORMULATING EXECUTION PATH...</span>
                    </div>
                  ) : (
                    taskDetails.steps.map((step) => (
                      <div
                        key={step.step_number}
                        className={`p-3 rounded-xl border text-xs transition ${
                          step.status === "COMPLETED" ? "bg-emerald-950/20 border-emerald-500/30 text-emerald-300" :
                          step.status === "EXECUTING" ? "bg-cyan-950/40 border-cyan-400 text-white shadow-[0_0_15px_rgba(0,240,255,0.2)]" :
                          step.status === "FAILED" ? "bg-red-950/20 border-red-500/30 text-red-300" :
                          "bg-[#051124]/60 border-cyan-500/20 text-slate-400"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-2.5">
                            <span className="font-mono font-bold text-cyan-400">[{step.step_number.toString().padStart(2, '0')}]</span>
                            <span className="font-semibold text-white">{step.description}</span>
                          </div>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            step.status === "COMPLETED" ? "text-emerald-400 bg-emerald-950" :
                            step.status === "EXECUTING" ? "text-cyan-300 bg-cyan-950 animate-pulse" :
                            step.status === "FAILED" ? "text-red-400 bg-red-950" :
                            "text-slate-500 bg-slate-900"
                          }`}>
                            {step.status}
                          </span>
                        </div>
                        {step.result && (
                          <div className="mt-2 p-2 rounded bg-black/40 text-[11px] font-mono text-cyan-300/90 whitespace-pre-wrap border border-cyan-900/30">
                            {step.result}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            ) : null}

            {/* SECURITY CLEARANCE REQUIRED MODAL */}
            {pendingPermission && (
              <div className="p-5 rounded-2xl bg-gradient-to-r from-amber-950/90 via-orange-950/90 to-amber-950/90 border-2 border-amber-500/70 shadow-[0_0_40px_rgba(245,158,11,0.3)] space-y-4 backdrop-blur-md animate-hud-glow">
                <div className="flex items-center space-x-3 text-amber-300">
                  <ShieldAlert className="h-6 w-6 text-amber-400 animate-bounce" />
                  <div>
                    <h3 className="text-sm font-black tracking-widest uppercase">SECURITY CLEARANCE AUTHORIZATION REQUIRED</h3>
                    <p className="text-xs text-amber-200/80">A high-risk action requires human approval to proceed.</p>
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-black/60 border border-amber-500/30 text-xs space-y-1 font-mono">
                  <div className="text-slate-400">TOOL: <span className="text-amber-300 font-bold">{pendingPermission.tool_name}</span></div>
                  <div className="text-slate-400">RISK: <span className="text-red-400 font-bold">{pendingPermission.risk_level}</span></div>
                  <div className="text-slate-400">ARGUMENTS: <span className="text-amber-200">{JSON.stringify(pendingPermission.arguments)}</span></div>
                </div>

                <div className="flex space-x-3">
                  <button
                    onClick={() => handlePermissionDecision(true)}
                    className="flex-1 py-2.5 px-4 rounded-xl bg-amber-500 hover:bg-amber-400 text-black font-black text-xs uppercase tracking-wider transition shadow-[0_0_20px_#f59e0b60] cursor-pointer"
                  >
                    GRANT AUTHORIZATION
                  </button>
                  <button
                    onClick={() => handlePermissionDecision(false)}
                    className="px-6 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 font-bold text-xs uppercase tracking-wider transition cursor-pointer"
                  >
                    ABORT
                  </button>
                </div>
              </div>
            )}

          </div>

          {/* TACTICAL INPUT PROMPT WITH INTEGRATED MIC ACTIVATION */}
          <form onSubmit={submitCommand} className="mt-4 flex space-x-3">
            <div className="relative flex-1">
              <input
                type="text"
                value={commandInput}
                onChange={(e) => setCommandInput(e.target.value)}
                placeholder="ENTER DIRECTIVE OR SAY 'NOVA' (E.G. 'OPEN NOTEPAD AND CHECK BATTERY')..."
                className="w-full bg-[#051124]/90 border border-cyan-500/40 rounded-xl px-5 py-3.5 text-xs font-bold text-cyan-200 placeholder-cyan-700/60 focus:outline-none focus:border-cyan-300 focus:shadow-[0_0_20px_rgba(0,240,255,0.3)] transition"
              />
            </div>
            
            {/* Direct Microphone Activation Button */}
            <button
              type="button"
              onClick={handleMicrophoneClick}
              className={`px-5 rounded-xl border transition flex items-center justify-center cursor-pointer ${
                isLocalRecording || voiceState === "LISTENING"
                  ? "bg-cyan-400 text-black border-cyan-300 shadow-[0_0_25px_#00f0ff] animate-pulse"
                  : "bg-[#051124] hover:bg-cyan-950/80 border-cyan-500/40 text-cyan-400 hover:shadow-[0_0_15px_rgba(0,240,255,0.3)]"
              }`}
              title="Click to speak command to NOVA"
            >
              <Mic className="h-5 w-5" />
            </button>

            {/* Run Button */}
            <button
              type="submit"
              className="px-6 rounded-xl bg-gradient-to-r from-cyan-500 to-sky-600 hover:from-cyan-400 hover:to-sky-500 text-black font-black text-xs uppercase tracking-wider transition flex items-center space-x-2 shadow-[0_0_20px_rgba(0,240,255,0.4)] cursor-pointer"
            >
              <Play className="h-4 w-4 fill-current" />
              <span>ENGAGE</span>
            </button>
          </form>
        </main>

        {/* RIGHT PANEL: Tabbed Matrix (Tools, Security Audit, Memory, Archive) */}
        <aside className="w-96 border-l border-cyan-500/20 bg-[#030914]/85 p-5 flex flex-col space-y-4 overflow-hidden backdrop-blur-md">
          
          {/* Tabs Selector Bar */}
          <div className="grid grid-cols-4 gap-1 p-1 bg-[#051124] rounded-xl border border-cyan-500/30 text-[10px] font-bold">
            <button
              onClick={() => { soundFx.playButtonClick(); setRightPanelTab("tools"); }}
              className={`py-1.5 rounded-lg transition text-center ${
                rightPanelTab === "tools" ? "bg-cyan-500 text-black shadow-[0_0_10px_#00f0ff]" : "text-cyan-400 hover:text-white"
              }`}
            >
              TOOLS ({tools.length})
            </button>
            <button
              onClick={() => { soundFx.playButtonClick(); setRightPanelTab("audit"); }}
              className={`py-1.5 rounded-lg transition text-center ${
                rightPanelTab === "audit" ? "bg-cyan-500 text-black shadow-[0_0_10px_#00f0ff]" : "text-cyan-400 hover:text-white"
              }`}
            >
              AUDIT
            </button>
            <button
              onClick={() => { soundFx.playButtonClick(); setRightPanelTab("memory"); }}
              className={`py-1.5 rounded-lg transition text-center ${
                rightPanelTab === "memory" ? "bg-cyan-500 text-black shadow-[0_0_10px_#00f0ff]" : "text-cyan-400 hover:text-white"
              }`}
            >
              MEMORY ({memories.length})
            </button>
            <button
              onClick={() => { soundFx.playButtonClick(); setRightPanelTab("archive"); }}
              className={`py-1.5 rounded-lg transition text-center ${
                rightPanelTab === "archive" ? "bg-cyan-500 text-black shadow-[0_0_10px_#00f0ff]" : "text-cyan-400 hover:text-white"
              }`}
            >
              HISTORY
            </button>
          </div>

          {/* TAB 1: TOOL MATRIX */}
          {rightPanelTab === "tools" && (
            <div className="flex-1 flex flex-col space-y-3 min-h-0">
              {/* Search Bar */}
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-cyan-600" />
                <input
                  type="text"
                  value={toolSearch}
                  onChange={(e) => setToolSearch(e.target.value)}
                  placeholder="FILTER TOOLS..."
                  className="w-full bg-[#051124] border border-cyan-500/30 rounded-lg pl-9 pr-3 py-1.5 text-[11px] text-cyan-200 placeholder-cyan-700/60 focus:outline-none focus:border-cyan-400"
                />
              </div>

              {/* Tools List */}
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {filteredTools.map((tool) => (
                  <div
                    key={tool.name}
                    onClick={() => {
                      soundFx.playButtonClick();
                      setSelectedTool(selectedTool === tool.name ? null : tool.name);
                    }}
                    className="p-2.5 rounded-lg bg-[#051124]/85 hover:bg-cyan-950/70 border border-cyan-500/20 cursor-pointer transition"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] font-bold text-cyan-300">{tool.name}</span>
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${getRiskColor(tool.risk_level)}`}>
                        {tool.risk_level}
                      </span>
                    </div>
                    {selectedTool === tool.name && (
                      <div className="mt-2 pt-2 border-t border-cyan-500/20 text-[10px] text-slate-300 space-y-1">
                        <p>{tool.description}</p>
                        <div className="text-cyan-400 font-bold">PERMISSION: {tool.required_permission}</div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: SECURITY AUDIT STREAM */}
          {rightPanelTab === "audit" && (
            <div className="flex-1 flex flex-col space-y-2 min-h-0">
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {auditLogs.length === 0 ? (
                  <div className="text-center text-[10px] text-slate-600 py-6 border border-dashed border-cyan-500/20 rounded-xl">
                    NO SECURITY AUDIT EVENTS RECORDED
                  </div>
                ) : (
                  auditLogs.map((log, idx) => (
                    <div key={log.id ? `audit-${log.id}` : `audit-${idx}`} className="p-2.5 rounded-lg bg-[#051124] border border-cyan-500/20 text-[10px] space-y-1">
                      <div className="flex justify-between items-center text-slate-500">
                        <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                        <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                          log.permission_status === "ALLOWED" ? "text-emerald-400 bg-emerald-950/80" :
                          log.permission_status === "DENIED" ? "text-red-400 bg-red-950/80" :
                          "text-amber-400 bg-amber-950/80"
                        }`}>
                          {log.permission_status}
                        </span>
                      </div>
                      <div className="text-cyan-300">
                        TOOL: <span className="font-bold text-white">{log.tool_name}</span>
                      </div>
                      <div className="text-slate-400 truncate text-[9px]">
                        ARGS: {log.arguments}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 3: CONTEXT MEMORY MATRIX */}
          {rightPanelTab === "memory" && (
            <div className="flex-1 flex flex-col space-y-2 min-h-0">
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {memories.length === 0 ? (
                  <div className="text-center text-[10px] text-slate-600 py-6 border border-dashed border-cyan-500/20 rounded-xl">
                    NO REMEMBERED PREFERENCES IN SQLITE
                  </div>
                ) : (
                  memories.map((m, idx) => (
                    <div key={m.id ? `mem-id-${m.id}` : `mem-${m.key}-${idx}`} className="p-2.5 rounded-lg bg-[#051124] border border-cyan-500/20 text-[10px] space-y-1">
                      <div className="flex justify-between items-center">
                        <span className="text-cyan-300 font-bold">{m.key}</span>
                        <div className="flex items-center space-x-2">
                          <span className="text-[8px] text-cyan-400 font-mono uppercase bg-cyan-950 px-1.5 py-0.5 rounded border border-cyan-800/40">
                            {m.category}
                          </span>
                          <button
                            onClick={() => deleteMemoryItem(m.key)}
                            className="text-slate-500 hover:text-red-400 transition"
                            title="Forget this memory"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                      <div className="text-slate-300 truncate">{m.value}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 4: MISSION ARCHIVE */}
          {rightPanelTab === "archive" && (
            <div className="flex-1 flex flex-col space-y-2 min-h-0">
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {recentTasks.length === 0 ? (
                  <div className="text-center text-[10px] text-slate-600 py-6 border border-dashed border-cyan-500/20 rounded-xl">
                    NO MISSIONS ARCHIVED
                  </div>
                ) : (
                  recentTasks.map((task, idx) => (
                    <div
                      key={task.id ? `task-${task.id}` : `task-${idx}`}
                      onClick={() => {
                        soundFx.playButtonClick();
                        fetch(`${API_BASE}/api/tasks/${task.id}`)
                          .then(r => r.json())
                          .then(data => { setTaskDetails(data); setCurrentTaskId(task.id); });
                      }}
                      className="p-2.5 rounded-lg bg-[#051124] hover:bg-cyan-950/70 border border-cyan-500/20 text-[10px] space-y-1 cursor-pointer transition"
                    >
                      <div className="flex justify-between text-slate-500">
                        <span>{new Date(task.created_at).toLocaleTimeString()}</span>
                        <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                          task.state === "COMPLETED" ? "text-emerald-400 bg-emerald-950" :
                          task.state === "FAILED" ? "text-red-400 bg-red-950" :
                          "text-cyan-400 bg-cyan-950"
                        }`}>
                          {task.state}
                        </span>
                      </div>
                      <div className="text-cyan-200 truncate font-semibold">
                        "{task.user_request}"
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

        </aside>
      </div>

    </div>
  );
}
