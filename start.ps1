Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Multi-Model OCR Application" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Use the currently activated Python environment
Write-Host "Using active Python environment" -ForegroundColor Green
Write-Host ""

# Start the Flask app
python app.py
