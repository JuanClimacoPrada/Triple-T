# RiskPredict — chatbot académico BCP (MVP)

Aplicación **independiente y educativa**, no afiliada al BCP. No utilizar para decisiones crediticias reales. No recopilar DNI ni datos personales.

## Ejecutar en Windows (PowerShell o terminal VS Code)

1. Instala Python 3.11 o superior desde https://www.python.org/downloads/ marcando **Add Python to PATH**.
2. Descomprime este paquete y abre la carpeta en VS Code.
3. **Forma rápida:** haz doble clic en `INICIAR_WINDOWS.bat` (necesita Internet para instalar Streamlit la primera vez).

   **Forma manual:** abre la terminal y escribe:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Si prefieres activar un entorno virtual, puedes usar CMD o PowerShell y luego `python -m streamlit run app.py`.

4. Se abrirá el navegador en `http://localhost:8501` (o la dirección local que indique Streamlit).

## Probar el motor

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Publicación gratis

1. Crea repositorio GitHub **solo con estos archivos de código**, sin datos de clientes ni secretos.
2. Sube `app.py`, `motor.py`, `requirements.txt`, `README.md` y `tests/`.
3. Accede a https://share.streamlit.io/, vincula GitHub y selecciona repo/branch con entrada `app.py`.
4. La plataforma genera una URL pública para incluir en la ficha.

## Cómo se usa

- **Chatbot de evaluación:** ingresa 8 parámetros sintéticos o carga un caso de prueba. El sistema calcula una cuota por sistema francés y muestra alertas basadas en reglas del ejercicio.
- **Alternativas estratégicas:** simula tres opciones (reglas, scoring hipotético, chatbot con scoring hipotético), cruzadas con tres escenarios de tiempos operativos. Los presupuestos y reducciones porcentuales son **supuestos académicos**, no cifras del BCP.
- **Metodología:** describe cómo se relacionan los pasos 1–6 con la ficha de trabajo.

## Límites metodológicos

- **No hay Machine Learning entrenado ni IA generativa** en esta versión: es un chatbot conversacional guiado por reglas y cálculos. Las alternativas B/C modelan inversiones hipotéticas, NO simulan la precisión real de un modelo inexistente.
- El **30% de cuota/ingreso** y las reglas de mora/estabilidad vienen del ejemplo académico del equipo y NO son políticas oficiales del BCP.
- La PD se puede introducir como **supuesto** para ilustrar `Pérdida esperada = EAD × PD × LGD`; no se estima ni valida aquí.
- Costos, tiempos y rentabilidad del análisis estratégico son totalmente hipotéticos. Las horas liberadas no garantizan ahorros monetarios.
- Ningún resultado supone aprobación o rechazo automáticos de personas.

## Futuro

Una segunda versión podría incluir un modelo de scoring *validado* con datos públicos/sintéticos adecuados, métricas de calibración, auditoría, documentación del origen de datos y herramientas de explicación, siempre con supervisión humana.
