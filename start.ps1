Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Multi-Model OCR Application" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Use the currently activated Python environment
Write-Host "Using active Python environment" -ForegroundColor Green
Write-Host ""

# Start the FastAPI app via Uvicorn
uvicorn web.app:app --host 0.0.0.0 --port 5000 --reload
