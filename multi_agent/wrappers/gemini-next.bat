@echo off
REM Fetch next pending message FOR gemini
python "%~dp0..\bus.py" next --agent gemini %*
