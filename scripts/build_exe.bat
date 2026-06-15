@echo off
setlocal
cd /d "%~dp0\.."

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m PyInstaller --noconsole --onefile --name FishReader app.py

echo.
echo Build complete: dist\FishReader.exe
