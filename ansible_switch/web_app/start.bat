@echo off
echo ============================================
echo   Ansible Switch Manager - Web Interface
echo ============================================
echo.
echo Starting server on http://localhost:8000
echo Press Ctrl+C to stop the server
echo.

cd /d "%~dp0.."
python -m uvicorn web_app.app:app --host 0.0.0.0 --port 8000 --reload
