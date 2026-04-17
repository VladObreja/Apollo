@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
TITLE Apollo Station - Safe Shutdown

call :detect_docker || goto :fail
call :detect_compose || goto :fail
call :check_docker_daemon || goto :fail

echo [1/4] Stopping application services...
%COMPOSE_CMD% stop -t 45 open-webui n8n apollo-agent lightrag docling crawl4ai browserless || goto :fail

echo [2/4] Stopping model and database services...
%COMPOSE_CMD% stop -t 60 ollama n8n_db || goto :fail

echo [3/4] Verifying containers are no longer running...
call :verify_stopped open-webui || goto :fail
call :verify_stopped n8n || goto :fail
call :verify_stopped apollo-agent || goto :fail
call :verify_stopped apollo-lightrag || goto :fail
call :verify_stopped docling || goto :fail
call :verify_stopped apollo-scout || goto :fail
call :verify_stopped browserless || goto :fail
call :verify_stopped ollama || goto :fail
call :verify_stopped n8n_db || goto :fail

echo [4/4] Reporting GPU status...
where nvidia-smi >nul 2>&1
if errorlevel 1 (
  echo     nvidia-smi not available on PATH.
) else (
  nvidia-smi
)

echo ==========================================
echo STATION HIBERNATING - SERVICES STOPPED
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

:verify_stopped
set "CONTAINER=%~1"
set "STATUS="
for /f "delims=" %%S in ('docker inspect -f "{{.State.Status}}" "%CONTAINER%" 2^>nul') do set "STATUS=%%S"
if not defined STATUS (
  echo     %CONTAINER% is not present, treating as stopped.
  exit /b 0
)
if /I not "!STATUS!"=="running" (
  echo     %CONTAINER% status: !STATUS!
  exit /b 0
)
echo     %CONTAINER% is still running.
exit /b 1

:fail
echo ==========================================
echo SHUTDOWN FAILED - REVIEW THE OUTPUT ABOVE
echo ==========================================
exit /b 1
