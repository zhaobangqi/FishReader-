$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m PyInstaller --noconsole --onefile --name FishReader app.py

Write-Host ""
Write-Host "Build complete: dist\FishReader.exe"
