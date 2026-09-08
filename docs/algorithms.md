# Algorithmic & Mathematical Foundations

This document details the mathematical formulations and algorithmic principles governing the autonomous driving system.

---

## 1. Pinhole Camera Geometry & Distance Estimation

Given a pinhole camera model with focal lengths $(f_x, f_y)$ and principal point $(c_x, c_y)$:

$$\begin{bmatrix} u \\ v \\ 1 \end{bmatrix} = \frac{1}{Z} \begin{bmatrix} f_x & 0 & c_x \\ 0 & f_y & c_y \\ 0 & 0 & 1 \end{bmatrix} \begin{bmatrix} X_c \\ Y_c \\ Z_c \end{bmatrix}$$

For a detected bounding box with pixel height $h_{\text{bbox}} = y_2 - y_1$ and known average real-world object height $H_{\text{real}}$:

$$Z_c = \frac{f_y \cdot H_{\text{real}}}{h_{\text{bbox}}}$$

The 3D relative position in the camera coordinate frame is:

$$X_c = \frac{(u_{\text{center}} - c_x) \cdot Z_c}{f_x}, \quad Y_c = \frac{(v_{\text{center}} - c_y) \cdot Z_c}{f_y}$$

Transforming from Camera coordinates $(X_c, Y_c, Z_c)$ to Vehicle Body frame $(X_v, Y_v, Z_v)$:

$$X_v = Z_c, \quad Y_v = X_c, \quad Z_v = -Y_c$$

---

## 2. Dynamic Obstacle Motion Prediction

For each tracked obstacle $i$ with estimated position $\mathbf{p}_i(t_0) = [x_i, y_i]^T$ and velocity vector $\mathbf{v}_i = [v_{x,i}, v_{y,i}]^T$:

The predicted position at future time $\tau \in [0, T_{\text{horizon}}]$ is:

$$\mathbf{p}_i(t_0 + \tau) = \mathbf{p}_i(t_0) + \mathbf{v}_i \cdot \tau$$

---

## 3. 2D Occupancy Grid Costmap Formulation

The cost of cell $(r, c)$ at world coordinate $(x, y)$ is evaluated as:

$$C(r, c) = C_{\text{road}}(y) + \sum_{i=1}^{N_{\text{obs}}} C_{\text{obs},i}(x, y) + \sum_{i=1}^{N_{\text{obs}}} \sum_{\tau} C_{\text{pred},i}(x, y, \tau)$$

Where:
- **Road Boundary Cost**:
  $$C_{\text{road}}(y) = \begin{cases} 0 & \text{if } |y| \le W_{\text{lane}} \\ \min\left(1.0, 0.6 + 0.4 \cdot (|y| - W_{\text{lane}})\right) & \text{if } |y| > W_{\text{lane}} \end{cases}$$

- **Obstacle Proximity Cost Gradient**:
  $$C_{\text{obs},i}(x, y) = \begin{cases} 1.0 & \text{if } d_i \le R_{\text{solid}} \\ 0.8 \cdot \left(1 - \frac{d_i - R_{\text{solid}}}{R_{\text{safety}}}\right) & \text{if } R_{\text{solid}} < d_i \le R_{\text{solid}} + R_{\text{safety}} \\ 0 & \text{otherwise} \end{cases}$$

where $d_i = \|\mathbf{p}_{\text{cell}} - \mathbf{p}_{\text{obs},i}\|$.

---

## 4. Adaptive A* Path Planning Formulation

The total evaluation function for node $n$ is:

$$f(n) = g(n) + h(n)$$

The transition cost from current node $u$ to neighbor $v$ is formulated as:

$$g(v) = g(u) + w_{\text{dist}} \cdot \Delta s + w_{\text{obs}} \cdot C(v) \cdot \alpha + w_{\text{smooth}} \cdot |\Delta \theta|$$

Where:
- $\Delta s$: Euclidean step displacement ($\Delta s \in \{\Delta x, \sqrt{\Delta x^2 + \Delta y^2}\}$).
- $C(v)$: Costmap value at node $v$.
- $|\Delta \theta|$: Heading angular deflection penalty between consecutive steps.
- $h(n)$: Admissible Euclidean distance heuristic to goal $(x_{\text{goal}}, y_{\text{goal}})$:
  $$h(n) = \sqrt{(x_{\text{goal}} - x_n)^2 + (y_{\text{goal}} - y_n)^2}$$

---

## 5. Time-To-Collision (TTC) & Risk Classification

For obstacle $i$ at longitudinal distance $d_{x,i} > 0$:

$$v_{\text{closing},i} = v_{\text{ego}} - v_{x,i}$$

$$\text{TTC}_i = \begin{cases} \frac{d_{x,i}}{v_{\text{closing},i}} & \text{if } v_{\text{closing},i} > 0.1 \text{ m/s} \\ \infty & \text{otherwise} \end{cases}$$

$$\text{TTC}_{\text{min}} = \min_{i} \text{TTC}_i$$

### Risk Level State Machine:
- **CRITICAL**: $\text{TTC}_{\text{min}} \le 1.5\text{s}$ OR $d_{\text{min}} \le 2.8\text{m} \implies \text{Emergency Maximum Braking } (8.5\text{ m/s}^2)$
- **HIGH**: $1.5\text{s} < \text{TTC}_{\text{min}} \le 2.5\text{s}$ OR $d_{\text{min}} \le 6.5\text{m} \implies \text{Decelerate & Evasive Replan}$
- **MEDIUM**: $2.5\text{s} < \text{TTC}_{\text{min}} \le 4.0\text{s}$ OR $d_{\text{min}} \le 12.0\text{m} \implies \text{Gentle Speed Reduction}$
- **LOW**: $\text{TTC}_{\text{min}} > 4.0\text{s} \text{ and } d_{\text{min}} > 12.0\text{m} \implies \text{Normal Cruising}$

---

## 6. Vehicle Control Formulation

### 6.1 Lateral Pure Pursuit Control
Target lookahead point $(x_t, y_t)$ in vehicle-relative frame at distance $L_d = \sqrt{x_t^2 + y_t^2}$:

Path curvature:
$$\kappa = \frac{2 \cdot y_t}{L_d^2}$$

Steering angle $\delta$:
$$\delta = \arctan(\kappa \cdot L_{\text{wheelbase}})$$

Normalized steer command $\in [-1.0, 1.0]$:
$$u_{\text{steer}} = \text{clip}\left(\frac{\delta}{\delta_{\text{max}}}, -1.0, 1.0\right)$$

### 6.2 Longitudinal Speed PID Control
$$e(t) = v_{\text{target}}(t) - v_{\text{current}}(t)$$

$$u(t) = K_p \cdot e(t) + K_i \int_{0}^{t} e(\tau) d\tau + K_d \frac{de(t)}{dt}$$

Actuator commands:
$$\text{Throttle} = \begin{cases} \text{clip}(u(t), 0, 1) & \text{if } u(t) \ge 0 \\ 0 & \text{otherwise} \end{cases}$$

$$\text{Brake} = \begin{cases} \text{clip}(-1.5 \cdot u(t), 0, 1) & \text{if } u(t) < 0 \\ 0 & \text{otherwise} \end{cases}$$
