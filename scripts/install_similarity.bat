@echo off
echo ========================================
echo Installing Semantic Similarity Feature
echo ========================================
echo.

echo Activating virtual environment...
call ocr_env\Scripts\activate.bat

echo.
echo Installing sentence-transformers...
pip install sentence-transformers

echo.
echo Installing numpy (if not already installed)...
pip install numpy

echo.
echo ========================================
echo Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Run: python migrate_db.py
echo 2. Start app: python app.py
echo 3. Test similarity feature on review page
echo.
pause
