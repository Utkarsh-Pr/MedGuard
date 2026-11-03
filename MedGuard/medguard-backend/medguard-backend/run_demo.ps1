param(
    [int]$Port = 8000
)

$env:DATABASE_URL = "sqlite:///./medguard.db"
$env:MEDGUARD_INFERENCE_BACKEND = "torch"
Write-Host "Starting MedGuard local demo at http://127.0.0.1:$Port"
Write-Host "Database: local SQLite file medguard.db"
$python = if (Test-Path ".\.venv-ml\Scripts\python.exe") { ".\.venv-ml\Scripts\python.exe" } else { "python" }
& $python -m uvicorn main:app --reload --port $Port
