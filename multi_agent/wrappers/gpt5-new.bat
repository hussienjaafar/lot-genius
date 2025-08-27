@echo off
REM Create a GPT-5 draft prompt. Pass --title and one of --text/--file.
python "%~dp0..\prompt_flow.py" new --from gpt5 --to claude %*
