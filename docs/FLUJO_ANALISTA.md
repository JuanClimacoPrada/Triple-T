# Flujo de trabajo del analista en Triple-T

La imagen de referencia orienta la paleta azul marino, blanco y azul claro,
el contraste y la jerarquía de las tarjetas. Cada importe, escenario y
puntuación de la aplicación procede del expediente y del motor local.

| Área | Cambio | Archivos principales |
| --- | --- | --- |
| Navegación | Menú lateral compacto para Análisis, Expediente, Historial y Criterios. El Resumen muestra las cifras esenciales y accesos directos a Alternativas e Indicadores. | `ui_flujo.py`, `ui_chat.py`, `triple_t_pro_layout.py`, `triple_t_pro_styles.css` |
| Herramientas de prueba | Los casos sintéticos, la comparación tecnológica, la PD ilustrativa y el score simulado quedan en Desarrollo. La pestaña Indicadores conserva un enlace secundario a Sentinel. | `ui_flujo.py`, `ui_riesgo.py` |
| Alternativas | La acción Analizar abre un único detalle con tres escenarios, desglose de puntos, alertas y selección. La matriz de nueve resultados se abre aparte. | `ui_alternativas.py`, `servicios/alternativas.py`, `experiencia/comparador.py` |
| Elección | La justificación requiere al menos tres palabras distintas de tres o más letras. Se conservan fecha, condiciones, puntuación y justificación en el informe vigente. | `experiencia/comparador.py`, `servicios/reporte.py` |
| Indicadores | Uso de capacidad, margen frente al umbral DTI, costo y alertas al confirmar los datos. Verde indica margen o saldo favorable y rojo identifica exceso o déficit. | `experiencia/tarjetas.py`, `triple_t_pro_layout.py`, `ui_flujo.py` |
| Gráficos y Detalle | Gráficos reúne la deuda, composición de cuotas, uso del ingreso, simulación y escenarios por alternativa. Detalle concentra el cronograma, la exportación CSV y el sustento disponible. | `visualizaciones.py`, `ui_resultados.py`, `ui_flujo.py` |
| TCEA | Diagnóstico por costo, pagador, desembolso, vencimiento y flujo. El acceso abre el formulario de costos y fechas. Guardar recalcula y actualiza la revisión. | `servicios/costos.py`, `servicios/finanzas.py`, `servicios/reglas.py`, `servicios/simulacion.py`, `ui_chat.py` |

## Uso habitual

En **Resumen**, verifica los datos de la solicitud, incluido el ingreso declarado,
el monto, la TEA y el plazo. Al confirmar el expediente, aparecen los resultados y
la sugerencia de Triple-T. La sugerencia se genera localmente con los escenarios
calculados. Explica qué opción revisaría primero, qué se gana y qué se tendría que
revisar antes de elegir. Si falta información o ninguna opción deja margen,
propone revisar los datos o las condiciones.

Pulsa **Ver alternativas**. En el catálogo, pulsa **Analizar alternativa** en la
tarjeta que quieres inspeccionar. Las etiquetas de saldo y DTI muestran por separado
el margen mensual y el cumplimiento del umbral académico, junto al puntaje y el
conteo de escenarios que cumplen los dos criterios.
En el detalle, revisa cómo cambia el saldo con la caída de ingresos, el costo
frente a la solicitud original y el índice ponderado. Para comparar las nueve
filas, vuelve al catálogo y abre la matriz general. Selecciona una alternativa
en su detalle, registra el motivo y prepara el PDF en **Informe e IA**.

En **Indicadores**, los avisos muestran qué dato impide el cálculo y el acceso
para resolverlo. Con ingreso admisible de S/ 0, el DTI se marca explícitamente
como «No calculable». El margen DTI negativo queda en rojo y con signo. En
costos, deja en blanco un importe desconocido, o registra
S/ 0 para un cargo que confirmaste que no aplica. Puedes confirmar el calendario
mostrado o registrar los vencimientos efectivos. Los plazos alternativos pueden
usar calendarios proyectados rotulados como tales. Una TCEA queda pendiente
hasta contar con costos, pagadores y flujos válidos.

Para usar los casos de prueba en un entorno local, ejecuta Streamlit con
`TRIPLE_T_HERRAMIENTAS_DEV=true` y abre **Desarrollo**. La configuración
operativa por defecto oculta ese espacio.

## Gemini y el aviso de conexión

El consentimiento se configura una vez en **Informe e IA → Asistente
conversacional**. Se mantiene durante la sesión y puede retirarse allí. El chat
muestra el estado del asistente. Los saludos, agradecimientos y pedidos básicos
de ayuda se atienden localmente. Las consultas sustantivas admitidas conservan
su interpretación por intención, con hechos validados por Python.

La ruta anterior enviaba «hola» a Gemini y agrupaba errores de inicialización
del SDK con errores de conexión. Eso explica el aviso ante un saludo, aunque
el texto de la pantalla no identifica qué falló en el entorno publicado. La
nueva ruta distingue configuración y SDK, esquema y solicitudes HTTP 400,
autenticación 401, permisos 403, modelo 404, cuota 429, tiempo de espera, DNS,
TLS y validación de respuesta. El registro del servidor incluye la categoría,
etapa, código HTTP cuando existe y versión del SDK. La interfaz continúa con
el asistente local y la evaluación financiera. [Diagnóstico de Gemini](https://ai.google.dev/gemini-api/docs/troubleshooting).

Se comprobó localmente la presencia de las opciones del SDK y su capacidad
para construir la configuración estructurada con `google-genai` 1.75.0.
La clave, el modelo y la confirmación de gratuidad no estaban configurados
localmente. La validación de la cuenta, disponibilidad, cuota y conectividad
de Streamlit Cloud queda pendiente de una consulta autorizada en dicho
entorno. [Salidas estructuradas de Gemini](https://ai.google.dev/gemini-api/docs/structured-output).

## Verificación local

- 123 pruebas satisfactorias con `python -m unittest discover -s tests -v`,
  incluidos los casos de déficit, ingreso cero y sugerencias con y sin alternativa robusta.
- Pruebas de Gemini con proveedor simulado, incluidos el saludo local, la
  interpretación por intención, errores HTTP, timeout y diagnóstico sin secretos.
- Prueba integrada de selección, rechazo de una justificación trivial,
  inclusión en PDF, edición del escenario e invalidación de elección e informe.
- En Edge, a 1440, 820 y 390 px, se abrió el detalle único, se comprobó el ancho
  de las tarjetas de escenario y se accedió a la matriz mediante su vista separada.
- En Edge también se verificaron el control único de consentimiento, el vínculo
  de TCEA al formulario correcto y la descarga del informe.
