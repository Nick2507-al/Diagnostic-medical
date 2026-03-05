@echo off
chcp 65001 >nul
title MediAI - Assistant Diagnostic Medical

cd /d "%~dp0"

echo ========================================
echo   MediAI - Demarrage de l'application
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    pause
    exit /b 1
)

echo Lancement de l'interface Gradio...
echo.
echo Le navigateur s'ouvrira dans 3 minutes (sans GPU, le chargement est plus long).
echo Si la page affiche "site inaccessible", attendez le message "Running on..."
echo puis cliquez sur Actualiser (F5) dans le navigateur.
echo.
echo Appuyez sur Ctrl+C pour arreter l'application.
echo ========================================
echo.

start /b cmd /c "timeout /t 180 /nobreak >nul && start http://127.0.0.1:7860"

python run_demo.py

pause
