@echo off
REM Acknowledge a message as gemini; requires --msg-id <MSG_ID>
python "%~dp0..\bus.py" ack --agent gemini %*
