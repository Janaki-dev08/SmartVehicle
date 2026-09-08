import React from 'react';
import { TelemetryFrame, RiskLevel, SupervisorAction } from '../types/simulation';
import { Gauge, ShieldAlert, ShieldCheck, AlertTriangle, Flame, Activity, Layers, Disc, Compass, Zap, Car, User, Bike } from 'lucide-react';

interface RightPanelProps {
  telemetry: TelemetryFrame | null;
}

export const RightPanel: React.FC<RightPanelProps> = ({ telemetry }) => {
  const veh = telemetry?.vehicle;
  const risk = telemetry?.risk;
  const action = telemetry?.action ?? 'CRUISING';
  const riskLevel: RiskLevel = risk?.risk_level ?? 'LOW';

  // Action badge styles
  const getActionBadge = (act: SupervisorAction) => {
    switch (act) {
      case 'EMERGENCY_BRAKE':
        return {
          bg: 'bg-red-950/90 border-red-500 text-red-300 shadow-[0_0_15px_rgba(239,68,68,0.5)] animate-pulse',
          label: 'EMERGENCY BRAKE',
          icon: Flame
        };
      case 'EVASIVE_REPLAN':
        return {
          bg: 'bg-amber-950/90 border-amber-500 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.4)]',
          label: 'EVASIVE REPLAN',
          icon: Zap
        };
      case 'SLOWING':
        return {
          bg: 'bg-yellow-950/90 border-yellow-500 text-yellow-300',
          label: 'DECELERATING',
          icon: Activity
        };
      case 'DESTINATION_REACHED':
        return {
          bg: 'bg-emerald-950/90 border-emerald-500 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.4)]',
          label: 'GOAL REACHED',
          icon: ShieldCheck
        };
      default:
        return {
          bg: 'bg-blue-950/80 border-blue-500/80 text-blue-300',
          label: 'CRUISING',
          icon: Compass
        };
    }
  };

  const actionInfo = getActionBadge(action);
  const ActionIcon = actionInfo.icon;

  // Risk badge styles
  const getRiskBadge = (lvl: RiskLevel) => {
    switch (lvl) {
      case 'CRITICAL':
        return {
          bg: 'bg-red-600 text-white shadow-[0_0_15px_rgba(220,38,38,0.7)] animate-bounce',
          pillBg: 'border-red-500/80 bg-red-950/50',
          icon: Flame
        };
      case 'HIGH':
        return {
          bg: 'bg-orange-500 text-white shadow-[0_0_12px_rgba(249,115,22,0.6)]',
          pillBg: 'border-orange-500/80 bg-orange-950/50',
          icon: ShieldAlert
        };
      case 'MEDIUM':
        return {
          bg: 'bg-amber-500 text-black',
          pillBg: 'border-amber-500/80 bg-amber-950/50',
          icon: AlertTriangle
        };
      default:
        return {
          bg: 'bg-emerald-600 text-white',
          pillBg: 'border-emerald-500/80 bg-emerald-950/50',
          icon: ShieldCheck
        };
    }
  };

  const riskBadge = getRiskBadge(riskLevel);
  const RiskIcon = riskBadge.icon;

  const getObstacleIcon = (className: string) => {
    const lower = className.toLowerCase();
    if (lower.includes('pedestrian') || lower.includes('person')) return User;
    if (lower.includes('motorcycle') || lower.includes('bike') || lower.includes('scooter')) return Bike;
    return Car;
  };

  return (
    <aside className="w-84 bg-dark-800/90 backdrop-blur border-l border-dark-600 flex flex-col h-full overflow-y-auto p-4 space-y-4 text-sm select-none custom-scrollbar">
      {/* Vehicle Speedometer & Kinematics Card */}
      <div className="bg-gradient-to-b from-dark-800 to-dark-900 border border-dark-600 rounded-2xl p-4 shadow-xl space-y-3.5">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
            <Gauge className="w-3.5 h-3.5 text-accent-cyan" />
            <span>Vehicle Telemetry</span>
          </h2>
          <span className="text-[10px] font-mono text-gray-400">CanBUS 20Hz</span>
        </div>

        {/* Digital Speedometer Display */}
        <div className="bg-dark-900/90 border border-dark-700 rounded-xl p-3.5 flex items-center justify-between relative overflow-hidden shadow-inner">
          <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-blue-500/10 to-transparent pointer-events-none" />
          <div>
            <div className="text-4xl font-black text-white font-mono tracking-tight flex items-baseline gap-1">
              <span>{veh?.speed_kmh.toFixed(1) ?? '0.0'}</span>
              <span className="text-xs font-bold text-accent-cyan font-sans tracking-normal">km/h</span>
            </div>
            <div className="text-[11px] text-gray-400 font-mono mt-0.5">
              {veh?.speed_ms.toFixed(2) ?? '0.00'} m/s • Heading {veh?.heading_deg.toFixed(1) ?? '0.0'}°
            </div>
          </div>
          <div className="text-right z-10">
            <div className="px-2 py-1 rounded-lg bg-blue-500/20 text-blue-300 border border-blue-500/30 text-xs font-mono font-bold">
              {veh?.acceleration_ms2 ? `${veh.acceleration_ms2 > 0 ? '+' : ''}${veh.acceleration_ms2.toFixed(1)}` : '0.0'} m/s²
            </div>
            <div className="text-[9px] text-gray-400 uppercase mt-1 font-mono">Longitudinal Accel</div>
          </div>
        </div>

        {/* Steering & Pedal Actuators */}
        <div className="space-y-2.5 text-xs bg-dark-900/70 p-3 rounded-xl border border-dark-700">
          {/* Steering Angle */}
          <div>
            <div className="flex justify-between text-[11px] mb-1">
              <span className="text-gray-400 flex items-center gap-1">
                <Disc className="w-3 h-3 text-gray-400" />
                <span>Steering Angle</span>
              </span>
              <span className="font-mono text-gray-200 font-semibold">
                {(veh?.steering_angle ?? 0.0) > 0 ? 'Right +' : (veh?.steering_angle ?? 0.0) < 0 ? 'Left -' : ''}
                {Math.abs(veh?.steering_angle ?? 0.0).toFixed(2)} rad
              </span>
            </div>
            <div className="w-full bg-dark-700 h-2.5 rounded-full overflow-hidden relative border border-dark-600">
              <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-gray-400 z-10"></div>
              <div
                className={`h-full transition-all duration-75 ${
                  (veh?.steering_angle ?? 0) >= 0
                    ? 'bg-gradient-to-r from-accent-blue to-accent-cyan ml-[50%]'
                    : 'bg-gradient-to-l from-accent-blue to-accent-cyan float-right mr-[50%]'
                }`}
                style={{ width: `${Math.min(50, Math.abs((veh?.steering_angle ?? 0) * 50))}%` }}
              />
            </div>
          </div>

          {/* Throttle Gauge */}
          <div>
            <div className="flex justify-between text-[11px] mb-1">
              <span className="text-gray-400">Throttle Input</span>
              <span className="font-mono text-emerald-400 font-bold">{((veh?.throttle ?? 0) * 100).toFixed(0)}%</span>
            </div>
            <div className="w-full bg-dark-700 h-2 rounded-full overflow-hidden border border-dark-600">
              <div
                className="bg-gradient-to-r from-emerald-600 to-emerald-400 h-full transition-all duration-75"
                style={{ width: `${(veh?.throttle ?? 0) * 100}%` }}
              />
            </div>
          </div>

          {/* Brake Gauge */}
          <div>
            <div className="flex justify-between text-[11px] mb-1">
              <span className="text-gray-400">Brake Input</span>
              <span className="font-mono text-rose-400 font-bold">{((veh?.brake ?? 0) * 100).toFixed(0)}%</span>
            </div>
            <div className="w-full bg-dark-700 h-2 rounded-full overflow-hidden border border-dark-600">
              <div
                className="bg-gradient-to-r from-rose-600 to-rose-400 h-full transition-all duration-75"
                style={{ width: `${(veh?.brake ?? 0) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Safety & Risk Assessment Card */}
      <div className="bg-gradient-to-b from-dark-800 to-dark-900 border border-dark-600 rounded-2xl p-4 shadow-xl space-y-3.5">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-accent-amber" />
            <span>Safety Supervisor & Risk</span>
          </h2>
          <span className="text-[10px] font-mono text-gray-400">TTC Layer</span>
        </div>

        {/* Dynamic Risk & Action Badges */}
        <div className="grid grid-cols-2 gap-2">
          <div className={`p-2.5 rounded-xl border flex flex-col items-center justify-center transition-all ${riskBadge.pillBg}`}>
            <span className="text-[9px] font-bold text-gray-400 uppercase tracking-wider mb-1">Risk Classification</span>
            <div className={`px-3 py-1 rounded-lg text-xs font-extrabold flex items-center space-x-1.5 ${riskBadge.bg}`}>
              <RiskIcon className="w-3.5 h-3.5" />
              <span>{riskLevel}</span>
            </div>
          </div>

          <div className="bg-dark-900/90 p-2.5 rounded-xl border border-dark-700 flex flex-col items-center justify-center">
            <span className="text-[9px] font-bold text-gray-400 uppercase tracking-wider mb-1">Supervisor Actuation</span>
            <div className={`px-2.5 py-1 rounded-lg text-[11px] font-extrabold border text-center flex items-center space-x-1 ${actionInfo.bg}`}>
              <ActionIcon className="w-3 h-3" />
              <span>{actionInfo.label}</span>
            </div>
          </div>
        </div>

        {/* Time-To-Collision (TTC) & Spatial Clearance */}
        <div className="bg-dark-900/90 p-3 rounded-xl border border-dark-700 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-400">Time-To-Collision (TTC):</span>
            <span
              className={`font-mono font-black text-sm ${
                (risk?.min_ttc ?? 99) < 2.5
                  ? 'text-rose-400 animate-pulse'
                  : (risk?.min_ttc ?? 99) < 5.0
                  ? 'text-amber-400'
                  : 'text-emerald-400'
              }`}
            >
              {risk?.min_ttc !== null && risk?.min_ttc !== undefined ? `${risk.min_ttc.toFixed(1)} s` : 'SAFE (>10s)'}
            </span>
          </div>

          <div className="flex items-center justify-between text-[11px] text-gray-400 pt-1.5 border-t border-dark-700">
            <span>Nearest Obstacle:</span>
            <span className="text-white font-semibold capitalize">
              {risk?.nearest_obstacle
                ? `${risk.nearest_obstacle.class_name.replace('_', ' ')} (${risk.nearest_distance.toFixed(1)}m)`
                : 'None in Corridor'}
            </span>
          </div>

          <div className="flex items-center justify-between text-[11px] text-gray-400">
            <span>Lateral Clearance:</span>
            <span className="font-mono text-accent-cyan font-bold">
              {risk?.lateral_clearance ? `${risk.lateral_clearance.toFixed(1)} m` : '10.0 m'}
            </span>
          </div>
        </div>
      </div>

      {/* YOLO Road Entity Detections Card */}
      <div className="bg-gradient-to-b from-dark-800 to-dark-900 border border-dark-600 rounded-2xl p-4 shadow-xl flex-1 flex flex-col min-h-[170px]">
        <div className="flex items-center justify-between mb-2.5">
          <h2 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-purple-400" />
            <span>YOLO Detections ({telemetry?.perception.detected_objects_count ?? 0})</span>
          </h2>
          <span className="text-[10px] font-mono text-gray-400">Tracker Active</span>
        </div>

        <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 custom-scrollbar">
          {(telemetry?.perception.objects ?? []).length === 0 ? (
            <div className="text-xs text-gray-500 text-center py-6 font-mono">
              No road obstacles detected in sensor envelope
            </div>
          ) : (
            (telemetry?.perception.objects ?? []).map((obj) => {
              const ObsIcon = getObstacleIcon(obj.class_name);
              return (
                <div
                  key={obj.object_id}
                  className="bg-dark-900/90 border border-dark-700 rounded-xl p-2.5 text-xs flex items-center justify-between hover:border-gray-600 transition"
                >
                  <div className="flex items-center space-x-2.5">
                    <div className="p-1.5 rounded-lg bg-dark-700 text-gray-300">
                      <ObsIcon className="w-3.5 h-3.5" />
                    </div>
                    <div>
                      <div className="font-bold text-white capitalize flex items-center gap-1.5">
                        <span>{obj.class_name.replace('_', ' ')}</span>
                        <span className="text-[9px] font-mono px-1 rounded bg-dark-700 text-gray-400">
                          #{obj.object_id}
                        </span>
                      </div>
                      <div className="text-[10px] text-gray-400 font-mono">
                        Conf: {(obj.confidence * 100).toFixed(0)}% • Rel: {obj.relative_position ? `(${obj.relative_position[0].toFixed(1)}m, ${obj.relative_position[1].toFixed(1)}m)` : ''}
                      </div>
                    </div>
                  </div>

                  <div className="text-right font-mono">
                    <div className="text-amber-400 font-bold text-xs">{obj.distance.toFixed(1)}m</div>
                    <div className="text-[10px] text-gray-400">
                      {obj.velocity > 0.2 ? `${(obj.velocity * 3.6).toFixed(0)} km/h` : 'Static'}
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </aside>
  );
};

