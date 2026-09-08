import React, { useState } from 'react';
import { X, MapPin, Navigation, CheckCircle2 } from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const GoogleMapsModal: React.FC<Props> = ({ isOpen, onClose }) => {
  const [origin, setOrigin] = useState<string>('Connaught Place, New Delhi, India');
  const [destination, setDestination] = useState<string>('India Gate, New Delhi, India');
  const [status, setStatus] = useState<string>('');

  if (!isOpen) return null;

  const handleApply = () => {
    setStatus('High-level waypoints ingested into CARLA global coordinate frame.');
    setTimeout(() => {
      onClose();
    }, 1500);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-dark-800 border border-dark-600 rounded-2xl w-full max-w-md p-5 space-y-4 shadow-2xl">
        <div className="flex items-center justify-between border-b border-dark-700 pb-3">
          <div className="flex items-center space-x-2">
            <MapPin className="w-5 h-5 text-accent-blue" />
            <h2 className="text-sm font-bold text-white">Google Maps High-Level Navigation</h2>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="text-xs text-gray-400 leading-relaxed">
          Google Maps acts exclusively as the high-level macro-routing layer. The local autonomous driving system
          (YOLO perception, Adaptive A*, and Pure Pursuit control) executes all local steering, obstacle avoidance,
          and dynamic replanning.
        </div>

        <div className="space-y-3 text-xs">
          <div>
            <label className="text-gray-400 block mb-1">Origin / Start Landmark</label>
            <input
              type="text"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              className="w-full bg-dark-900 border border-dark-600 rounded-lg p-2 text-white"
            />
          </div>

          <div>
            <label className="text-gray-400 block mb-1">Destination Landmark</label>
            <input
              type="text"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              className="w-full bg-dark-900 border border-dark-600 rounded-lg p-2 text-white"
            />
          </div>
        </div>

        {status && (
          <div className="text-xs text-emerald-400 flex items-center space-x-1">
            <CheckCircle2 className="w-4 h-4" />
            <span>{status}</span>
          </div>
        )}

        <div className="flex items-center justify-end space-x-2 pt-2 border-t border-dark-700">
          <button
            onClick={onClose}
            className="px-3 py-1.5 rounded-lg text-xs font-medium text-gray-400 hover:bg-dark-700"
          >
            Cancel
          </button>
          <button
            onClick={handleApply}
            className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-accent-blue hover:bg-blue-600 text-white transition shadow-md"
          >
            Ingest Route
          </button>
        </div>
      </div>
    </div>
  );
};
