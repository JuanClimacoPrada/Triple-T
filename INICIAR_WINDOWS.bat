@echo off
setlocal
cd /d "%~dp0"
echo ===========================================
echo BCP RiskPredict - Prototipo academico
 echo ===========================================
if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    py -m venv .venv
    if errorlevel 1 goto :error
)
echo Instalando/verificando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error
echo Abriendo chatbot...
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 goto :error
exit /b 0
:error
echo.
echo Hubo un error. Verifica que Python este instalado y que tengas conexion a Internet.
pause
exit /b 1
