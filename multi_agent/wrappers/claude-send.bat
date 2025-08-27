@echo off
REM Send a message FROM claude; pass remaining args to bus.py
python "%~dp0..\bus.py" send --from claude %*
