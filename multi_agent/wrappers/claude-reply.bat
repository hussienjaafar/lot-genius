@echo off
REM Reply as claude; requires --parent <MSG_ID>
python "%~dp0..\bus.py" reply --from claude %*
