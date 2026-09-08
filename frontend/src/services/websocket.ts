import { TelemetryFrame } from '../types/simulation';

export type TelemetryCallback = (data: TelemetryFrame) => void;

class TelemetryWebSocketService {
  private socket: WebSocket | null = null;
  private listeners: Set<TelemetryCallback> = new Set();
  private isConnecting: boolean = false;
  private reconnectInterval: number = 2000;
  private url: string;

  constructor() {
    const loc = window.location;
    const wsHost = loc.port === '5173' ? 'localhost:8000' : loc.host;
    const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';
    this.url = `${protocol}//${wsHost}/ws/telemetry`;
  }

  public connect() {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isConnecting = true;
    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        this.isConnecting = false;
        console.log('[WS] Connected to Autonomous Vehicle Telemetry Stream');
      };

      this.socket.onmessage = (event) => {
        try {
          const data: TelemetryFrame = JSON.parse(event.data);
          this.listeners.forEach((callback) => callback(data));
        } catch (e) {
          console.error('[WS] Message parse error:', e);
        }
      };

      this.socket.onclose = () => {
        this.isConnecting = false;
        this.socket = null;
        setTimeout(() => this.connect(), this.reconnectInterval);
      };

      this.socket.onerror = (error) => {
        console.warn('[WS] WebSocket error:', error);
        this.socket?.close();
      };
    } catch (e) {
      this.isConnecting = false;
      setTimeout(() => this.connect(), this.reconnectInterval);
    }
  }

  public subscribe(callback: TelemetryCallback): () => void {
    this.listeners.add(callback);
    if (!this.socket || this.socket.readyState === WebSocket.CLOSED) {
      this.connect();
    }
    return () => {
      this.listeners.delete(callback);
    };
  }

  public disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}

export const telemetryWS = new TelemetryWebSocketService();
