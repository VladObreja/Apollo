@echo off
TITLE Apollo Station - Safe Shutdown
echo [1/2] Gracefully parking the Council...
docker-compose stop

echo [2/2] Releasing 5070 Ti VRAM...
nvidia-smi

echo ==========================================
echo STATION HIBERNATING - ALL STATE SAVED
echo ==========================================
timeout /t 3