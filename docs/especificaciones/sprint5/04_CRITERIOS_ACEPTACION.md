# Sprint 5 unificado — Matriz de aceptación de Triple-T

**Obligatorio:** para cada criterio dejar prueba automatizada cuando sea viable, evidencia de UI cuando corresponda, y estado `PASA`, `FALLA` o `PENDIENTE CON JUSTIFICACIÓN`. No presentar criterios no ejecutados como completados.

| ID | Escenario de prueba | Comportamiento exigido |
|---|---|---|
| CA-01 | Abrir por primera vez | Saludo breve, comenzar evaluación en un toque, sin exponer `None`/JSON/campos técnicos |
| CA-02 | Escribir `hola` | Contesta natural, ofrece opciones; no mensaje genérico de SDK o ayuda larga |
| CA-03 | Analista nuevo pulsa iniciar | Pregunta monto o primera variable esencial y muestra progreso |
| CA-04 | `Quiero 15000 en 24 meses` | Captura dos campos y pregunta solo TEA; no repite |
| CA-05 | Analista desconoce TEA | Marca pendiente, explica cómo obtenerla; no asigna valor ni calcula cuota con tasa inventada |
| CA-06 | Mensaje con ingresos 3500, gastos 1400 y cuotas 300 | Extrae los tres datos y pregunta descuentos de planilla |
| CA-07 | `No sé` o `Agregar después` | Permanece pendiente; nunca se convierte en cero ni en información verificada |
| CA-08 | `No tiene historial` | `INSUFICIENTE` o desconocido según expresión; `dias_mora=None`, sin inferir mora |
| CA-09 | Analista presenta boleta de prueba | Uploader contextual, sin salir del chat y sin solicitar Gemini |
| CA-10 | Tres boletas sintéticas de distintos meses confirmadas | Promedio de ingresos calculado por motor con fuentes y meses correctos |
| CA-11 | Boleta pendiente/no confirmada | No entra en el promedio ni se etiqueta verificada |
| CA-12 | Dos boletas del mismo mes | Detecta duplicado, pide decisión documentada, no escoge automáticamente |
| CA-13 | Documento corrupto/ilegible | Alerta con siguiente paso, sin perder expediente ni datos |
| CA-14 | Ingreso declarado contradice boletas | Exige aclaración y justificación antes de evaluación sustentada |
| CA-15 | Analista dice tener un inmueble | Ofrece panel local de documento de propiedad, registra tipo y valor fuente/estado |
| CA-16 | Documento de propiedad/titularidad | Nunca afirma validación registral, garantía constituida ni capacidad de pago por patrimonio |
| CA-17 | Archivo de propiedad de prueba con nombre/identificador | No se envía a Gemini ni aparece en contexto remoto, logs o PDF completo |
| CA-18 | Usuario omite documento | Estado `Pendiente de evidencia`; permite ver cálculos parciales etiquetados |
| CA-19 | Cuota 10000, 12 meses, TEA 25 | Cuota base aprox. S/ 938.46, igual al motor existente |
| CA-20 | Todos los datos requeridos completos | Cuatro cards coherentes: cuota, DTI, disponible, estado de revisión |
| CA-21 | Sin ingresos suficientes para DTI | Card DTI `Pendiente`, sin 0, sin recomendación favorable |
| CA-22 | Alertas múltiples | Máximo una alerta destacada + `Ver todas`; texto breve y comprensible |
| CA-23 | Ver gráfico y amortización | Uso exclusivo de resultado calculado; sin sobrecargar vista inicial |
| CA-24 | Simular plazo 24 sobre base 12 | Mantiene base intacta, diferencia visible en cards/tabla/gráfica |
| CA-25 | Generar PDF y corregir dato financiero | Informe anterior invalidado; no descargar reporte obsoleto |
| CA-26 | Antes del análisis: saludar, preguntar TEA, subir archivo | Cero llamadas remotas a Gemini incluso si hay una clave configurada |
| CA-27 | Después del análisis: botón IA sin consentimiento | No realiza llamada remota, explica consentimiento y permite modo local |
| CA-28 | IA habilitada tras resultado | Envía solo allowlist de hechos derivados; cero bytes/fragmentos de PDF, OCR, filename o notas libres |
| CA-29 | Pregunta IA sobre DTI o alerta | Respuesta sustentada en datos, sin cifras nuevas ni aprobación |
| CA-30 | Pregunta de escenario tras resultado | Cálculo efectuado primero en simulador local; explicación posterior usa cifras verificadas |
| CA-31 | Gemini devuelve importe incorrecto, inventa PD o aprobación | Rechaza respuesta o sustituye por explicación determinista; expediente intacto |
| CA-32 | Gemini falla 404/429/timeout o no hay clave | Fallback funcional, expediente y PDF conservados; diagnóstico seguro no invasivo |
| CA-33 | Cambiar ingreso/gasto/documento | Marca revisión nueva e invalida estados/cifras/IA/PDF obsoletos |
| CA-34 | Sidebar escritorio | Cerrado al inicio; opciones comprensibles y acorde a etapa |
| CA-35 | Sidebar móvil 375 px | Drawer legible, cards apiladas, sin desbordamiento horizontal |
| CA-36 | Teclado y accesibilidad | Botones y tarjetas rotulados, orden foco lógico, no solo color |
| CA-37 | Demo pública intenta documento real o PII | Bloquea/no acepta y explica; no transmite a Gemini |
| CA-38 | APP_ENV=private_pilot/production sin habilitación | Falla cerrado, no habilita captura de datos reales |
| CA-39 | Tres alternativas × tres escenarios estratégicos | Continúa disponible y separado de evaluación individual |
| CA-40 | Todas las pruebas | Corre regresión anterior actualizada + nuevos tests sin pasar claves ni credenciales |
| CA-41 | Cinco recorridos guiados por analistas/usuarios nuevos | Registrar fricciones y demostrar tareas completadas; si no hay participantes, marcar pendiente, no inventar resultados |
| CA-42 | Vista PDF/resultado y datos de evidencia | Fuentes, pendientes, supuestos y versión de reglas legibles; sin documento bruto |

## Casos de recorrido manual prioritarios

**Recorrido A — Ingreso formal:** iniciar, monto, plazo, TEA, ingreso/gastos/deuda, sin mora declarada, subir 3 boletas de prueba, confirmar, revisar cards, simular 24 meses, PDF, preguntar a IA por DTI.

**Recorrido B — Historial insuficiente:** indicar falta historial, documentos incompletos, propiedades declaradas, comprobar no equiparar propiedad con liquidez ni sin historial con mora; resultado pendiente de verificación.

**Recorrido C — Fallo sin IA:** sin clave de Gemini completar todo el recorrido financiero; verificar que cards/gráficos/PDF funcionen y que el proveedor tenga 0 llamadas.

**Recorrido D — Contradicción:** ingresos declarados vs boletas diferentes, exigir aclaración; corregir, invalidar informes y permitir finalizar sin datos falsificados.

**Recorrido E — Preguntas abiertas post-informe:** preguntar «¿por qué el DTI es alto?», «¿qué pasa si lo amplío a 24 meses?», «¿apruebo el préstamo?». La IA explica solo hechos comprobados y nunca decide.
