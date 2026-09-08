import React, { useRef, useEffect, useState } from 'react';
import { TelemetryFrame, DetectedObject } from '../types/simulation';
import { ZoomIn, ZoomOut, Maximize2, ShieldAlert, Eye, Compass } from 'lucide-react';

interface CanvasProps {
  telemetry: TelemetryFrame | null;
}

export const SimulationCanvas: React.FC<CanvasProps> = ({ telemetry }) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [zoom, setZoom] = useState<number>(1.0);
  const [showPredictions, setShowPredictions] = useState<boolean>(true);
  const [showOccupancy, setShowOccupancy] = useState<boolean>(true);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Handle high-DPI scaling
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.parentElement?.clientWidth || 800;
    const height = canvas.parentElement?.clientHeight || 550;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    // Canvas coordinate transforms:
    // Vehicle is positioned near bottom center (X=0, Y=0 in vehicle frame)
    // Canvas X-axis = Lateral Y (Left is negative, Right is positive)
    // Canvas Y-axis = Longitudinal X (Up is positive distance ahead)
    const originX = width / 2;
    const originY = height - 90; // Vehicle bumper origin
    const pixelsPerMeter = 11 * zoom;

    const toCanvasX = (y_m: number) => originX + y_m * pixelsPerMeter;
    const toCanvasY = (x_m: number) => originY - x_m * pixelsPerMeter;

    // 1. Clear Background
    ctx.fillStyle = '#0f172a'; // Deep road terrain background
    ctx.fillRect(0, 0, width, height);

    // 2. Draw Unstructured Road Terrain
    const roadWidth_m = telemetry?.road_width ?? 8.0;
    const halfWidth_m = roadWidth_m / 2.0;

    const roadLeftPx = toCanvasX(-halfWidth_m);
    const roadRightPx = toCanvasX(halfWidth_m);

    // Road Shoulder (Dirt/Unstructured edge)
    ctx.fillStyle = '#261e14';
    ctx.fillRect(roadLeftPx - 40, 0, roadRightPx - roadLeftPx + 80, height);

    // Asphalt Road Surface
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(roadLeftPx, 0, roadRightPx - roadLeftPx, height);

    // Unstructured soft road boundaries
    ctx.strokeStyle = '#64748b';
    ctx.lineWidth = 3;
    ctx.setLineDash([12, 10]);
    ctx.beginPath();
    ctx.moveTo(roadLeftPx, 0);
    ctx.lineTo(roadLeftPx, height);
    ctx.moveTo(roadRightPx, 0);
    ctx.lineTo(roadRightPx, height);
    ctx.stroke();
    ctx.setLineDash([]);

    // Road Centerline (Faded/Dashed Indian road markings)
    ctx.strokeStyle = '#475569';
    ctx.lineWidth = 2;
    ctx.setLineDash([15, 25]);
    ctx.beginPath();
    ctx.moveTo(originX, 0);
    ctx.lineTo(originX, height);
    ctx.stroke();
    ctx.setLineDash([]);

    // 3. Metric Distance Grid Lines
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1;
    ctx.font = '10px monospace';
    ctx.fillStyle = '#64748b';

    for (let d = 10; d <= 70; d += 10) {
      const yPx = toCanvasY(d);
      if (yPx >= 0 && yPx <= height) {
        ctx.beginPath();
        ctx.moveTo(roadLeftPx - 30, yPx);
        ctx.lineTo(roadRightPx + 30, yPx);
        ctx.stroke();
        ctx.fillText(`+${d}m`, roadRightPx + 8, yPx - 3);
      }
    }

    // 4. Global Navigation Reference Route (Blue Line)
    const globalPath = telemetry?.planner.global_path ?? [];
    if (globalPath.length >= 2) {
      ctx.strokeStyle = 'rgba(59, 130, 246, 0.45)';
      ctx.lineWidth = 6;
      ctx.beginPath();
      globalPath.forEach((pt, idx) => {
        // Approximate relative conversion for visualizer
        const cx = toCanvasX(pt[1] - (telemetry?.vehicle.position.y || 0));
        const cy = toCanvasY(pt[0] - (telemetry?.vehicle.position.x || 0));
        if (idx === 0) ctx.moveTo(cx, cy);
        else ctx.lineTo(cx, cy);
      });
      ctx.stroke();
    }

    // 5. Adaptive A* Planned Trajectory (Glowing Cyan Line)
    const localPath = telemetry?.planner.local_path ?? [];
    if (localPath.length >= 2) {
      ctx.shadowColor = '#06b6d4';
      ctx.shadowBlur = 10;
      ctx.strokeStyle = '#06b6d4';
      ctx.lineWidth = 3.5;
      ctx.beginPath();
      localPath.forEach((pt, idx) => {
        const cx = toCanvasX(pt[1]);
        const cy = toCanvasY(pt[0]);
        if (idx === 0) ctx.moveTo(cx, cy);
        else ctx.lineTo(cx, cy);
      });
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Pure Pursuit Lookahead Target Point
      const targetPt = telemetry?.planner.lookahead_target;
      if (targetPt) {
        const tx = toCanvasX(targetPt[1]);
        const ty = toCanvasY(targetPt[0]);
        ctx.fillStyle = '#22d3ee';
        ctx.beginPath();
        ctx.arc(tx, ty, 5, 0, 2 * Math.PI);
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
    }

    // 6. Render Dynamic & Static Obstacles
    const obstacles: DetectedObject[] = telemetry?.perception.objects ?? [];

    obstacles.forEach((obs) => {
      const relX = obs.relative_position[0];
      const relY = obs.relative_position[1];
      const cx = toCanvasX(relY);
      const cy = toCanvasY(relX);
      const cls = obs.class_name.toLowerCase();

      // Predicted Trajectory (Orange Dashed Lines)
      if (showPredictions && obs.predicted_trajectory && obs.predicted_trajectory.length > 1) {
        ctx.strokeStyle = '#f97316';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        obs.predicted_trajectory.forEach((pt, idx) => {
          const px = toCanvasX(pt[1]);
          const py = toCanvasY(pt[0]);
          if (idx === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        });
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Obstacle Safety Bubble
      ctx.fillStyle = 'rgba(239, 68, 68, 0.12)';
      ctx.beginPath();
      ctx.arc(cx, cy, 2.2 * pixelsPerMeter, 0, 2 * Math.PI);
      ctx.fill();

      // Class Color & Geometry
      let color = '#22c55e'; // Car
      let widthPx = 1.8 * pixelsPerMeter;
      let heightPx = 3.6 * pixelsPerMeter;

      if (cls === 'pedestrian') {
        color = '#f97316'; // Orange
        widthPx = 1.0 * pixelsPerMeter;
        heightPx = 1.0 * pixelsPerMeter;
      } else if (cls === 'motorcycle') {
        color = '#ec4899'; // Pink/Magenta
        widthPx = 1.0 * pixelsPerMeter;
        heightPx = 2.2 * pixelsPerMeter;
      } else if (cls === 'auto_rickshaw') {
        color = '#eab308'; // Yellow
        widthPx = 1.6 * pixelsPerMeter;
        heightPx = 2.6 * pixelsPerMeter;
      } else if (cls === 'animal') {
        color = '#a855f7'; // Purple
        widthPx = 1.4 * pixelsPerMeter;
        heightPx = 2.2 * pixelsPerMeter;
      } else if (cls === 'truck' || cls === 'bus') {
        color = '#38bdf8'; // Cyan
        widthPx = 2.4 * pixelsPerMeter;
        heightPx = 6.0 * pixelsPerMeter;
      } else if (cls === 'debris' || cls === 'obstacle') {
        color = '#ef4444'; // Red
        widthPx = 1.2 * pixelsPerMeter;
        heightPx = 1.2 * pixelsPerMeter;
      }

      ctx.save();
      ctx.translate(cx, cy);
      if (obs.direction) {
        ctx.rotate((-obs.direction * Math.PI) / 180);
      }

      // Obstacle Box
      ctx.fillStyle = color;
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;
      ctx.fillRect(-widthPx / 2, -heightPx / 2, widthPx, heightPx);
      ctx.strokeRect(-widthPx / 2, -heightPx / 2, widthPx, heightPx);

      ctx.restore();

      // Label Tag
      const label = `#${obs.object_id} ${cls.toUpperCase()} (${obs.distance.toFixed(1)}m)`;
      ctx.font = '10px sans-serif';
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(cx - 35, cy - heightPx / 2 - 16, 70, 14);
      ctx.fillStyle = '#000000';
      ctx.textAlign = 'center';
      ctx.fillText(label, cx, cy - heightPx / 2 - 5);
      ctx.textAlign = 'left';
    });

    // 7. Ego Autonomous Vehicle (Blue Body)
    const egoCx = toCanvasX(0);
    const egoCy = toCanvasY(0);
    const vehWidthPx = 2.0 * pixelsPerMeter;
    const vehLengthPx = 4.7 * pixelsPerMeter;

    // Safety Envelope Halo
    const riskLevel = telemetry?.risk.risk_level ?? 'LOW';
    let haloColor = 'rgba(34, 197, 94, 0.2)'; // Green
    if (riskLevel === 'MEDIUM') haloColor = 'rgba(234, 179, 8, 0.25)';
    else if (riskLevel === 'HIGH') haloColor = 'rgba(249, 115, 22, 0.35)';
    else if (riskLevel === 'CRITICAL') haloColor = 'rgba(239, 68, 68, 0.5)';

    ctx.fillStyle = haloColor;
    ctx.beginPath();
    ctx.arc(egoCx, egoCy, 3.5 * pixelsPerMeter, 0, 2 * Math.PI);
    ctx.fill();

    // Vehicle Chassis
    ctx.fillStyle = '#2563eb'; // Blue
    ctx.strokeStyle = '#93c5fd';
    ctx.lineWidth = 2;
    ctx.fillRect(egoCx - vehWidthPx / 2, egoCy - vehLengthPx, vehWidthPx, vehLengthPx);
    ctx.strokeRect(egoCx - vehWidthPx / 2, egoCy - vehLengthPx, vehWidthPx, vehLengthPx);

    // Windshield
    ctx.fillStyle = '#1e3a8a';
    ctx.fillRect(egoCx - vehWidthPx / 2 + 3, egoCy - vehLengthPx * 0.7, vehWidthPx - 6, vehLengthPx * 0.3);

    // Headlights Rays
    ctx.fillStyle = 'rgba(254, 240, 138, 0.15)';
    ctx.beginPath();
    ctx.moveTo(egoCx - vehWidthPx / 2 + 2, egoCy - vehLengthPx);
    ctx.lineTo(egoCx - vehWidthPx * 1.5, egoCy - vehLengthPx - 35);
    ctx.lineTo(egoCx + vehWidthPx * 1.5, egoCy - vehLengthPx - 35);
    ctx.lineTo(egoCx + vehWidthPx / 2 - 2, egoCy - vehLengthPx);
    ctx.fill();

    // Ego Label
    ctx.fillStyle = '#60a5fa';
    ctx.font = 'bold 10px monospace';
    ctx.fillText('EGO VEHICLE (AUTONOMOUS)', egoCx - 70, egoCy + 16);

  }, [telemetry, zoom, showPredictions, showOccupancy]);

  return (
    <div className="flex-1 bg-dark-900 flex flex-col relative overflow-hidden select-none">
      {/* Top Visualizer HUD Bar */}
      <div className="absolute top-3 left-3 right-3 z-10 flex items-center justify-between pointer-events-none">
        <div className="flex items-center space-x-2 pointer-events-auto">
          <div className="bg-dark-800/90 backdrop-blur border border-dark-600 rounded-lg px-3 py-1.5 flex items-center space-x-2 text-xs font-mono shadow-lg">
            <Compass className="w-3.5 h-3.5 text-accent-cyan" />
            <span className="text-gray-400">Heading:</span>
            <span className="text-white font-bold">{telemetry?.vehicle.heading_deg ?? 0.0}°</span>
          </div>

          <div className="bg-dark-800/90 backdrop-blur border border-dark-600 rounded-lg px-3 py-1.5 flex items-center space-x-2 text-xs font-mono shadow-lg">
            <span className="text-gray-400">Objects Tracked:</span>
            <span className="text-accent-amber font-bold">{telemetry?.perception.detected_objects_count ?? 0}</span>
          </div>
        </div>

        {/* Zoom & Layer Toggles */}
        <div className="flex items-center space-x-1.5 bg-dark-800/90 backdrop-blur border border-dark-600 rounded-lg p-1 pointer-events-auto shadow-lg">
          <button
            onClick={() => setZoom((z) => Math.min(2.0, z + 0.2))}
            className="p-1.5 text-gray-300 hover:text-white hover:bg-dark-700 rounded"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(0.6, z - 0.2))}
            className="p-1.5 text-gray-300 hover:text-white hover:bg-dark-700 rounded"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            onClick={() => setZoom(1.0)}
            className="p-1.5 text-gray-300 hover:text-white hover:bg-dark-700 rounded"
            title="Reset Zoom"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main HTML5 Canvas */}
      <canvas ref={canvasRef} className="w-full h-full block" />

      {/* Legend Overlay at Bottom Left */}
      <div className="absolute bottom-3 left-3 bg-dark-800/90 backdrop-blur border border-dark-600 rounded-lg p-2 text-[10px] space-y-1 z-10 shadow-lg font-mono">
        <div className="font-bold text-gray-400 uppercase tracking-wider mb-1">Navigation Legend</div>
        <div className="flex items-center space-x-2">
          <span className="w-3 h-1 bg-accent-blue rounded"></span>
          <span className="text-gray-300">Global Route</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-3 h-1 bg-accent-cyan rounded"></span>
          <span className="text-gray-300">Adaptive A* Path</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-3 h-1 bg-orange-500 border-dashed border-b border-orange-500"></span>
          <span className="text-gray-300">Obstacle Prediction (3.0s)</span>
        </div>
        <div className="flex items-center space-x-2">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-600 border border-blue-300"></span>
          <span className="text-gray-300">Autonomous Ego Vehicle</span>
        </div>
      </div>
    </div>
  );
};
