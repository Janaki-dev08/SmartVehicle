import React from 'react';
import { ReplanEvent } from '../types/simulation';

interface EventLogProps {
  replans: ReplanEvent[];
}

export const EventLog: React.FC<EventLogProps> = ({ replans }) => {

  return (
    <div className="flex flex-col h-full space-y-2 select-none font-mono text-xs">
      {/* Event List Container */}
      <div className="flex-1 overflow-y-auto bg-dark-900 border border-dark-700 rounded-xl p-3 space-y-2 font-mono">
        {replans.length === 0 ? (
          <div className="text-gray-500 text-center py-6">
            Autonomous event recorder active. No safety events triggered yet.
          </div>
        ) : (
          replans.map((evt) => (
            <div
              key={evt.id}
              className="bg-dark-800/90 border border-dark-600 rounded-lg p-2 flex items-start justify-between space-x-3 text-[11px]"
            >
              <div className="flex items-start space-x-2">
                <span className="px-1.5 py-0.5 rounded bg-accent-cyan/20 text-accent-cyan font-bold border border-accent-cyan/30 text-[10px]">
                  REPLAN #{evt.id}
                </span>
                <div>
                  <div className="text-white font-medium">{evt.reason}</div>
                  <div className="text-[10px] text-gray-400">
                    Trajectory: {evt.prev_points} pts → {evt.new_points} pts
                  </div>
                </div>
              </div>

              <div className="text-right">
                <span className="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-400 font-bold text-[10px]">
                  {evt.latency_ms} ms
                </span>
                <div className="text-[9px] text-gray-500 mt-0.5">
                  {new Date(evt.timestamp * 1000).toLocaleTimeString()}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
