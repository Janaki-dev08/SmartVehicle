import React, { useState, useEffect } from 'react';
import { TelemetryFrame, ScenarioData } from './types/simulation';
import { telemetryWS } from './services/websocket';
import { fetchScenarios, loadScenario } from './services/api';
import { Header } from './components/Header';
import { LeftPanel } from './components/LeftPanel';
import { SimulationCanvas } from './components/SimulationCanvas';
import { RightPanel } from './components/RightPanel';
import { BottomPanel } from './components/BottomPanel';
import { ScenarioDetailsModal } from './components/ScenarioDetailsModal';
import { GoogleMapsModal } from './components/GoogleMapsModal';

export const App: React.FC = () => {
  const [telemetry, setTelemetry] = useState<TelemetryFrame | null>(null);
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [scenarios, setScenarios] = useState<ScenarioData[]>([]);
  const [isScenarioModalOpen, setIsScenarioModalOpen] = useState<boolean>(false);
  const [isMapsModalOpen, setIsMapsModalOpen] = useState<boolean>(false);

  // 1. Fetch initial scenarios on mount
  useEffect(() => {
    fetchScenarios()
      .then((data) => {
        if (data.scenarios) {
          setScenarios(data.scenarios);
        }
      })
      .catch((err) => console.error('[App] Scenarios fetch error:', err));
  }, []);

  // 2. Subscribe to WebSocket high-frequency telemetry stream
  useEffect(() => {
    const unsubscribe = telemetryWS.subscribe((frame) => {
      setTelemetry(frame);
      setWsConnected(true);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const handleSelectScenario = async (scId: string) => {
    await loadScenario(scId);
  };

  return (
    <div className="flex flex-col h-screen w-screen bg-dark-900 text-gray-100 overflow-hidden select-none">
      {/* Top Header & Driverless Autonomous Banner */}
      <Header telemetry={telemetry} wsConnected={wsConnected} />

      {/* Main Cockpit Layout (Left Controls, Center Canvas, Right Telemetry) */}
      <main className="flex flex-1 min-h-0 relative">
        <LeftPanel
          telemetry={telemetry}
          scenarios={scenarios}
          onOpenScenarioModal={() => setIsScenarioModalOpen(true)}
          onOpenMapsModal={() => setIsMapsModalOpen(true)}
        />

        <SimulationCanvas telemetry={telemetry} />

        <RightPanel telemetry={telemetry} />
      </main>

      {/* Bottom Panel (Logs, Real-Time Charts, Benchmark Table) */}
      <BottomPanel telemetry={telemetry} />

      {/* Modals */}
      <ScenarioDetailsModal
        isOpen={isScenarioModalOpen}
        onClose={() => setIsScenarioModalOpen(false)}
        scenarios={scenarios}
        activeScenarioId={telemetry?.scenario?.id}
        onSelectScenario={handleSelectScenario}
      />

      <GoogleMapsModal
        isOpen={isMapsModalOpen}
        onClose={() => setIsMapsModalOpen(false)}
      />
    </div>
  );
};

export default App;
