@echo off
echo Installing visualization dependencies...
echo.

cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist "ocr_env\Scripts\activate.bat" (
    echo Activating virtual environment...
    call ocr_env\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found at ocr_env\Scripts\activate.bat
    echo Installing globally...
    echo.
)

echo Installing matplotlib and scikit-image...
pip install matplotlib==3.10.1 scikit-image==0.24.0

echo.
echo ✓ Visualization dependencies installed successfully!
echo.
echo Note: Make sure the CRAFT model file is present at:
echo   char_visualisation\line-segmentation\pretrained_craft\craft_mlt_25k.pth
echo.
pause
