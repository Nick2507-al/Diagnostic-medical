@echo off
chcp 65001 >nul
title MediAI
cd /d "%~dp0"

if not exist backend\.venv\Scripts\python.exe (
  echo [ERREUR] Environnement Python absent. Voir README.md, section Installation.
  pause & exit /b 1
)
if not exist frontend\node_modules (
  echo [ERREUR] Dependances du frontend absentes : lancez "npm install" dans le dossier frontend.
  pause & exit /b 1
)

echo Application des migrations de la base de donnees...
pushd backend
.venv\Scripts\alembic upgrade head || (echo [ERREUR] Migration impossible : PostgreSQL est-il demarre ? & popd & pause & exit /b 1)
popd

echo Demarrage de l'API (port 8000)...
start "MediAI - API" /d "%~dp0backend" cmd /k ".venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Demarrage de l'interface (port 3000)...
start "MediAI - Interface" /d "%~dp0frontend" cmd /k "npm run dev"

timeout /t 8 /nobreak >nul
start http://localhost:3000
