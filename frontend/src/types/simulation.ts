export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type SupervisorAction = 
  | 'CRUISING' 
  | 'SLOWING' 
  | 'EVASIVE_REPLAN' 
  | 'EMERGENCY_BRAKE' 
  | 'DESTINATION_REACHED';

export interface VehicleState {
  speed_kmh: number;
  speed_ms: number;
  position: { x: number; y: number; z: number };
  heading_deg: number;
  heading_rad: number;
  acceleration_ms2: number;
  steering_angle: number;
  throttle: number;
  brake: number;
  destination_distance_m: number;
}

export interface DetectedObject {
  object_id: number;
  class_name: string;
  confidence: number;
  bounding_box: [number, number, number, number];
  distance: number;
  relative_position: [number, number, number];
  velocity: number;
  vx?: number;
  vy?: number;
  direction: number;
  predicted_trajectory?: [number, number][];
}

export interface RiskReport {
  risk_level: RiskLevel;
  min_ttc: number | null;
  nearest_obstacle: {
    id: number;
    class_name: string;
    distance: number;
    relative_position: [number, number, number];
  } | null;
  nearest_distance: number;
  threat_count: number;
  lateral_clearance: number;
  risk_score: number;
}

export interface PlannerState {
  algorithm: string;
  total_replans: number;
  latest_planning_time_ms: number;
  local_path: [number, number][];
  global_path: [number, number][];
  lookahead_target: [number, number];
}

export interface ScenarioActor {
  id: number;
  type: string;
  rel_x: number;
  rel_y: number;
  rel_z: number;
  speed: number;
  heading: number;
  behavior: string;
}

export interface ScenarioData {
  id: string;
  name: string;
  category: string;
  difficulty: 'Easy' | 'Medium' | 'Hard' | 'Expert';
  description: string;
  road_width: number;
  actor_count: number;
  actors: ScenarioActor[];
  start_position: { x: number; y: number; heading: number };
  destination: { x: number; y: number };
}

export interface MetricsSummary {
  total_distance_m: number;
  avg_speed_kmh: number;
  min_ttc_seconds: number;
  avg_ttc_seconds: number;
  avg_obstacle_clearance_m: number;
  avg_planning_time_ms: number;
  max_planning_time_ms: number;
  total_replans: number;
  collision_count: number;
  collision_rate_percent: number;
  navigation_success_rate_percent: number;
  emergency_stops: number;
  destination_reached: boolean;
}

export interface ReplanEvent {
  id: number;
  timestamp: number;
  reason: string;
  latency_ms: number;
  prev_points: number;
  new_points: number;
  status: string;
}

export interface CarlaStatus {
  connected: boolean;
  status: string;
  host: string;
  port: number;
  map: string;
  sync_mode: boolean;
  last_error: string;
  instructions: string;
}

export interface BenchmarkComparison {
  fixed_path_baseline: {
    planner_name: string;
    collision_rate: string;
    avg_speed: string;
    min_ttc: string;
    avg_clearance: string;
    emergency_stops: string;
    success_rate: string;
    adaptability: string;
  };
  adaptive_astar: {
    planner_name: string;
    collision_rate: string;
    avg_speed: string;
    min_ttc: string;
    avg_clearance: string;
    emergency_stops: string;
    success_rate: string;
    adaptability: string;
  };
  improvement: {
    collision_reduction: string;
    safety_clearance_gain: string;
    avg_planning_latency: string;
  };
}

export interface TelemetryFrame {
  timestamp: number;
  step: number;
  running: boolean;
  mode: string;
  driver: string;
  human_control: string;
  vehicle: VehicleState;
  carla: CarlaStatus;
  scenario: ScenarioData | null;
  risk: RiskReport;
  action: SupervisorAction;
  planner: PlannerState;
  perception: {
    detected_objects_count: number;
    objects: DetectedObject[];
  };
  metrics: MetricsSummary;
  benchmark: BenchmarkComparison;
  latest_replans: ReplanEvent[];
  road_width: number;
}
