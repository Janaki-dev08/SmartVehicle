import React from 'react';
import { TelemetryFrame } from '../types/simulation';
import { Cpu, Radio, Sparkles, Shield, Bot, Compass } from 'lucide-react';

interface HeaderProps {
  telemetry: TelemetryFrame | null;
  wsConnected: boolean;
}

export const Header: React.FC<HeaderProps> = ({ telemetry, wsConnected }) => {
  const isCarlaConnected = telemetry?.carla.connected ?? false;
  const driverMode = (telemetry?.driver || 'META').toUpperCase();

  // Dynamic driver badge configuration
  const getDriverBadgeConfig = (mode: string) => {
    switch (mode) {
      case 'META':
        return {
          label: 'AI AGENT (PPO)',
          sub: 'Deep RL Policy',
          bg: 'bg-gradient-to-r from-purple-900/60 to-indigo-900/60 border-purple-500/50 text-purple-200',
          dot: 'bg-purple-400 animate-pulse shadow-purple-500/50',
          icon: Bot
        };
      case 'CARLA':
        return {
          label: 'CARLA HIL',
          sub: 'Hardware-in-Loop',
          bg: 'bg-gradient-to-r from-cyan-900/60 to-blue-900/60 border-cyan-500/50 text-cyan-200',
          dot: 'bg-cyan-400 animate-pulse shadow-cyan-500/50',
          icon: Radio
        };
      case 'NONE':
      default:
        return {
          label: 'AUTONOMOUS (A*)',
          sub: 'Rule-Based Supervisor',
          bg: 'bg-gradient-to-r from-amber-900/60 to-orange-900/60 border-amber-500/50 text-amber-200',
          dot: 'bg-amber-400 shadow-amber-500/50',
          icon: Compass
        };
    }
  };

  const driverBadge = getDriverBadgeConfig(driverMode);
  const DriverIcon = driverBadge.icon;

  return (
    <header className="bg-dark-800/95 backdrop-blur border-b border-dark-600 px-5 py-3 flex flex-wrap items-center justify-between gap-4 select-none shadow-xl z-20">
      {/* Title & Branding */}
      <div className="flex items-center space-x-3.5">
        <div className="p-2.5 bg-gradient-to-br from-blue-600/20 to-cyan-500/20 border border-blue-500/40 rounded-xl text-blue-400 shadow-lg shadow-blue-900/20 flex items-center justify-center">
          <Cpu className="w-6 h-6 animate-pulse text-accent-cyan" />
        </div>
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-extrabold text-white tracking-wide flex items-center gap-2">
              Adaptive Path Planning & Collision Avoidance
            </h1>
            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-gradient-to-r from-blue-500/20 to-cyan-500/20 text-accent-cyan border border-cyan-500/30 flex items-center gap-1 shadow-sm">
              <Sparkles className="w-3 h-3 text-cyan-300" />
              Indian Roads v2.0
            </span>
          </div>
          <p className="text-xs text-gray-400 flex items-center gap-2 mt-0.5">
            <span>YOLO Perception</span>
            <span className="text-dark-600">•</span>
            <span>Adaptive A* Lattice</span>
            <span className="text-dark-600">•</span>
            <span>PPO RL Model</span>
            <span className="text-dark-600">•</span>
            <span>TTC Safety Layer</span>
          </p>
        </div>
      </div>

      {/* Driverless & Active Driver Mode Badges */}
      <div className="flex items-center gap-2.5">
        {/* Mode Pill */}
        <div className="px-3 py-1.5 bg-dark-900/90 border border-dark-600 rounded-lg flex items-center space-x-2 text-xs font-mono shadow-inner">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
          <span className="text-gray-400">MODE:</span>
          <span className="text-emerald-400 font-bold tracking-wider">AUTONOMOUS</span>
        </div>

        {/* Dynamic Driver Selection Badge */}
        <div className={`px-3.5 py-1.5 border rounded-lg flex items-center space-x-2 text-xs font-mono shadow-lg transition-all duration-300 ${driverBadge.bg}`}>
          <span className={`w-2 h-2 rounded-full ${driverBadge.dot}`}></span>
          <DriverIcon className="w-3.5 h-3.5" />
          <div className="flex flex-col">
            <span className="text-[11px] font-extrabold tracking-wide">{driverBadge.label}</span>
          </div>
        </div>

        {/* Human Control Pill */}
        <div className="px-3 py-1.5 bg-red-950/30 border border-red-500/30 rounded-lg flex items-center space-x-1.5 text-xs font-mono">
          <Shield className="w-3.5 h-3.5 text-red-400" />
          <span className="text-gray-400">Human:</span>
          <span className="text-red-400 font-bold">DISABLED</span>
        </div>
      </div>

      {/* Connectivity Status Indicators */}
      <div className="flex items-center space-x-3">
        {/* CARLA Status Pill */}
        <div
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold border flex items-center space-x-2 shadow-sm transition-all duration-300 ${
            isCarlaConnected
              ? 'bg-emerald-950/50 border-emerald-500/50 text-emerald-300 shadow-emerald-950/40'
              : 'bg-amber-950/40 border-amber-500/40 text-amber-300 shadow-amber-950/30'
          }`}
        >
          <Radio className={`w-3.5 h-3.5 ${isCarlaConnected ? 'text-emerald-400 animate-pulse' : 'text-amber-400'}`} />
          <span className="text-[11px]">
            {isCarlaConnected ? 'CARLA CONNECTED' : 'CARLA DISCONNECTED (STANDALONE)'}
          </span>
        </div>

        {/* WebSocket Stream Indicator */}
        <div className="flex items-center space-x-1.5 bg-dark-900/80 border border-dark-700 px-2.5 py-1.5 rounded-lg text-xs font-mono text-gray-300">
          <span
            className={`w-2 h-2 rounded-full ${
              wsConnected ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]' : 'bg-red-500 animate-ping'
            }`}
          />
          <span className="text-[11px] font-medium">20 Hz Stream</span>
        </div>
      </div>
    </header>
  );
};

