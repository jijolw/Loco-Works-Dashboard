@echo off
title Supabase ERP Dashboard (Port 5001)
cd /d "%~dp0"
echo ==========================================
echo Starting Supabase ERP Web App...
echo URL: http://localhost:5001
echo ==========================================
python app.py
pause
