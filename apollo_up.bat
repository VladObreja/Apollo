@echo off
TITLE Apollo Station - Ignition
echo [1/4] Clearing stale AI locks...
if exist "Intel\*.lock" del /q "Intel\*.lock"

echo [2/4] Starting Ollama and Pulling Embeddings...
docker-compose up -d ollama
timeout /t 5
docker exec -it ollama ollama pull nomic-embed-text

echo [3/4] Starting Station Orchestration...
docker-compose up -d --remove-orphans

echo [4/4] Launching Interfaces...
start http://localhost:18789
start http://localhost:3000

echo ==========================================
echo STATION ONLINE - RESEARCH COMMENCING
echo ==========================================
timeout /t 5