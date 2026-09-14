@echo off
rem Double-click before a Meet. Starts OFF - your plain webcam - with the hotkeys on.
rem Keep this window open for the whole call; closing it turns Meet's camera black.
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
  echo Not set up yet. Run:  powershell -ExecutionPolicy Bypass -File setup.ps1
  pause
  exit /b 1
)
title Meme Cam - keep open during the Meet
set GLOG_minloglevel=2
echo Starting the meme cam. In Meet pick "OBS Virtual Camera".
echo   ctrl+alt+A  gesture mode 60s     ctrl+alt+F  FAHHHHH
echo   ctrl+alt+N  manual               ctrl+alt+.  off
echo   ctrl+alt+1-9 0 - = [ ]  fire a meme     q twice in the preview  quit
echo.
venv\Scripts\python.exe its_giving_v2.py --hotkeys
echo.
echo Meme cam stopped. Meet's camera is black until you start it again.
pause
