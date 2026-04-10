# Apollo-V2 Sequential Download Rig
$ErrorActionPreference = "Continue"

# 1. Force environment refresh in case PATH is acting up
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# 2. High-Performance Flags (2026 Xet-Bypass)
$env:HF_HUB_DISABLE_XET = "1"
$env:HF_HUB_ENABLE_HF_TRANSFER = "1"

$VaultPath = "C:\Apollo\Vault"
if (!(Test-Path $VaultPath)) { New-Item -ItemType Directory -Path $VaultPath }

Write-Host "--- APOLLO VAULT INITIALIZING ---" -ForegroundColor Cyan

$Models = @(
    @{Repo="bartowski/mistralai_Ministral-3-14B-Instruct-2512-GGUF"; File="mistralai_Ministral-3-14B-Instruct-2512-Q6_K.gguf"},
    @{Repo="bartowski/Qwen_Qwen3.5-9B-GGUF"; File="Qwen_Qwen3.5-9B-Q8_0.gguf"},
    @{Repo="bartowski/whisper-large-v3-turbo-GGUF"; File="whisper-large-v3-turbo-Q8_0.gguf"}
)

foreach ($Model in $Models) {
    Write-Host "`n>>> Pulling: $($Model.File)" -ForegroundColor Yellow
    hf download $($Model.Repo) $($Model.File) --local-dir $VaultPath
}

Write-Host "`n--- DOWNLOADS COMPLETE ---" -ForegroundColor Green
Read-Host "Press Enter to close this window..."