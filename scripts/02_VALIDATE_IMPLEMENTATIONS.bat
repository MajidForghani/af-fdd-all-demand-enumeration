@echo off
setlocal
cd /d "%~dp0"
call conda activate af_fdd_final
if errorlevel 1 goto :error
set PYTHONPATH=src
python -m unittest discover -s tests -v
if errorlevel 1 goto :error
echo.
echo Validation passed. Next run 03_RUN_SMOKE_TEST.bat
pause
exit /b 0
:error
echo Validation failed. Stop and copy the complete screen output.
pause
exit /b 1
