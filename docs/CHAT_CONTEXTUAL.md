# Chat contextual y estado de Gemini

Cambios posteriores al Sprint 4, sobre `origin/main` (incluida la corrección del
adaptador Gemini ya fusionada). No cambian fórmulas, políticas de crédito ni fuentes
de datos. La interfaz sigue en Streamlit y no incorpora dependencias nuevas.

## Interfaz

- Conversación centrada, bienvenida breve, entrada fija y señal de procesamiento.
- Desaparece la fila permanente de cinco botones; se puede pedir cada acción por chat.
- Barra lateral cerrada al inicio: expediente, casos, edición manual, costos, parámetros,
  PD/LGD ilustrativas y acceso a las tres alternativas/nueve escenarios estratégicos.
- Adjuntos al pedir evidencias; acceso contextual cuando faltan boletas. Una corrección
  de datos ya no abre innecesariamente el formulario de archivos.
- Confirmar/cancelar únicamente ante cambios pendientes. Se preservan ambos controles.
- Detalle plegado cuando hay cifras; se abre al solicitar gráficos/amortización/explicación.
  PDF se solicita por chat o desde el detalle; la descarga aparece cuando está generado.

## Conexión

Un panel junto al título reúne consentimiento y activación en un interruptor. Desactivado
al inicio; sin conexión de prueba ni reintentos automáticos. Los fallos devuelven el
interruptor a apagado y conservan los datos. Reactivar es una decisión explícita.

Se diferencian configuración incompleta, configuración disponible sin llamada y respuesta
validada recibida. Un mensaje resuelto por el parser local no se presenta como respuesta
de Gemini. El contador conserva el límite de veinte llamadas y no se reinicia al crear
un caso nuevo.

El adaptador traduce excepciones a códigos permitidos: acceso, cuota, modelo, solicitud,
timeout, dependencia o conexión; el validador distingue una respuesta no aceptada.
Nunca se muestra ni registra el texto remoto de la excepción. Un 400 puede deberse a
varias causas: su mensaje invita a revisar compatibilidad, sin afirmar un diagnóstico
que requiera inspeccionar secretos. La configuración admite espacios exteriores y el
prefijo `models/` en el identificador, sin elegir modelos alternativos.

## Validación pendiente del usuario

Por petición expresa, no se ejecutaron pruebas, no se creó una suite nueva ni se llamó
a Gemini. Solo se revisaron código y diferencias. No se declara verificada la conexión
real ni la presentación visual. Los tests de interfaz anteriores tienen expectativas
de la pantalla antigua (por ejemplo, nueve filas estratégicas en el inicio) que deberán
adaptarse al nuevo flujo si se decide mantenerlos; no se modificaron ni excluyeron.

Para la revisión manual del usuario tras desplegar la rama:

1. Inicio con chat limpio; abrir herramientas laterales cuando se necesiten.
2. Activar Gemini con consentimiento y enviar la paráfrasis del Sprint 4; comprobar
   respuesta validada o motivo de error, sin compartir la clave.
3. Pedir «¿y a 24 meses?», revisar base intacta, pedir gráfico y PDF.
4. Pedir boletas y confirmar evidencia sintética; corregir ingreso y cancelar el cambio.
5. Desactivar Gemini, continuar localmente y revisar la interfaz en móvil.

No se fusiona ni despliega automáticamente esta rama.
