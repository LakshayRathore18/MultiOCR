@echo off
cd /d "%~dp0\.."
set PATH=%PATH%;C:\Program Files\Tesseract-OCR
ocr_env\Scripts\python.exe app.py
echo Server started.
