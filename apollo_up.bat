@echo off
TITLE Apollo Station - Ignition
echo [1/3] Clearing stale AI locks...
if exist "Intel\*.lock" del /q "Intel\*.lock"

echo [2/3] Starting 5070 Ti Orchestration...
docker-compose up -d --remove-orphans

echo [3/3] Launching Dashboard...
start http://localhost:18789

echo ==========================================
echo STATION ONLINE - RESEARCH COMMENCING
echo ==========================================
timeout /t 5