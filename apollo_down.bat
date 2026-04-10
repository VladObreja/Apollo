@echo off
TITLE Apollo Station - Safe Shutdown
echo [1/2] Gracefully parking the Strategist...
docker-compose stop

echo [2/2] Releasing VRAM...
nvidia-smi

echo ==========================================
echo STATION HIBERNATING - ALL STATE SAVED
echo ==========================================
timeout /t 3