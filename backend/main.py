"""
backend/main.py — FastAPI Application Entry Point.
"""

import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from backend.api.routes import router as api_router, sim_engine
from backend.api.websocket import ws_manager
from backend.services.simulation_service import simulation_service

# Resolve the frontend directory relative to project root
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Simulation loop tick rate (20 Hz)
SIM_TICK_INTERVAL = 0.05


def create_app() -> FastAPI:
    app = FastAPI(
        title="Adaptive Path Planning & Collision Avoidance (SIH)",
        description="Autonomous Vehicle Navigation on Unstructured Indian Roads using PPO RL and Deterministic Safety Layer.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Enable CORS for React Frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include REST API routes
    app.include_router(api_router)

    # Serve frontend static assets (src/, assets/, etc.) if frontend dir exists
    if FRONTEND_DIR.exists():
        src_dir = FRONTEND_DIR / "src"
        if src_dir.exists():
            app.mount("/src", StaticFiles(directory=str(src_dir)), name="frontend-src")

    # -----------------------------------------------------------------------
    # WebSocket — Real-Time Telemetry Stream
    # -----------------------------------------------------------------------
    @app.websocket("/ws/telemetry")
    async def websocket_telemetry(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                # Keep connection alive; telemetry is pushed by the background loop
                await asyncio.sleep(1)
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
        except Exception:
            ws_manager.disconnect(websocket)

    # -----------------------------------------------------------------------
    # Background Simulation Loop — runs at 20 Hz and broadcasts telemetry
    # -----------------------------------------------------------------------
    @app.on_event("startup")
    async def start_simulation_loop():
        asyncio.create_task(_simulation_loop())

    # -----------------------------------------------------------------------
    # Misc REST endpoints
    # -----------------------------------------------------------------------
    @app.get("/api/status")
    async def api_status():
        return {
            "message": "Adaptive Path Planning & Collision Avoidance API Running",
            "docs": "/docs",
            "model_ready": simulation_service.model_loaded,
            "carla": sim_engine.carla_conn.get_status()
        }

    # Serve frontend index.html at root (and for any unmatched routes as SPA fallback)
    @app.get("/")
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str = ""):
        # Don't intercept API or docs routes
        if full_path.startswith(("api/", "docs", "redoc", "openapi", "ws")):
            from fastapi import HTTPException
            raise HTTPException(status_code=404)
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file), media_type="text/html")
        return {
            "message": "Adaptive Path Planning & Collision Avoidance API Running",
            "docs": "/docs",
            "model_ready": simulation_service.model_loaded
        }

    return app


async def _simulation_loop():
    """
    Background coroutine: ticks the simulation engine at ~20 Hz and
    broadcasts telemetry to all connected WebSocket clients.
    """
    print("[SimLoop] Background simulation loop started at 20 Hz.")
    while True:
        try:
            telemetry = sim_engine.step(dt=SIM_TICK_INTERVAL)
            if ws_manager.active_connections:
                await ws_manager.broadcast_json(telemetry)
        except Exception as e:
            print(f"[SimLoop] Error in simulation loop: {e}")
        await asyncio.sleep(SIM_TICK_INTERVAL)


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
