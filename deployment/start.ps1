Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Starting Multi-Model OCR Application" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set Tesseract path
$env:PATH = "$env:PATH;C:\Program Files\Tesseract-OCR"

# Use virtual environment Python
Write-Host "Using virtual environment: ocr_env" -ForegroundColor Green
Write-Host ""

# Start the Flask app
& "ocr_env\Scripts\python.exe" app.py
