@echo off
REM Build_Daily_Position_EXE.bat - makes Daily_Position.exe (Claude for JIJO, 06-11-2026)
REM Run once on JIJO's PC (it has Python). Output folder: D:\Coach_Position_Apps\Daily_Position_EXE
REM Copy that whole folder to the staff PC - no Python needed there.
cd /d "%~dp0"
echo Installing PyInstaller (only the first time)...
python -m pip install --quiet --disable-pip-version-check pyinstaller
echo Building Daily_Position.exe (2-4 minutes)...
python -m PyInstaller --noconfirm --clean --onefile --console --name Daily_Position ^
  --collect-submodules analysis --collect-submodules core --collect-submodules updaters ^
  --hidden-import gspread --hidden-import google.oauth2.service_account --hidden-import openpyxl ^
  daily_position_exe.py
if not exist dist\Daily_Position.exe (
  echo.
  echo BUILD FAILED - send a photo of this window to Claude.
  pause
  exit /b 1
)
set OUT=D:\Coach_Position_Apps\Daily_Position_EXE
if not exist "%OUT%\data" mkdir "%OUT%\data"
copy /y dist\Daily_Position.exe "%OUT%\" >nul
copy /y coach_groups.csv "%OUT%\" >nul
REM holidays / Saturday rule / AC bay fallback come from the app's saved inputs
if not exist "%OUT%\data\daily_report.json" copy /y data\daily_report.json "%OUT%\data\" >nul
REM ERP login: the ERP_ lines of this app's .env (never printed). On the staff PC put HIS login in .env.
if not exist "%OUT%\.env" findstr /b /c:"ERP_" .env > "%OUT%\.env"
REM Google service-account key (read-only use)
if not exist "%OUT%\credentials.json" (
  if exist "D:\JIJO\information\Coach Position\credentials.json" copy /y "D:\JIJO\information\Coach Position\credentials.json" "%OUT%\credentials.json" >nul
)
if not exist "%OUT%\credentials.json" (
  if exist "D:\TypeWiseHoldingApp\credentials.json" copy /y "D:\TypeWiseHoldingApp\credentials.json" "%OUT%\credentials.json" >nul
)
echo.
echo DONE: %OUT%\Daily_Position.exe
echo Double-click it to make today's Daily Position PDF.
pause
