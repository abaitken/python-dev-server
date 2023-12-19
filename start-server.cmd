@echo off
title Local Server
cd /d "%~dp0"

SET pythonpath=%USERPROFILE%\AppData\Local\Programs\Python\Python310
SET PATH=%pythonpath%;%PATH%
SET SERVERPORT=8080

SETLOCAL ENABLEDELAYEDEXPANSION

if exist env.user for /f "eol=# tokens=1,2 delims==" %%i in (env.user) do SET %%i=%%j

python localserver

ENDLOCAL
pause

