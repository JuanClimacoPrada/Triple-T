# Triple-T — Mapa técnico del código actual

**Fuente del análisis:** `JuanClimacoPrada/Triple-T`, rama `main`, commit `c9c4e142bcf88ead260c653fd1ae0127906b2a86` (21-11-2026). Este documento describe el código inspeccionado; no acredita funcionamiento de producción ni acceso a sistemas del BCP.

## 1. Resumen ejecutivo

Triple-T es una aplicación Python/Streamlit con un chat principal, un analizador local de intenciones, un intérprete Gemini opcional, un gestor de expediente en memoria, un motor de cuotas y riesgo basado en reglas, lectura documental, simulación y PDF. **Gemini interpreta consultas; no realiza la decisión crediticia ni redacta libremente la respuesta final.** Solo crédito personal en PEN está habilitado. El módulo estratégico de tres alternativas × tres escenarios se mantiene separado de la evaluación individual.

## 2. Ejecución y capas

1. `app.py`: punto de entrada Streamlit. Configura título, página centrada y barra lateral plegada; llama a `ui_chat.mostrar_chat()`.
2. `ui_chat.py`: dibuja conversación, encabezado y control de Gemini; barra lateral con expediente y herramientas; confirmaciones, carga de documentos, detalles financieros y PDF. Guarda sesión de Streamlit. **No debería contener reglas de decisión.**
3. `conversacion/modelos.py`: dataclasses `Conversacion`, `Mensaje`, `Interpretacion`. Guarda expediente base, lista de mensajes, estado, revisión, acciones pendientes, resultado, escenario, documentos, informe, última pregunta y preferencias de vista.
4. `conversacion/intenciones.py`: parser local de expresiones regulares en español. Detecta monto, ingresos, gastos, otras cuotas, plazo, TEA, historial, mora, tipos de acción, etc. Bloquea ambigüedades y cifras que no puede interpretar. No es comprensión libre del español.
5. `ia/politicas.py`: enruta primero al parser local. Solo determinados mensajes no reconocidos o números escritos en palabras llegan a Gemini si existe configuración, consentimiento y presupuesto. Aplica hasta 20 llamadas por sesión, corta ante errores y retorna un código de causa sin revelar texto de excepciones.
6. `ia/proveedor.py`: lee `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_FREE_TIER_CONFIRMED`; usa SDK `google-genai`, salida JSON, modelo explícito, sin herramientas, tiempo límite y sin reintento automático.
7. `ia/esquemas.py`: valida JSON de Gemini, acción de lista permitida, tipo de cada campo, rangos, coherencia y fragmentos literales del mensaje como respaldo de valores; impide que Gemini invente cantidades.
8. `ia/privacidad.py`: bloquea algunos patrones de identificación y construye un contexto remoto reducido. No se envían por esta vía documentos, OCR o historial completo de chat. **No garantiza anonimización.**
9. `conversacion/gestor.py`: orquesta todo. Actualiza datos con validación, pide confirmación antes de reemplazar valores, invalida simulaciones/reportes anteriores, deriva cálculos al motor, genera simulaciones y reportes; no aprueba créditos.
10. `conversacion/respuestas.py`: plantillas textuales para listar faltantes, preguntar siguiente dato, informar cuotas, DTI, alertas, supuestos y límites. Esta capa explica por qué saludos o preguntas abiertas reciben respuestas mecánicas pese a existir Gemini.

## 3. Modelo de expediente, reglas y cálculos

11. `dominio/modelos.py`: `Expediente` inmutable con monto, meses, TEA, ingreso, gastos, otras cuotas, estabilidad, estado declarado del historial, posibles días de mora, descuento de planilla, evidencia, cargos, fechas, patrimonio y fuentes. `Evidencia` registra archivo/región, valor, fecha y estado; `Configuracion` contiene umbral DTI 30 %, tolerancia documental 10 % y tope TEA técnico; `Resultado` guarda cifras, alertas, tabla, promedio y TCEA. **Los valores 30 % y 10 % son parámetros pedagógicos, no una política bancaria aprobada.**
12. `servicios/finanzas.py`: validación numérica con `Decimal`; cuota por amortización francesa, `TEM = (1+TEA/100)^(1/12)-1`; cronograma de interés, amortización, cargos y saldo; fechas mensuales y cálculo referencial anualizado de TCEA con flujos completos y fecha explícita.
13. `servicios/reglas.py`: `analizar(expediente, configuracion)` valida campos, historial y cargos; usa 3–6 meses únicos de boletas confirmadas; detecta duplicados y discrepancias; calcula cuota, pago mensual total, saldo postcuota y `DTI = (otras_cuotas + nueva_cuota + cargos_mensuales_del_solicitante) / ingreso_admisible`; produce alertas y estados. No aplica modelos predictivos reales.
14. `servicios/simulacion.py`: copia el expediente, cambia monto/plazo/TEA y/o aplica caída de ingresos; mantiene expediente base intacto. Bloquea simulación de capacidad si hay datos faltantes o discrepancias que impiden análisis.
15. `servicios/documentos.py`: recibe PDF/PNG/JPEG, valida tamaño y páginas, extrae texto PDF con `pypdf`, previsualiza con `pypdfium2`, OCR opcional con Tesseract, identifica posibles candidatos de ingreso neto y pide confirmación o descarte manual. No comprueba autenticidad de boletas o identidad.
16. `servicios/reporte.py`: crea PDF con `reportlab`: entradas, indicadores, alertas, fuentes, hipótesis, comparaciones y estado. No incluye documentos originales completos.
17. `visualizaciones.py`, `ui_resultados.py`: tablas y gráficos de saldo, interés/capital, ingreso y escenarios a partir de resultados del motor.
18. `casos.py`: cuestionario heredado y casos de demostración. **No confundir este catálogo con expedientes de clientes reales.**
19. `motor.py`, `reglas_credito.py`: motor original del Sprint 1, compatibilidad de cálculos y análisis estratégico. Perfiles de personal, vehicular, hipotecario y empresarial definidos, pero los tres últimos no tienen política operativa detallada.
20. `ui_estrategia.py`: compara inversiones tecnológicas A/B/C en 3 escenarios; cifras y beneficios son supuestos, no datos observados del banco.
21. `tests/`: pruebas de motor, interfaz de etapas previas, servicios y conversación. El PR #5 indica que algunas pruebas de UI siguen esperando componentes anteriores y que no se ejecutó regresión tras rediseñar; deben actualizarse.
22. `requirements.txt`: Streamlit, pypdf, ReportLab, pypdfium2 y google-genai; otras librerías pueden ser dependencias transitivas. `.streamlit/secrets.toml.example` ejemplifica credenciales y `.gitignore` excluye la clave local.

## 4. Flujo real actual

- El analista escribe: `Cliente gana 3500 soles, solicita 10000 soles a 12 meses con TEA 25%`.
- `ui_chat.py` llama a `conversacion.gestor.recibir`.
- `ia/politicas.py` prioriza la interpretación local. Si no es suficiente y hay consentimiento, consulta Gemini; el JSON debe superar `ia/esquemas.py`.
- `gestor.proponer/aplicar` registra campos declarados y su procedencia en `Expediente`; puede solicitar confirmación antes de sustituir datos existentes.
- `servicios/reglas.py` detecta faltantes; si faltan ingresos/gastos, el gestor aún puede usar `cronograma` para informar una **cuota teórica**, sin afirmar capacidad de pago.
- `respuestas.py` redacta una respuesta construida con resultados y solicita el siguiente dato.
- Si el analista escribe `¿y a 24 meses?`, `gestor.crear_escenario` modifica una copia; muestra comparación, gráfico y PDF, conservando la base.
- Si adjunta boletas, `documentos.py` produce candidatos pendientes; el analista confirma importes y meses antes de que `reglas.py` pueda promediarlos.

## 5. Límites actuales que impiden usar expedientes personales reales

- No hay autenticación/autorización de analistas ni roles; la URL pública da acceso al prototipo.
- El expediente y archivos viven en la sesión de Streamlit; no hay gestor empresarial de expedientes ni auditoría durable de quién accedió/corrigió/aprobó.
- No hay custodia segura documental verificada, antivirus/sandbox robusto, calendario de retención ni flujo para ejercer derechos sobre datos.
- La detección de identificadores es parcial; no se puede prometer que el servicio gratuito de Gemini no reciba datos personales.
- Los documentos no se autentican; se confirma transcripción, no veracidad.
- No existen convenios/integraciones autorizados con fuentes bancarias ni centrales de riesgo.
- Las reglas siguen siendo configuraciones de demostración, no políticas institucionales aprobadas.
- Gemini no estima PD ni hay modelo predictivo entrenado y validado.
- El cambio de interfaz del PR #5 no tiene pruebas de regresión actualizadas/ejecutadas en ese PR.

**Conclusión:** mejorar primero la UX con datos no personales en el sitio público. Diseñar despliegue privado con requisitos de gobierno y seguridad antes de usar expedientes reales.
