@echo off
REM Approve the latest draft (by filename order) and optionally --send
for /f %%i in ('powershell -NoLogo -NoProfile -Command "(Get-ChildItem -Path '%~dp0..\prompts\drafts' -Filter *.md | Sort-Object Name | Select-Object -Last 1).Name -replace '.*_([0-9a-f]{32})_.*','$1'"') do set PID=%%i
if "%PID%"=="" (
  echo No draft prompts found in prompts\drafts
  exit /b 1
)
python "%~dp0..\prompt_flow.py" approve --from gemini --to claude --id %PID% %*
