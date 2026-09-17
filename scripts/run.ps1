param(
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.11 -m venv .venv
}

$python = Join-Path (Get-Location) ".venv\Scripts\python.exe"
& $python -m pip install -e ".[dev]"
Copy-Item ".env.example" ".env" -Force -ErrorAction SilentlyContinue
& $python -m uvicorn app.main:app --host 127.0.0.1 --port $Port