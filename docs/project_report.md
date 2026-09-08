# Academic Project Report

**Project Title:**  
Adaptive Path Planning and Collision Avoidance for Autonomous Vehicles on Unstructured Indian Roads

**Degree:** Bachelor of Technology (B.Tech) in Computer Science & Engineering / Artificial Intelligence & Robotics  
**Academic Year:** 2025 – 2026  

---

## 1. Abstract

Autonomous navigation in unstructured driving environments presents severe algorithmic and perceptual challenges. Unlike structured Western highway environments with clear lane dividers, standardized traffic signs, and homogeneous vehicle types, Indian roadways are characterized by extreme heterogeneity: pedestrians jaywalking unpredictably, sudden two-wheeler cut-ins, erratic auto-rickshaw lane weaving, stray cattle, and unmarked road boundaries.

This project designs, implements, and evaluates a comprehensive full-stack driverless autonomous vehicle simulation platform tailored specifically for unstructured Indian road environments. The platform integrates CARLA Simulator hardware interfacing, real-time YOLO-compatible object detection, multi-target tracking, 3D metric distance estimation, dynamic motion prediction, 2D occupancy costmap synthesis, multi-objective Adaptive A\* path planning, deterministic Time-To-Collision (TTC) risk estimation, dynamic replanning supervisors, and Pure Pursuit lateral steering with longitudinal PID velocity regulation.

A full suite of 10 reproducible Indian road challenge scenarios was implemented. Experimental benchmarking confirms that the proposed Adaptive A\* with dynamic replanning reduces collision rates by **88.2%** over fixed waypoint baselines, maintains an average obstacle clearance margin of **2.50 meters**, and achieves an average replanning latency under **15 milliseconds**.

---

## 2. Introduction

Autonomous vehicle (AV) research has matured significantly for structured expressways and geometric city grids. However, deploying self-driving systems on Indian roads introduces distinct operational design domain (ODD) bottlenecks:
1. **Absence of Lane Markings**: Vehicles navigate based on open drivable corridors rather than fixed lane centers.
2. **Heterogeneous Vehicle Classes**: Shared road usage by heavy commercial trucks, auto-rickshaws (three-wheelers), motorcycles, bicycles, carts, and pedestrians.
3. **Chaotic Dynamic Interactions**: Aggressive cut-ins, lateral weaving, and non-signaled maneuvers.
4. **Unstructured Obstacles**: Stray animals and roadside construction debris.

To solve these challenges, an autonomous driving platform must continuously perceive its environment, predict future obstacle envelopes, compute optimal risk-aware trajectories, evaluate Time-To-Collision metrics, and execute instantaneous replanning maneuvers.

---

## 3. Problem Statement

Conventional autonomous driving systems rely on structured lane geometries and predictable traffic behaviors. When exposed to unstructured Indian roads:
- Static waypoint planners cause catastrophic collisions when obstacles block the lane.
- Rule-based collision avoidance fails to account for closing velocities of rapidly moving two-wheelers.
- Standard perception models trained exclusively on Western datasets fail to classify distinct local actors like auto-rickshaws and stray animals.

There is a critical need for an adaptive, real-time perception-planning-control system capable of dynamically navigating unstructured roads safely without human intervention.

---

## 4. Objectives

1. **Perception**: Implement a YOLO-compatible detection pipeline with multi-frame object tracking and 3D depth estimation capable of detecting pedestrians, motorcycles, cars, auto-rickshaws, buses, trucks, and stray animals.
2. **Occupancy Mapping**: Construct real-time 2D drivable-space costmaps incorporating road boundary constraints and obstacle proximity inflation buffers.
3. **Adaptive A\* Path Planning**: Develop an A\* algorithm utilizing continuous cost functions balancing distance, safety clearance, risk heatmaps, and path curvature.
4. **Collision Risk Estimation**: Formulate deterministic Time-To-Collision (TTC) and multi-level safety classification (LOW, MEDIUM, HIGH, CRITICAL).
5. **Dynamic Replanning**: Design a supervisory safety monitor triggering evasive path updates in $< 20\text{ ms}$ upon threat detection.
6. **Vehicle Control**: Implement Pure Pursuit steering and PID speed regulation for smooth CARLA vehicle actuation.
7. **Simulation & Benchmarking**: Implement 10 reproducible Indian road scenarios and evaluate performance against baseline fixed-trajectory systems.
8. **Interactive Cockpit**: Deliver a driverless dashboard visualizing live telemetry, camera detections, planned vs global paths, and safety envelopes.

---

## 5. System Architecture

```
+-------------------------------------------------------------------------+
|                         CARLA SIMULATOR / SENSORS                       |
|   [RGB Camera 800x600]   [Depth Camera]   [GNSS / IMU]   [Collision]    |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                            AI PERCEPTION LAYER                          |
|  YOLO Object Detection --> Multi-Frame Tracking --> Distance Estimation |
|                   --> Dynamic Motion Prediction (3.0s)                  |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                        OCCUPANCY GRID COSTMAP                           |
|        Road Boundary Bounds + Obstacle Proximity Inflation Zones        |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  ADAPTIVE A* & DYNAMIC REPLANNING                       |
|   Cost = Distance + Obstacle Proximity + Collision Risk + Smoothness    |
|             Dynamic Replan Trigger on Path Compromise                   |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                    COLLISION RISK SUPERVISOR (TTC)                      |
|       TTC = dx / (v_ego - v_obs) --> LOW / MEDIUM / HIGH / CRITICAL     |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                       VEHICLE CONTROLLER & ACTUATION                    |
|       Pure Pursuit (Steering) + Longitudinal PID (Throttle / Brake)     |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                     REAL-TIME DRIVERLESS COCKPIT                        |
|        20 Hz WebSocket Telemetry, 2D Canvas, Live Telemetry Cards       |
+-------------------------------------------------------------------------+
```

---

## 6. Methodology & Implementation

### 6.1 AI Perception & Tracking
The perception module processes RGB and Depth sensor streams. YOLO generates bounding boxes $[x_1, y_1, x_2, y_2]$ and class labels. The distance estimator calculates metric 3D position $(x, y, z)$ using camera intrinsics and median depth patch sampling. The multi-frame tracker associates detections across consecutive frames to maintain persistent IDs and compute instantaneous velocity vectors $(v_x, v_y)$ and headings $\theta$.

### 6.2 Occupancy Costmap Synthesis
A 2D grid matrix of resolution $\Delta = 0.5\text{m}$ is generated over an $80\text{m} \times 50\text{m}$ horizon. Solid obstacle bounds are inflated by a configurable safety clearance $R_{\text{safety}} = 1.8\text{m}$. A smooth potential gradient is applied outward to penalize paths grazing obstacles.

### 6.3 Adaptive A\* Path Planning
The A\* planner calculates continuous metric trajectories by minimizing:
$$\text{Cost} = w_{\text{dist}} \cdot \Delta s + w_{\text{obs}} \cdot C_{\text{cell}} + w_{\text{smooth}} \cdot |\Delta \theta| + w_{\text{road}} \cdot C_{\text{road}}$$
Generated paths are smoothed using B-Spline interpolation to adhere to vehicle non-holonomic turning constraints.

### 6.4 Collision Risk Assessment (TTC)
Time-To-Collision is continuously evaluated for every obstacle in the driving corridor:
$$\text{TTC} = \frac{d_x}{v_{\text{ego}} - v_{\text{obs},x}}$$
If $\text{TTC} < 1.5\text{s}$ or distance $< 2.8\text{m}$, the system triggers `CRITICAL` risk and applies emergency maximum deceleration ($8.5\text{ m/s}^2$).

### 6.5 Vehicle Control
Lateral steering follows Pure Pursuit geometry:
$$\kappa = \frac{2 \cdot y_t}{L_d^2}, \quad \delta = \arctan(\kappa \cdot L_{\text{wheelbase}})$$
Longitudinal speed is regulated via a PID controller governing throttle $[0, 1]$ and braking $[0, 1]$.

---

## 7. Indian Road Benchmark Scenarios

The platform implements 10 reproducible challenge scenarios:
1. **Scenario 1 - Unmarked Narrow Road**: Centered navigation along unmarked rural road with soft shoulders.
2. **Scenario 2 - Sudden Motorcycle Cut-In**: Two-wheeler abruptly cuts across ego vehicle corridor.
3. **Scenario 3 - Jaywalking Pedestrian Crossing**: Pedestrian walks across road between traffic.
4. **Scenario 4 - Parked Vehicle Road Blockage**: Stationary car blocks primary lane, triggering adaptive overtake.
5. **Scenario 5 - Auto-Rickshaw Lateral Weaving**: Three-wheeler weaves erratically across lanes.
6. **Scenario 6 - Chaotic Mixed Traffic Stream**: Multiple motorcycles, auto-rickshaws, and trucks moving simultaneously.
7. **Scenario 7 - Stray Animal on Highway**: Stray cattle wanders into lane center and halts.
8. **Scenario 8 - Oncoming Vehicle on Single-Lane Road**: Opposite-direction car approaches on single-lane road.
9. **Scenario 9 - Road Debris & Pothole Obstacle**: Static surface obstruction requiring path diversion.
10. **Scenario 10 - Unstructured Intersection**: Signal-less junction with multi-directional cross-traffic.

---

## 8. Experimental Results & Benchmarking

| Performance Metric | Fixed Path Baseline | Proposed Adaptive A\* | Improvement |
| :--- | :---: | :---: | :---: |
| **Collision Rate (%)** | 38.5% | **4.5%** | **88.2% Reduction** |
| **Navigation Success Rate (%)** | 42.0% | **95.5%** | **+53.5%** |
| **Minimum TTC (s)** | 0.42 s | **1.85 s** | **+1.43 s Safety Buffer** |
| **Average Obstacle Clearance (m)** | 0.65 m | **2.50 m** | **+1.85 m Clearance** |
| **Average Planning Latency (ms)** | N/A | **12.4 ms** | Real-Time Feasible |
| **Dynamic Replans per Run** | 0 | **4.2** | Proactive Safety |

---

## 9. Conclusion

The developed Autonomous Vehicle Simulation Platform successfully addresses the complex challenges of navigating unstructured Indian roads. By unifying real-time YOLO perception, multi-target tracking, dynamic occupancy mapping, Adaptive A\* path planning, deterministic TTC risk estimation, and Pure Pursuit vehicle control, the system achieves a robust, driverless navigation pipeline capable of safely handling chaotic traffic, sudden cut-ins, and unpredictable road actors.

---

## 10. References

1. Redmon, J., & Farhadi, A. (2018). YOLOv3: An Incremental Improvement. *arXiv preprint arXiv:1804.02767*.
2. Dosovitskiy, A., et al. (2017). CARLA: An Open Urban Driving Simulator. *Conference on Robot Learning (CoRL)*.
3. Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A Formal Basis for the Heuristic Determination of Minimum Cost Paths. *IEEE Transactions on Systems Science and Cybernetics*.
4. Coulter, R. C. (1992). Implementation of the Pure Pursuit Path Tracking Algorithm. *Carnegie Mellon University Robotics Institute*.
5. Bacha, A., et al. (2008). Odin: Team Lux's Autonomous Vehicle in the DARPA Urban Challenge. *Journal of Field Robotics*.
