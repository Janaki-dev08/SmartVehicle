import React, { useState } from 'react';
import { TelemetryFrame, ScenarioData } from '../types/simulation';
import { Play, Pause, RotateCcw, Radio, MapPin, Info, Navigation2, CheckCircle2, Bot, Compass, Cpu, Sliders, ShieldCheck } from 'lucide-react';
import { startSimulation, stopSimulation, resetSimulation, loadScenario, connectCarla, setDriver } from '../services/api';

interface LeftPanelProps {
  telemetry: TelemetryFrame | null;
  scenarios: ScenarioData[];
  onOpenScenarioModal: () => void;
  onOpenMapsModal: () => void;
}

export const LeftPanel: React.FC<LeftPanelProps> = ({
  telemetry,
  scenarios,
  onOpenScenarioModal,
  onOpenMapsModal,
}) => {
  const isRunning = telemetry?.running ?? false;
  const currentScenarioId = telemetry?.scenario?.id ?? 'scenario_02';
  const activeDriver = (telemetry?.driver || 'META').toUpperCase() as 'NONE' | 'META' | 'CARLA';

  const [selectedScenario, setSelectedScenario] = useState<string>(currentScenarioId);
  const [carlaHost, setCarlaHost] = useState<string>('localhost');
  const [carlaPort, setCarlaPort] = useState<number>(2000);
  const [isConnectingCarla, setIsConnectingCarla] = useState<boolean>(false);
  const [isChangingDriver, setIsChangingDriver] = useState<boolean>(false);
  const [actionMessage, setActionMessage] = useState<string>('');

  const showFeedback = (msg: string) => {
    setActionMessage(msg);
    setTimeout(() => setActionMessage(''), 3500);
  };

  const handleStart = async () => {
    await startSimulation();
    showFeedback('Autonomous simulation started');
  };

  const handleStop = async () => {
    await stopSimulation();
    showFeedback('Autonomous simulation paused');
  };

  const handleReset = async () => {
    await resetSimulation();
    showFeedback('Simulation reset to origin');
  };

  const handleScenarioChange = async (scId: string) => {
    setSelectedScenario(scId);
    await loadScenario(scId);
    showFeedback(`Loaded scenario: ${scId}`);
  };

  const handleDriverChange = async (newDriver: 'NONE' | 'META' | 'CARLA') => {
    setIsChangingDriver(true);
    try {
      const res = await setDriver(newDriver);
      showFeedback(res.message || `Driver mode set to ${newDriver}`);
    } catch (e) {
      showFeedback(`Failed to change driver: ${e}`);
    } finally {
      setIsChangingDriver(false);
    }
  };

  const handleCarlaConnect = async () => {
    setIsConnectingCarla(true);
    const res = await connectCarla(carlaHost, carlaPort);
    setIsConnectingCarla(false);
    showFeedback(res.connected ? 'Connected to CARLA server' : res.message || 'CARLA not reachable — running in standalone mode');
  };

  const activeScenarioObj = scenarios.find((s) => s.id === selectedScenario) || telemetry?.scenario;

  const driverOptions: Array<{
    id: 'META' | 'NONE' | 'CARLA';
    name: string;
    subtext: string;
    icon: React.ComponentType<{ className?: string }>;
    accentColor: string;
  }> = [
    {
      id: 'META',
      name: 'AI PPO Policy Model',
      subtext: 'Neural Deep RL Agent with Zero-Delay Inference',
      icon: Bot,
      accentColor: 'border-purple-500/60 bg-purple-950/30 text-purple-300'
    },
    {
      id: 'NONE',
      name: 'Rule-Based Autonomous',
      subtext: 'Deterministic Adaptive A* Lattice & TTC Supervisor',
      icon: Compass,
      accentColor: 'border-amber-500/60 bg-amber-950/30 text-amber-300'
    },
    {
      id: 'CARLA',
      name: 'CARLA HIL RPC',
      subtext: 'Hardware-in-the-Loop Simulator Synchronizer',
      icon: Radio,
      accentColor: 'border-cyan-500/60 bg-cyan-950/30 text-cyan-300'
    }
  ];

  return (
    <aside className="w-84 bg-dark-800/90 backdrop-blur border-r border-dark-600 flex flex-col h-full overflow-y-auto p-4 space-y-4 text-sm select-none custom-scrollbar">
      {/* Simulation Execution Controls Card */}
      <div className="bg-gradient-to-b from-dark-800 to-dark-900 border border-dark-600 rounded-2xl p-4 shadow-xl">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
            <Sliders className="w-3.5 h-3.5 text-accent-cyan" />
            <span>Simulation Controls</span>
          </h2>
          <span
            className={`text-[10px] font-mono px-2.5 py-0.5 rounded-full font-bold border transition-all ${
              isRunning
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 animate-pulse'
                : 'bg-dark-700 text-gray-400 border-dark-600'
            }`}
          >
            {isRunning ? '● RUNNING' : '○ PAUSED'}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={handleStart}
            disabled={isRunning}
            className={`py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center space-x-1.5 transition-all shadow-md active:scale-95 ${
              isRunning
                ? 'bg-dark-700/60 text-gray-500 cursor-not-allowed border border-dark-600'
                : 'bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white shadow-emerald-950/50 hover:shadow-emerald-600/30'
            }`}
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Start</span>
          </button>

          <button
            onClick={handleStop}
            disabled={!isRunning}
            className={`py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center space-x-1.5 transition-all shadow-md active:scale-95 ${
              !isRunning
                ? 'bg-dark-700/60 text-gray-500 cursor-not-allowed border border-dark-600'
                : 'bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white shadow-amber-950/50 hover:shadow-amber-600/30'
            }`}
          >
            <Pause className="w-3.5 h-3.5 fill-current" />
            <span>Stop</span>
          </button>

          <button
            onClick={handleReset}
            className="py-2.5 px-3 rounded-xl font-bold text-xs bg-dark-700/80 hover:bg-dark-600 text-gray-200 border border-dark-600 hover:border-gray-500 flex items-center justify-center space-x-1.5 transition-all active:scale-95 shadow-sm"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset</span>
          </button>
        </div>

        {actionMessage && (
          <div className="mt-3 p-2 rounded-lg bg-dark-900/90 border border-accent-cyan/30 text-[11px] text-center text-accent-cyan flex items-center justify-center gap-1.5 font-medium animate-fadeIn">
            <CheckCircle2 className="w-3.5 h-3.5 text-accent-cyan" />
            <span>{actionMessage}</span>
          </div>
        )}
      </div>

      {/* Driver Mode Selection Card */}
      <div className="bg-gradient-to-b from-dark-800 to-dark-900 border border-dark-600 rounded-2xl p-4 shadow-xl space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            <span>Driver Mode Selection</span>
          </h2>
          <span className="text-[10px] font-mono text-gray-400">PPO / Rule / HIL</span>
        </div>

        <div className="space-y-2">
          {driverOptions.map((opt) => {
            const isSelected = activeDriver === opt.id;
            const Icon = opt.icon;
            return (
              <button
                key={opt.id}
                onClick={() => handleDriverChange(opt.id)}
                disabled={isChangingDriver}
                className={`w-full text-left p-2.5 rounded-xl border transition-all flex items-start gap-2.5 relative ${
                  isSelected
                    ? `${opt.accentColor} shadow-lg ring-1 ring-white/10`
                    : 'border-dark-700 bg-dark-800/50 hover:bg-dark-800 text-gray-400 hover:text-gray-200'
                }`}
              >
                <div
                  className={`p-1.5 rounded-lg ${
                    isSelected ? 'bg-white/10 text-white' : 'bg-dark-700 text-gray-400'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <div className={`text-xs font-bold ${isSelected ? 'text-white' : 'text-gray-300'}`}>
                      {opt.name}
                    </div>
                    {isSelected && (
                      <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                    )}
                  </div>
                  <p className="text-[10px] text-gray-400 leading-tight mt-0.5">
                    {opt.subtext}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Scenario Selector Card */}
      <div className="bg-gradient-to-b from-dark-800 to-dark-900 border border-dark-600 rounded-2xl p-4 shadow-xl space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-accent-amber" />
            <span>Scenario Pack ({scenarios.length || 10})</span>
          </h2>
          <button
            onClick={onOpenScenarioModal}
            className="text-[11px] text-accent-blue hover:text-blue-300 flex items-center space-x-1 font-semibold transition"
          >
            <Info className="w-3 h-3" />
            <span>Details</span>
          </button>
        </div>

        <select
          value={selectedScenario}
          onChange={(e) => handleScenarioChange(e.target.value)}
          className="w-full bg-dark-800/90 border border-dark-600 rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-accent-blue focus:ring-1 focus:ring-accent-blue font-medium"
        >
          {scenarios.map((sc) => (
            <option key={sc.id} value={sc.id}>
              {sc.id.toUpperCase()}: {sc.name} ({sc.difficulty})
            </option>
          ))}
        </select>

        {activeScenarioObj && (
          <div className="bg-dark-900/90 border border-dark-700 rounded-xl p-3 text-xs space-y-2">
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div>
                <span className="text-gray-400 block text-[10px]">Category</span>
                <span className="text-gray-200 font-semibold">{activeScenarioObj.category}</span>
              </div>
              <div>
                <span className="text-gray-400 block text-[10px]">Road Width</span>
                <span className="text-gray-200 font-mono font-semibold">{activeScenarioObj.road_width} m</span>
              </div>
            </div>
            <p className="text-[11px] text-gray-400 leading-relaxed pt-2 border-t border-dark-700">
              {activeScenarioObj.description}
            </p>
          </div>
        )}
      </div>

      {/* CARLA RPC Connection Card */}
      <div className="bg-gradient-to-b from-dark-800 to-dark-900 border border-dark-600 rounded-2xl p-4 shadow-xl space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-cyan-400" />
            <span>CARLA Simulator RPC</span>
          </span>
        </h2>

        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <label className="text-[10px] text-gray-400 block mb-0.5">Host</label>
            <input
              type="text"
              value={carlaHost}
              onChange={(e) => setCarlaHost(e.target.value)}
              className="w-full bg-dark-800 border border-dark-600 rounded-lg p-2 text-xs text-white font-mono focus:border-cyan-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="text-[10px] text-gray-400 block mb-0.5">Port</label>
            <input
              type="number"
              value={carlaPort}
              onChange={(e) => setCarlaPort(Number(e.target.value))}
              className="w-full bg-dark-800 border border-dark-600 rounded-lg p-2 text-xs text-white font-mono focus:border-cyan-500 focus:outline-none"
            />
          </div>
        </div>

        <button
          onClick={handleCarlaConnect}
          disabled={isConnectingCarla}
          className="w-full py-2 rounded-xl bg-dark-700 hover:bg-dark-600 text-xs font-semibold border border-dark-600 text-gray-200 transition shadow-sm hover:border-gray-500 active:scale-95"
        >
          {isConnectingCarla ? 'Connecting...' : 'Connect to CARLA Server'}
        </button>

        <p className="text-[10px] text-gray-500 leading-tight">
          Default: <span className="font-mono text-gray-400">localhost:2000</span>. Standalone simulator operates automatically when CARLA is offline.
        </p>
      </div>

      {/* High-Level Route & Google Maps Card */}
      <div className="bg-gradient-to-b from-dark-800 to-dark-900 border border-dark-600 rounded-2xl p-4 shadow-xl space-y-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <Navigation2 className="w-3.5 h-3.5 text-accent-blue" />
            <span>High-Level Route</span>
          </span>
        </h2>

        <div className="text-xs space-y-1.5 bg-dark-900/80 p-2.5 rounded-xl border border-dark-700">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-gray-400">Target Distance:</span>
            <span className="font-mono text-white font-bold">
              {telemetry?.vehicle.destination_distance_m?.toFixed(1) ?? '120.0'} m
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-gray-400">Route Geometry:</span>
            <span className="font-mono text-accent-cyan font-semibold">OSRM Global Path</span>
          </div>
        </div>

        <button
          onClick={onOpenMapsModal}
          className="w-full py-2 rounded-xl bg-accent-blue/15 hover:bg-accent-blue/25 border border-accent-blue/40 text-accent-blue text-xs font-bold transition flex items-center justify-center space-x-1.5 shadow-sm active:scale-95"
        >
          <MapPin className="w-3.5 h-3.5" />
          <span>Configure Global Route (OSRM)</span>
        </button>
      </div>
    </aside>
  );
};

