@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
TITLE Apollo Station - Ignition

call :detect_docker || goto :fail
call :detect_compose || goto :fail
call :check_docker_daemon || goto :fail

echo [1/6] Starting Ollama bootstrap...
%COMPOSE_CMD% up -d ollama || goto :fail

echo [2/6] Waiting for Ollama to become healthy...
call :wait_healthy ollama 180 || goto :fail

echo [3/6] Ensuring nomic-embed-text is present...
docker exec ollama ollama list | findstr /I /C:"nomic-embed-text" >nul 2>&1
if errorlevel 1 (
  echo     Pulling nomic-embed-text...
  docker exec ollama ollama pull nomic-embed-text || goto :fail
) else (
  echo     nomic-embed-text already present.
)

echo [4/6] Starting full Apollo stack...
%COMPOSE_CMD% up -d --remove-orphans || goto :fail

echo [5/6] Waiting for core services to become healthy...
call :wait_healthy ollama 180 || goto :fail
call :wait_healthy apollo-agent 180 || goto :fail
call :wait_healthy docling 180 || goto :fail
call :wait_healthy apollo-lightrag 180 || goto :fail
call :wait_healthy browserless 180 || goto :fail
call :wait_healthy apollo-scout 180 || goto :fail
call :wait_healthy n8n_db 180 || goto :fail
call :wait_healthy n8n 180 || goto :fail
call :wait_healthy open-webui 180 || goto :fail

echo [6/6] Launching local interfaces...
start "" http://localhost:18789
start "" http://localhost:3000

echo ==========================================
echo STATION ONLINE - CORE SERVICES HEALTHY
echo Compose command: %COMPOSE_CMD%
echo OpenClaw:  http://localhost:18789
echo Open WebUI: http://localhost:3000
echo ==========================================
exit /b 0

:detect_docker
where docker >nul 2>&1
if errorlevel 1 (
  echo Docker CLI not found in PATH.
  exit /b 1
)
exit /b 0

:detect_compose
docker compose version >nul 2>&1
if not errorlevel 1 (
  set "COMPOSE_CMD=docker compose"
  exit /b 0
)
where docker-compose >nul 2>&1
if errorlevel 1 (
  echo Neither "docker compose" nor "docker-compose" is available.
  exit /b 1
)
set "COMPOSE_CMD=docker-compose"
exit /b 0

:check_docker_daemon
echo Checking Docker daemon...
docker info >nul 2>&1
if errorlevel 1 (
  echo Docker daemon is not reachable. Start Docker Desktop first.
  exit /b 1
)
exit /b 0

:wait_healthy
set "CONTAINER=%~1"
set /a TIMEOUT=%~2
set /a ELAPSED=0
:wait_healthy_loop
set "STATUS="
for /f "delims=" %%S in ('docker inspect -f "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}" "%CONTAINER%" 2^>nul') do set "STATUS=%%S"
if /I "!STATUS!"=="healthy" (
  echo     %CONTAINER% is healthy.
  exit /b 0
)
if /I "!STATUS!"=="unhealthy" (
  echo     %CONTAINER% reported unhealthy.
  exit /b 1
)
if /I "!STATUS!"=="exited" (
  echo     %CONTAINER% exited unexpectedly.
  exit /b 1
)
if !ELAPSED! GEQ !TIMEOUT! (
  echo     Timed out waiting for %CONTAINER%. Last status: !STATUS!
  exit /b 1
)
echo     waiting for %CONTAINER% ... current status: !STATUS!
timeout /t 5 /nobreak >nul
set /a ELAPSED+=5
goto :wait_healthy_loop

:fail
echo ==========================================
echo STARTUP FAILED - REVIEW THE OUTPUT ABOVE
echo ==========================================
exit /b 1
