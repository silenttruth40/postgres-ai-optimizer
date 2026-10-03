@echo off
title PostgreSQL AI Performance Optimizer
echo ========================================================
echo Starting PostgreSQL AI Performance Optimizer...
echo ========================================================

REM Run python launcher using virtualenv if available
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" run.py
) else (
    python run.py
)
pause
