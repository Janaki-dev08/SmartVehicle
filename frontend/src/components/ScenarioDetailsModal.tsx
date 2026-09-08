import React from 'react';
import { ScenarioData } from '../types/simulation';
import { X, Layers, AlertCircle, Shield, CheckCircle2 } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  scenarios: ScenarioData[];
  activeScenarioId?: string;
  onSelectScenario: (id: string) => void;
}

export const ScenarioDetailsModal: React.FC<Props> = ({
  isOpen,
  onClose,
  scenarios,
  activeScenarioId,
  onSelectScenario,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-dark-800 border border-dark-600 rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-4 border-b border-dark-600 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Layers className="w-5 h-5 text-accent-blue" />
            <h2 className="text-base font-bold text-white">
              Indian Road Autonomous Driving Benchmark Scenarios (10 Scenarios)
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-dark-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          {scenarios.map((sc) => {
            const isActive = sc.id === activeScenarioId;
            return (
              <div
                key={sc.id}
                className={`p-3 rounded-xl border transition ${
                  isActive
                    ? 'bg-accent-blue/10 border-accent-blue shadow-md'
                    : 'bg-dark-900/90 border-dark-700 hover:border-dark-500'
                }`}
              >
                <div className="flex items-start justify-between mb-1.5">
                  <div className="flex items-center space-x-1.5">
                    <span className="font-mono font-bold text-accent-cyan">{sc.id.toUpperCase()}</span>
                    <span className="font-semibold text-white">{sc.name}</span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                      sc.difficulty === 'Expert'
                        ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                        : sc.difficulty === 'Hard'
                        ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
                        : sc.difficulty === 'Medium'
                        ? 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30'
                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    }`}
                  >
                    {sc.difficulty}
                  </span>
                </div>

                <div className="text-gray-400 text-[11px] mb-2 leading-relaxed">{sc.description}</div>

                <div className="flex items-center justify-between text-[10px] text-gray-400 pt-2 border-t border-dark-700">
                  <span>Category: {sc.category}</span>
                  <span>Road Width: {sc.road_width}m</span>
                  <button
                    onClick={() => {
                      onSelectScenario(sc.id);
                      onClose();
                    }}
                    className="px-2 py-1 rounded bg-dark-700 hover:bg-accent-blue hover:text-white text-gray-200 font-medium transition"
                  >
                    {isActive ? 'Active' : 'Load Scenario'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
