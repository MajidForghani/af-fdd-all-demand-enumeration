@echo off
setlocal
cd /d "%~dp0"
call conda create -n af_fdd_final python=3.12 -y
if errorlevel 1 goto :error
call conda activate af_fdd_final
if errorlevel 1 goto :error
python -m pip install -e .
if errorlevel 1 goto :error
echo.
echo Installation completed. Next run 02_VALIDATE_IMPLEMENTATIONS.bat
pause
exit /b 0
:error
echo Installation failed. Please copy the complete screen output.
pause
exit /b 1
