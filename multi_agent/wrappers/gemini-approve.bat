@echo off
REM Approve a draft by id and optionally --send to Claude
python "%~dp0..\prompt_flow.py" approve --from gemini --to claude %*
