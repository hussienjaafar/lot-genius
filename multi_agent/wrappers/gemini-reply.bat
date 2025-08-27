@echo off
REM Reply as gemini; requires --parent <MSG_ID>
python "%~dp0..\bus.py" reply --from gemini %*
