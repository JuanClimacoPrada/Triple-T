# Triple-T — asistente académico de análisis crediticio

## Alternativas de un mismo crédito

La pestaña **Alternativas** calcula tres condiciones de préstamo bajo tres
escenarios editables de ingreso. Muestra consecuencias, alertas y puntuación
ponderada. La elección del analista y su justificación se incorporan al PDF.
[Flujo, ponderación y verificación](docs/ALTERNATIVAS_CREDITO.md).

## Riesgo hipotético y Sentinel

«Evaluación del riesgo crediticio» separa capacidad financiera de los supuestos
de PD. En Indicadores se editan tres escenarios sin cifras precargadas, horizonte
explícito, complemento 100% − PD y pérdida ilustrativa con LGD y exposición.
No existe modelo predictivo validado. El score externo permanece no disponible;
un score manual solo puede registrarse como simulado, con fuente y fecha.
El enlace `SENTINEL_URL` abre el portal oficial sin datos del expediente.
Consulta [alcance, contratos futuros y validación](docs/RIESGO_HIPOTETICO.md).

## Diseño profesional integrado

Navegación lateral, chat guiado y panel financiero progresivo inspirado en el flyer.
Los indicadores y gráficos utilizan el motor existente. La tarjeta «Score crediticio»
muestra «No disponible» y permite configurar un enlace externo mediante
`SENTINEL_URL`, sin transmitir el expediente. Consulta [integración y pendientes](docs/UI_PRO.md).
El diseño inicial se entregó sin pruebas por instrucción del responsable. La mejora
de riesgo incluye la actualización y ejecución de las pruebas autorizadas;
la validación visual completa y capturas siguen pendientes.

## Sprint 5 — evaluación guiada, documentos y resumen visual

Inicia una evaluación o una simulación y responde una pregunta por vez. Puedes
registrar varios datos juntos, dejar lo desconocido pendiente, presentar respaldos,
revisar fuentes y confirmar antes de calcular. Las tarjetas muestran cuota, DTI,
disponible y estado de revisión. Escenarios, gráficos, cronograma y PDF reutilizan
el motor Python. Solo crédito personal en PEN.

**Toda la captura y el procesamiento documental funcionan sin Gemini.** Desde
el chat se puede activar Gemini para interpretar consultas de demostración
durante la captura y el análisis. Python valida entidades, calcula los
indicadores y pide confirmación para aplicar cambios propuestos.

Los archivos se procesan en el **servidor** de Triple-T. En Community Cloud no es
el equipo del usuario. Solo se permiten documentos de demostración sin identificadores.
Otros respaldos y patrimonio se registran para revisión, sin convertir importes en
ingreso ni garantías. La confirmación es de transcripción, nunca de autenticidad.

`APP_ENV="demo"` es la única modalidad habilitada; configurar otro entorno bloquea
la aplicación. `GEMINI_ENABLED=false` deshabilita las consultas remotas. No se agregan
dependencias ni servicios de pago. [Arquitectura, matriz y guía manual del Sprint 5](docs/SPRINT_5.md).

## Configuración opcional de Gemini

Gemini interpreta la consulta filtrada y devuelve intenciones, referencias,
entidades y explicaciones en JSON. Python valida el esquema y resuelve los
datos de la explicación con los resultados del motor. El modo local está
disponible siempre.

1. Instala `requirements.txt` y ejecuta Streamlit como se indica abajo.
2. El responsable verifica el nivel gratuito de su cuenta en
   [Google AI Studio](https://aistudio.google.com/apikey) y la
   [tarifa vigente](https://ai.google.dev/gemini-api/docs/pricing), sin activar facturación.
3. Copia `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` (ignorado
   por Git), o configura Secrets en Community Cloud después de la revisión.
   Define `GEMINI_API_KEY`, `GEMINI_MODEL` y `GEMINI_FREE_TIER_CONFIRMED = true`
   únicamente tras verificar acceso gratuito. También se admiten variables de entorno.
   No compartas la clave en chat, GitHub, capturas ni informes.
4. Abre «Gemini opcional» en el chat, lee el aviso, consiente y activa Gemini.
   «Seguir sin IA» vuelve al flujo local. Al reiniciar un caso se solicita el
   consentimiento de nuevo.
   Configuración disponible no significa conexión probada: el panel indica si Gemini
   ya respondió en la sesión y muestra un motivo seguro cuando falla.

El chat presenta las herramientas a medida que hacen falta: escribe «subir boletas»,
«ver gráfico» o «genera PDF». El expediente, edición manual, costos y casos ficticios
están en la barra lateral, cerrada al comenzar. [Cambios de interfaz y comprobaciones pendientes](docs/CHAT_CONTEXTUAL.md).

El nivel gratuito puede usar el contenido enviado para mejorar productos.
No se transmiten documentos ni OCR; el detector de identificadores es conservador
y no garantiza anonimización. No se habilita facturación ni se selecciona otro
modelo ante errores. La confirmación de gratuidad es declarativa, no una comprobación
automática de la cuenta. [Configuración, aceptación y pendientes](docs/SPRINT_4.md).

## Sprint 3 — conversación principal

Introduce datos y consultas en español desde el chat: captura múltiple, preguntas
por faltantes, cuota parcial, correcciones confirmadas, boletas, escenarios, gráficos
y PDF. El panel experto y el análisis estratégico son secundarios; no es obligatorio
recorrer pestañas. El Sprint 3 aporta el intérprete **local de intenciones y reglas**;
el Sprint 4 añade la interpretación remota opcional.

Ejemplo: «Cliente gana 3500 soles, solicita 10000 soles a 12 meses con TEA 25%»;
después «¿cuál es la cuota?», «gastos 1400 y otras cuotas 300» o «¿y a 24 meses?».
Solo personal PEN. Las decisiones corresponden al analista; solo datos ficticios.

[Arquitectura, decisiones, aceptación y pendientes del Sprint 3](docs/SPRINT_3.md).
Reutiliza el motor, documentos, simulaciones y PDF del Sprint 2 sin nuevas dependencias.

## Triple-T v2.0 — Sprint 2

Flujo de seis pasos: **Datos → Evidencias → Confirmar → Analizar → Simular → Reporte**.
Crédito personal en PEN, DTI total configurable, ingresos de 3–6 meses confirmados,
extracción local de PDF y OCR opcional con fallback manual, simulaciones independientes,
cargos separados, TCEA referencial con flujos completos y reporte PDF trazable.
Los otros productos quedan «próximamente» y el módulo estratégico 3×3 se conserva.

Consulta el [manual y matriz de aceptación](docs/SPRINT_2.md) y
las [limitaciones de seguridad, OCR, TCEA y despliegue](LIMITACIONES.md).
Solo datos sintéticos/anónimos: confirmar transcripción no verifica autenticidad.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

Para Community Cloud, incluir **todo el repositorio** (módulos `dominio/`,
`servicios/`, `casos.py`, `visualizaciones.py`, `ui_estrategia.py` y `.streamlit/config.toml`).
No se necesitan secretos ni APIs de pago. Tesseract es opcional; sin él se ofrece
transcripción manual. La verificación en el despliegue público queda pendiente
de revisión/autorización; esta entrega no despliega ni fusiona.

## Sprint 1 — Triple-T

Incluye perfiles configurables personal, vehicular, hipotecario y empresarial,
capacidad de pago y endeudamiento ampliados, simulador de monto/plazo/TEA y tabla
de amortización exportable. Las políticas específicas por producto quedan
pendientes de definición; se conservan las reglas académicas y los nueve escenarios.
Consulta [convenciones financieras, fórmulas y validación](docs/SPRINT_1.md).
La calculadora de pérdida esperada requiere PD y LGD introducidas por el usuario,
sin probabilidades precargadas. Todos los resultados requieren revisión humana.

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
2. Sube `app.py`, `motor.py`, `reglas_credito.py`, `requirements.txt`, `README.md`, `docs/` y `tests/`.
3. Accede a https://share.streamlit.io/, vincula GitHub y selecciona repo/branch con entrada `app.py`.
4. La plataforma genera una URL pública para incluir en la ficha.

## Cómo se usa

- **Chatbot de evaluación:** ingresa 8 parámetros sintéticos o carga un caso de prueba. El sistema calcula una cuota por sistema francés y muestra alertas basadas en reglas del ejercicio.
- **Alternativas estratégicas:** simula tres opciones (reglas, scoring hipotético, chatbot con scoring hipotético), cruzadas con tres escenarios de tiempos operativos. Los presupuestos y reducciones porcentuales son **supuestos académicos**, no cifras del BCP.
- **Metodología:** describe cómo se relacionan los pasos 1–6 con la ficha de trabajo.

## Límites metodológicos

- Triple-T usa reglas y cálculos deterministas para sus indicadores financieros. Gemini es opcional y cumple una función conversacional. Las alternativas B/C del módulo estratégico modelan inversiones hipotéticas. El proyecto carece de un modelo predictivo de riesgo entrenado y calibrado.
- El **30% de cuota/ingreso** y las reglas de mora/estabilidad vienen del ejemplo académico del equipo y NO son políticas oficiales del BCP.
- La PD se puede introducir como **supuesto** para ilustrar `Pérdida esperada = EAD × PD × LGD`; no se estima ni valida aquí.
- Costos, tiempos y rentabilidad del análisis estratégico son totalmente hipotéticos. Las horas liberadas no garantizan ahorros monetarios.
- Ningún resultado supone aprobación o rechazo automáticos de personas.

## Futuro

Una segunda versión podría incluir un modelo de scoring *validado* con datos públicos/sintéticos adecuados, métricas de calibración, auditoría, documentación del origen de datos y herramientas de explicación, siempre con supervisión humana.
# Triple-T
