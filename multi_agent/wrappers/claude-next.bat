@echo off
REM Fetch next pending message FOR claude
python "%~dp0..\bus.py" next --agent claude %*
