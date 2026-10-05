@echo off
rem Serve this folder at http://localhost:8000 and open it in the browser.
rem Close this window (or press Ctrl+C) to stop the server.
cd /d "%~dp0"
set PORT=8000
rem Open the browser a second later so the server is already listening.
start "" /min cmd /c "ping -n 2 127.0.0.1 >nul & start "" http://localhost:%PORT%/"
echo Serving %CD% at http://localhost:%PORT%/
echo Close this window to stop.
python -m http.server %PORT% --bind 127.0.0.1
pause
