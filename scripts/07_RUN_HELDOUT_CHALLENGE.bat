@echo off
setlocal
cd /d "%~dp0"
call conda activate af_fdd_final
if errorlevel 1 goto :error
python run_comprehensive.py --profile challenge-definitive --repetitions 3 --timeout 600 --memory-gib 12
if errorlevel 1 goto :error
echo.
echo Held-out challenge completed.
echo Send the complete study\results\challenge-definitive folder.
pause
exit /b 0
:error
echo The run stopped. It is resumable: run this same file again after checking the error.
pause
exit /b 1
