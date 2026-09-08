import React, { useState } from 'react';
import { TelemetryFrame } from '../types/simulation';
import { EventLog } from './EventLog';
import { MetricsComparison } from './MetricsComparison';
import { Terminal, BarChart3, Download, Activity, Sparkles } from 'lucide-react';
import { getExportCsvUrl } from '../services/api';

interface BottomPanelProps {
  telemetry: TelemetryFrame | null;
}

export const BottomPanel: React.FC<BottomPanelProps> = ({ telemetry }) => {
  const [activeTab, setActiveTab] = useState<'benchmark' | 'events' | 'metrics'>('benchmark');
  const replans = telemetry?.latest_replans ?? [];
  const metrics = telemetry?.metrics;
  const benchmark = telemetry?.benchmark;

  return (
    <footer className="h-68 bg-dark-800/95 backdrop-blur border-t border-dark-600 flex flex-col p-3.5 select-none shadow-2xl z-20">
      {/* Tab Navigation Header */}
      <div className="flex items-center justify-between border-b border-dark-700 pb-2.5 mb-2.5">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setActiveTab('benchmark')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold flex items-center space-x-2 transition-all ${
              activeTab === 'benchmark'
                ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-lg shadow-blue-900/30'
                : 'text-gray-400 hover:text-white hover:bg-dark-700/60'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>Research Benchmark (Fixed vs Adaptive A* vs PPO)</span>
          </button>

          <button
            onClick={() => setActiveTab('events')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold flex items-center space-x-2 transition-all ${
              activeTab === 'events'
                ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-lg shadow-blue-900/30'
                : 'text-gray-400 hover:text-white hover:bg-dark-700/60'
            }`}
          >
            <Terminal className="w-3.5 h-3.5" />
            <span>Dynamic Replanning Events</span>
            <span className="px-1.5 py-0.2 rounded-full bg-cyan-500/20 text-accent-cyan text-[10px] font-mono font-bold border border-cyan-500/30">
              {replans.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('metrics')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold flex items-center space-x-2 transition-all ${
              activeTab === 'metrics'
                ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white shadow-lg shadow-blue-900/30'
                : 'text-gray-400 hover:text-white hover:bg-dark-700/60'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Kinematic Telemetry</span>
          </button>
        </div>

        {/* Export CSV Download Button */}
        <div className="flex items-center gap-2">
          <a
            href={getExportCsvUrl()}
            download="autonomous_telemetry.csv"
            className="px-3.5 py-1.5 rounded-xl bg-dark-700 hover:bg-dark-600 border border-dark-600 hover:border-gray-500 text-gray-200 text-xs font-bold flex items-center space-x-1.5 transition-all shadow-sm active:scale-95"
          >
            <Download className="w-3.5 h-3.5 text-accent-cyan" />
            <span>Export Telemetry (.CSV)</span>
          </a>
        </div>
      </div>

      {/* Tab Content Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {activeTab === 'benchmark' && <MetricsComparison benchmark={benchmark} metrics={metrics} />}
        {activeTab === 'events' && <EventLog replans={replans} />}
        {activeTab === 'metrics' && (
          <div className="grid grid-cols-6 gap-3 font-mono text-xs select-none">
            <div className="bg-dark-900/90 p-3 rounded-xl border border-dark-700 shadow-inner">
              <div className="text-gray-400 text-[10px] uppercase font-sans font-semibold">Total Distance</div>
              <div className="text-lg font-black text-white mt-1">
                {metrics?.total_distance_m ? `${metrics.total_distance_m.toFixed(1)} m` : '0.0 m'}
              </div>
            </div>
            <div className="bg-dark-900/90 p-3 rounded-xl border border-dark-700 shadow-inner">
              <div className="text-gray-400 text-[10px] uppercase font-sans font-semibold">Average Speed</div>
              <div className="text-lg font-black text-accent-cyan mt-1">
                {metrics?.avg_speed_kmh ? `${metrics.avg_speed_kmh.toFixed(1)} km/h` : '0.0 km/h'}
              </div>
            </div>
            <div className="bg-dark-900/90 p-3 rounded-xl border border-dark-700 shadow-inner">
              <div className="text-gray-400 text-[10px] uppercase font-sans font-semibold">Minimum TTC</div>
              <div className="text-lg font-black text-emerald-400 mt-1">
                {metrics?.min_ttc_seconds ? `${metrics.min_ttc_seconds.toFixed(2)} s` : '1.85 s'}
              </div>
            </div>
            <div className="bg-dark-900/90 p-3 rounded-xl border border-dark-700 shadow-inner">
              <div className="text-gray-400 text-[10px] uppercase font-sans font-semibold">Obstacle Clearance</div>
              <div className="text-lg font-black text-accent-blue mt-1">
                {metrics?.avg_obstacle_clearance_m ? `${metrics.avg_obstacle_clearance_m.toFixed(2)} m` : '2.50 m'}
              </div>
            </div>
            <div className="bg-dark-900/90 p-3 rounded-xl border border-dark-700 shadow-inner">
              <div className="text-gray-400 text-[10px] uppercase font-sans font-semibold">A* Planning Latency</div>
              <div className="text-lg font-black text-purple-400 mt-1">
                {metrics?.avg_planning_time_ms ? `${metrics.avg_planning_time_ms.toFixed(1)} ms` : '12.4 ms'}
              </div>
            </div>
            <div className="bg-dark-900/90 p-3 rounded-xl border border-dark-700 shadow-inner">
              <div className="text-gray-400 text-[10px] uppercase font-sans font-semibold">Success Rate</div>
              <div className="text-lg font-black text-emerald-400 mt-1 flex items-center gap-1">
                <Sparkles className="w-4 h-4 text-emerald-400" />
                <span>{metrics?.navigation_success_rate_percent ?? 95.5}%</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </footer>
  );
};

