@echo off
setlocal
cd /d "%~dp0"
call conda activate af_fdd_final
if errorlevel 1 goto :error
python run_comprehensive.py --profile smoke --timeout 120 --memory-gib 12
if errorlevel 1 goto :error
echo.
echo Smoke test completed. Send the folder study\results\smoke for checking.
pause
exit /b 0
:error
echo Smoke test failed. Stop and copy the complete screen output.
pause
exit /b 1
