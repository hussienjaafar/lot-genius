@echo off
REM Send a message FROM gemini; pass remaining args to bus.py
python "%~dp0..\bus.py" send --from gemini %*
