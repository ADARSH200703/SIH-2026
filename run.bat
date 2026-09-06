@echo off
title UAV Aero Piston Engine Digital Twin Launcher
echo =========================================================================
echo  AI-Enabled Real-Time Digital Twin System for MALE UAV Aero Piston Engines
echo =========================================================================
echo.
echo [1/2] Starting Python FastAPI Telemetry Backend on port 8000...
start /b uvicorn backend.main:app --host 0.0.0.0 --port 8000
echo.
echo [2/2] Starting Frontend Vite Development Server on port 3000...
start /b npm run dev
echo.
echo =========================================================================
echo  System is running!
echo  - Frontend Dashboard: http://localhost:3000/
echo  - Backend REST API:   http://localhost:8000/docs
echo  - WebSocket Stream:   ws://localhost:8000/ws/telemetry
echo =========================================================================
pause
