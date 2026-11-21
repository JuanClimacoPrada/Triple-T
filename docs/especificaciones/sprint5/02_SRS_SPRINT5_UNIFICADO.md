# Triple-T — Sprint 5 unificado: evaluación guiada, evidencias locales, resultados visuales e IA de apoyo posterior

**Versión:** SRS/SDD 2.0 · **Fecha de elaboración:** 21-11-2026
**Base de desarrollo:** repositorio `JuanClimacoPrada/Triple-T`, rama `main`, SHA `c9c4e142bcf88ead260c653fd1ae0127906b2a86` al revisar. Codex debe verificar HEAD al iniciar.
**Sustituye:** `02_SRS_SPRINT5_ASISTENTE_GUIADO.md` anterior. Este documento consolida la UX guiada previa y agrega el módulo documental local, las tarjetas finales y la consulta a la IA solo tras obtener resultados. No ejecutar dos sprints paralelos ni duplicar requisitos.

## 1. Objetivo e hipótesis de producto

Convertir Triple-T en un **copiloto crediticio de uso intuitivo** que guíe a un analista, incluso sin capacitación sobre la herramienta, durante una evaluación preliminar personal en PEN. Toda la captura, validación documental, cálculo y preparación de resultados debe funcionar sin Gemini. Solo cuando exista un resultado calculado y aceptado para revisión, ofrecer de modo opcional **Preguntar a la IA sobre este análisis**, con hechos financieros mínimos y verificados; la respuesta de IA no puede cambiar datos, valores ni estados, y debe poder sustituirse por una explicación determinista.

**Secuencia obligatoria:** Inicio → Condiciones → Economía del solicitante → Historial → Evidencias locales → Revisión de datos → Análisis → Resumen visual → Simulaciones/Gráficos/PDF → Preguntas opcionales a IA.

La IA no debe ser un paso obligatorio ni requisito para obtener evaluación, gráficas o informe. Una conversación iniciada con “hola” debe ofrecer opciones concretas y una siguiente acción obvia, no un manual técnico.

## 2. Política de entornos y privacidad (requisito bloqueante)

### 2.1 Distinción técnica imprescindible

“Procesamiento local” significa **procesar documentos en el servidor que ejecuta Triple-T sin mandarlos a Gemini**. Si la aplicación está en Streamlit Community Cloud, ese servidor sigue siendo remoto, NO el PC del usuario. No prometer procesamiento 100 % en el dispositivo del analista sin una implementación específica local/on-prem.

### 2.2 Entornos

- `demo`: única modalidad operativa en la web pública actual. Utiliza datos y documentos sintéticos o anonimizados con autorización de prueba, nunca expedientes de clientes identificables. Mantener aviso visible pero discreto “Entorno de demostración · No introduzcas datos personales ni documentos reales”. Redacción del resto de la UI profesional, sin repetir avisos en cada burbuja.
- `private_pilot` / `production`: **bloqueados** hasta cumplir controles y aprobaciones descritos en §12. No activar por un cambio de variable, texto ni selector desde navegador. Si se configura indebidamente un entorno no habilitado, fallar de forma cerrada.
- Gemini free-tier no recibe documentos, fotografías, texto OCR, nombres, identificadores, nombres de archivo, datos bancarios identificables, histórico completo, notas libres ni campos que permitan reidentificar. Solo una estructura mínima allowlist derivada de resultados de demostración, cuando el analista habilita voluntariamente la consulta posterior.
- El procesamiento documental local no implica autenticidad, titularidad validada ni acceso a una base de datos oficial. No anunciar una revisión patrimonial “verificada” sin una integración autorizada y un procedimiento formal.

## 3. Diseño conversacional sin comandos

### 3.1 Pantalla de inicio

Mostrar título **Triple-T**, subtítulo breve “Asistente de análisis crediticio”, una bienvenida de una a tres líneas y tres acciones claras:

1. **Iniciar evaluación** (primaria).
2. **Simular un préstamo** (secundaria, si existe monto/plazo/TEA o conduce a obtenerlos).
3. **Continuar expediente** (solo si hay uno vigente en la misma sesión).

“Revisar documentos” puede existir como acceso contextual, no un botón principal obligatorio. Evitar tablas `None`, JSON, `RN-03`, `SIN_ACLARAR`, nombres de variables y advertencias técnicas en la primera pantalla. El estado de Gemini es pequeño, fuera de las burbujas del chat.

### 3.2 Recolección progresiva, una pregunta útil por vez

- **Etapa 1: condiciones:** crédito personal/PEN habilitado, monto, plazo y TEA; si no sabe la tasa, explicar dónde encontrarla y permitir **Pendiente**, sin inventar cifra ni calcular cuota.
- **Etapa 2: ingresos/egresos:** ingreso neto mensual, gastos habituales sin cuotas, otras cuotas mensuales; preguntar si esas cuotas ya están descontadas del ingreso para evitar doble conteo. El analista puede proporcionar varios datos en un mensaje y corregirlos con confirmación.
- **Etapa 3: continuidad e historial:** meses de actividad/empleo, historial declarado/desconocido/insuficiente/mora explícita. No equiparar “sin historial” con 0 días de mora ni con historial favorable.
- **Etapa 4: respaldo documental:** solicitar **documento de ingresos**, y ofrecer adicionalmente **documento de propiedad/patrimonio** si el analista indica que existe. Explicar qué aporta cada uno. El segundo nunca sustituye capacidad de pago ni implica garantía legalmente constituida. Permitir “No dispongo”, “Solicitar al cliente” y “Agregar más tarde” manteniendo pendientes explícitos.
- **Etapa 5: revisión:** mostrar los datos registrados con su fuente y ofrecer “Confirmar / Editar / Dejar pendiente”. No validar automáticamente documentos ni aceptar duplicados de meses como prueba suficiente.
- **Etapa 6: análisis:** si existen datos mínimos, emitir cálculo y estado para revisión. Si faltan datos que afectan capacidad, mostrar solo cálculos parciales justificados (por ejemplo, cuota teórica) y próximos pasos.
- **Etapa 7: resultados:** tarjetas, gráficos y PDF; después botón opcional de preguntas a IA.

Cada mensaje guiado debe terminar con una pregunta concreta y ofrecer 2–4 opciones rápidas cuando corresponda. Responder “No sé” no equivale a 0 y “No tengo” no equivale a “No existe”. Evitar repetir preguntas respondidas. Recordar la etapa en un módulo de estado centralizado independiente de Streamlit.

### 3.3 Mensajes propuestos

- «Hola» → «Hola, soy Triple-T. Puedo guiarte en una evaluación crediticia. ¿Iniciamos una solicitud o prefieres simular condiciones?» con acciones.
- «Quiero evaluar un cliente» → «Empecemos. ¿Qué monto de financiamiento solicita?».
- «No conozco la TEA» → explicación breve, botón “Pendiente” y siguiente acción: consultar condiciones/tasa definida por la entidad. Sin inventar tasas de oferta.
- «Tengo tres boletas y una propiedad» → pedir carga de boletas **en módulo documental local**; la propiedad se registra como respaldo declarado, con solicitud de documentación y comprobaciones pendientes.
- «¿Es obligatorio subir documentos?» → explicar que, sin evidencia, el análisis mantiene limitaciones y no puede presentarse como respaldado documentalmente.
- «¿Por qué preguntas si otras cuotas están descontadas?» → explicación en lenguaje llano sobre doble conteo.
- «¿Lo apruebo?» → resumen de indicadores y pendientes; autoridad humana decide.

## 4. Documentación local: ingresos y patrimonio

### 4.1 Tipos y estado

**Ingresos:** boleta de pago, estado de cuenta, recibo por honorarios u otra fuente admitida por una política explícita. **Patrimonio:** partida/título/constancia de propiedad o documentación equivalente presentada, únicamente como respaldo patrimonial declarado; ningún documento por sí solo verifica titularidad o facultades para dar garantía.

- Reutilizar `servicios/documentos.py`: carga PDF/JPG/PNG, validación tipo y tamaño, OCR opcional y confirmación manual; no enviar archivos ni su texto a la IA.
- En la versión actual, la extracción reconocida para el cálculo de promedio es principalmente de **boletas**. Para otros documentos agregar **clasificación local y metadatos mínimos**; no inventar extractores generales ni tratar los importes de extractos bancarios como ingreso neto estable sin criterio documentado.
- Para **propiedad**, solicitar tipo de bien, documento presentado, valor *declarado o de tasación según fuente*, relación de titularidad *declarada*, fecha y observaciones de revisión. No solicitar ni almacenar DNI/nombres reales en demo. Estado mínimo `PRESENTADO_PENDIENTE_REVISION`, `TRANSCRIPCION_CONFIRMADA`, `SIN_VERIFICACION_EXTERNA`, `DESCARTADO`; el último estado sobre revisión no implica verificación de autenticidad.
- Evitar exponer identificadores de titular, número de partida, dirección completa, correos, cuentas o nombres a Gemini; en demo bloquearlos también en ingreso y guardar solo información sintética.
- Si se reciben 3–6 boletas de meses distintos, confirmar importes y excluir ingresos extraordinarios antes de promediar. Cualquier discrepancia relevante con ingreso declarado exige justificación antes de continuar con evaluación sustentada.
- Documento duplicado, ilegible, corrupto, protegido, sin fecha o no permitido: error localizado, clara solución manual y estado pendiente; nunca bloquear todo el chat ni establecer cero automáticamente.
- **No subir documentos reales a la instancia pública.** Para documentos de clientes reales la función requiere un despliegue privado y controles del §12.

### 4.2 Flujo de carga

Chat pregunta «¿Tienes documentos que respalden los ingresos?». Respuestas rápidas: `Subir boletas`, `Otro respaldo`, `No por ahora`. Si `Subir boletas` → aparece uploader en el flujo, no forzar a abrir panel experto. Luego tarjetas de cada evidencia muestran tipo, período, importe extraído/propuesto, fuente y estado; `Confirmar`, `Corregir`, `Descartar`. Al terminar ingresos, preguntar **de forma opcional** por propiedades: `Sí, hay un bien`, `No`, `Desconocido`; si sí, abrir el panel de documento patrimonial local.

Nunca mostrar como “Verificada” una transcripción confirmada por el analista. El analista solo confirmó que el dato transcrito coincide con lo que observa; puede quedar pendiente autenticidad y titularidad.

## 5. Resumen visual al obtener suficientes datos

### 5.1 Tarjetas principales (máximo cuatro)

1. **Cuota mensual estimada**: S/ __, distinguir cuota base de pago con cargos cuando aplique, y TEA.
2. **Compromiso de ingresos (DTI)**: __ %, definir de modo breve y compararlo **con umbral configurable, no oficial**.
3. **Disponible después del pago**: S/ __, solo si capacidad calculable; de lo contrario `Pendiente`.
4. **Estado de revisión**: `Información pendiente` / `Requiere aclaración` / `Listo para revisión` / `Alertas identificadas`. Nunca `Crédito aprobado` o `Riesgo bajo` sin modelo validado y decisión autorizada.

- Si una cifra falta: mostrar `—` y la causa, **nunca 0**.
- Destacar *como máximo* una alerta crítica y el siguiente paso; colores semánticos sobrios y accesibles, no aparentar scoring oficial.
- Bajo las cards, dos controles: **Ver detalle y evidencias** y **Comparar escenario**. Mostrar gráfico de saldo/amortización y reporte PDF al solicitar o tras terminar evaluación, sin cargar todo desde inicio.
- Una sección plegable “Cómo se calculó” contiene fórmula, fuente, fecha, versión de reglas, redondeo y supuestos; útil para auditores, no saturar al analista.
- Si el caso está incompleto, presentar una tarjeta `Información pendiente` con checklist y botón `Continuar`, sin crear falsa tarjeta de capacidad. Los datos parciales que sean válidos (cuota teórica) pueden mostrarse con etiqueta claramente provisional.
- Vista responsive: tarjetas 2x2 en desktop, 1 columna en móvil, sin scroll horizontal.

### 5.2 Comparación de escenarios

Card base + escenario, mostrar diferencia de cuotas, intereses y saldo disponible solo cuando calculables. Mantener base inmutable. Indicar supuestos, plazo, TEA y cambios. Gráficos de saldo y amortización basados exclusivamente en el motor Python.

## 6. La IA solo después del análisis

### 6.1 Dos etapas explícitas

**Etapa A — Evaluación autónoma (sin IA remota):** bienvenida, interpretación guiada controlada, recopilación, carga/lectura de documentos, confirmación, motor financiero, alertas, tarjetas, gráficos, PDF. Aunque Gemini esté configurado, no hay ninguna llamada remota durante esta etapa. Una pregunta explicativa antes del resultado se responde con plantillas y definiciones locales.

**Etapa B — Asistente IA opcional sobre resultados:** solo si ya existe análisis válido para el nivel disponible (puede ser parcial, etiquetado), el analista ve botón **“Preguntar a la IA sobre este análisis”**, lee aviso y da consentimiento explícito independiente. Botón también «Seguir sin IA». El modo de chat para consultas sigue etiquetado como *asistencia sobre resultados*, no como agente decisor.

**Nota de diseño:** el Sprint 4 actual manda mensajes ambiguos a Gemini durante el flujo. Codex deberá modificar el enrutamiento para respetar *sin IA hasta resultados*, sin eliminar el modo local ni debilitar validaciones. Las preguntas abiertas tempranas se resolverán determinísticamente o pedirán reformulación; no se afirmará comprensión universal.

### 6.2 Contexto para la IA

Enviar únicamente campos allowlist **no identificables** y mínimos de un *caso de demostración*: tipo de producto, monto/plazo/TEA declarados, **resultados numéricos producidos por Python**, indicadores/alertas canónicos, estados de evidencia y campos pendientes, versión de reglas, condiciones del escenario. No enviar `Expediente` serializado completo, documentos, OCR, imagen, nombre de archivo, identificador, dirección, nombre real, ingreso personal identificable o mensajes históricos. El texto de una pregunta también pasa por filtros previos al envío, con opción de sanitizar o bloquear.

El contenido del asistente no tiene acceso a herramientas para editar expediente, confirmar evidencias ni decidir/aprobar. Es un sistema de **explicación consultiva de resultados ya calculados**; no puede inventar cifras ni cambiar estados. Las preguntas tipo «¿y si cambio el plazo?» deben ejecutarse primero mediante **simulador local** y consultar después la explicación sobre las nuevas cifras, nunca pedir a Gemini que calcule cuota.

### 6.3 Contrato recomendado de explicación

No confiar en texto libre de Gemini sin validación. Preferencia: solicitar salida estructurada tipo `{intent, explanation_by_fact_ids, suggestions_from_allowlist, asks_clarification}` y ensamblar la respuesta final desde plantillas de hechos verificados. Si se ofrece texto redactado por IA, validar que *toda* mención de importes/porcentajes coincide con hechos disponibles, no aparecen hechos sin soporte, no hay aprobación o PD inventada y no se introducen fuentes inexistentes. Si la validación es insuficiente, mostrar explicación local. No afirmar que la IA “verificó” documentos.

Mostrar pregunta/respuesta en el mismo chat, con acceso discreto a “Fuentes y cálculos” y una explicación de uso de IA. No colocar logs o frases «JSON validado» como burbujas ordinarias.

### 6.4 Fallos

Sin credenciales, cuota agotada (429), modelo ausente (404), error de autenticación, esquema inválido, timeout o falta de consentimiento: permitir seguir consultando resultados de forma local sin perder expediente, escenarios, PDF ni evidencia confirmada; nunca reintentos automáticos ni exposición de claves/errors crudos. Mantener límites de uso por sesión y considerar el riesgo de abuso en acceso público; la IA debe poder quedar desactivada en la demo pública por configuración de servidor.

## 7. Panel lateral profesional

- **Inicialmente cerrado**. Al abrirse: encabezado “Expediente” con estado en lenguaje normal y progreso, acceso “Continuar paso pendiente”.
- Secciones plegadas: `Resumen del expediente`, `Documentos y evidencia`, `Simulaciones`, `Historial de cambios de la sesión`, `Herramientas avanzadas` (incluye TEA/TCEA/umbral/PD-LGD ilustrativas y 3x3 estratégico). Evitar exhibir nombres de campos de Python como `otras_cuotas` o `dias_mora`.
- Mostrar solo información relevante a etapa; no lista de campos sin valor. Estado de conexión IA fuera de conversación y sin mostrarse antes de análisis.
- Botones `Nueva evaluación` con confirmación; no “borrado asegurado de proveedor”.
- Móvil: panel tipo drawer navegable, iconos con texto y uso por teclado.
- El módulo estratégico 3 alternativas x 3 escenarios permanece íntegro, pero secundario y claramente independiente del análisis crediticio individual.

## 8. Máquina de estados y modularidad

Estados sugeridos (pueden mapearse a existentes):
`INICIO`, `CONDICIONES`, `FINANZAS`, `HISTORIAL`, `EVIDENCIA_INGRESOS`, `EVIDENCIA_PATRIMONIO`, `REVISION_DATOS`, `ANALISIS`, `RESULTADOS`, `PREGUNTAS_IA`, `ACLARACION_PENDIENTE`.

Estados del expediente distintos a pasos: `BORRADOR`, `PENDIENTE_DOCUMENTOS`, `PENDIENTE_DATOS`, `DISCREPANCIA`, `LISTO_PARA_REVISION`, `REVISION_CON_ALERTAS`, `INFORME_EMITIDO`.

Implementación sugerida sin reescribir motor:
- `experiencia/flujo.py`: transiciones puras y siguiente acción.
- `experiencia/preguntas.py`: significado, razón, preguntas y respuestas guiadas.
- `experiencia/tarjetas.py`: construir ViewModels de resultados, null-safety, fuente y unidades.
- `experiencia/ambientes.py`: `demo` público y `private_pilot/production` bloqueados hasta control real.
- `experiencia/evidencia.py`: secuencia de documentos, estados, tipo de respaldo, confirma/corrige/descarta.
- `experiencia/ayuda_ia.py`: permitir IA **solo tras resultados**, armar facts allowlist y validar respuestas.
- `ui_chat.py`: componentes, conversaciones guiadas, progreso, cards y acceso a adjuntos contextuales.
- `conversacion/gestor.py`: orquestar flujo; invariantes y confirmaciones en un solo lugar.
- `ia/politicas.py`, `ia/proveedor.py`, `ia/esquemas.py`, `ia/privacidad.py`: reutilizar y adecuar con mínimos datos después del análisis, no ampliar indiscriminadamente privilegios.
- `dominio/modelos.py`: agregar tipos/estados de evidencia o metadatos solo cuando sea imprescindible y migrar pruebas.
- `servicios/documentos.py`: extender clasificación local y metadatos patrimoniales sin afirmar verificación registral.
- `servicios/finanzas.py`, `servicios/reglas.py`, `servicios/simulacion.py`, `servicios/reporte.py`: reutilizar; cambios de fórmulas/umbrales solo por bug demostrado y con pruebas de regresión.
- `tests/`: actualizar pruebas UI que quedaron basadas en la interfaz anterior y añadir casos de seguridad/sesión.

## 9. Reglas innegociables

- RN-S5-01: la UI debe guiar, no exigir comandos ni siglas.
- RN-S5-02: cada dato tiene fuente (`DECLARADO`, `TRANSCRIPCION_CONFIRMADA`, `CALCULADO`, `SUPUESTO`, `PENDIENTE`, `VERIFICACION_EXTERNA_NO_DISPONIBLE`); nunca intercambiar semánticas.
- RN-S5-03: desconocido, ausencia de documento y dato cero son distintos.
- RN-S5-04: documentos jamás se envían al proveedor de IA ni se exponen en prompts, logs o PDFs crudos.
- RN-S5-05: pruebas públicas con documentos sintéticos solamente.
- RN-S5-06: titularidad y propiedad solo presentadas/declaradas, no verificadas en ausencia de acceso autorizado.
- RN-S5-07: patrimonio no se transforma en ingreso líquido, ni aprueba automáticamente.
- RN-S5-08: la decisión final es humana; evitar estados de “aprobado/rechazado” automáticos.
- RN-S5-09: números del motor Python son única fuente para valores derivados; una IA no calcula ni sobrescribe.
- RN-S5-10: cambios invalidan resultados, escenarios y PDF obsoletos con versión/revisión coherente.
- RN-S5-11: TEA y TCEA diferenciadas; TCEA solo cuando existen costos/fechas completos.
- RN-S5-12: no fingir política BCP, verificaciones SBS/SUNARP/RENIEC ni riesgo predictivo calibrado.
- RN-S5-13: preservar cálculos actuales, nueve escenarios estratégicos y funcionamiento totalmente sin Gemini.
- RN-S5-14: no habilitar modos producción/piloto real desde un control del navegador ni por renombrado de etiquetas.

## 10. Diseño visual y accesibilidad

- Layout central con chat; anchura legible, tipografía consistente y máxima legibilidad; no colores por decoración. 4 métricas/card, grupo 2x2 desktop y una columna móvil.
- Dar importancia a cifras, unidades, fuente y estado; una misma card muestra número y una línea de interpretación. Evitar textos largos en tarjetas.
- Evitar reportes enteros incrustados en conversación. Mostrar `Ver más` y `Cómo se calculó`.
- Botones de continuación claros, enfoque por teclado, etiquetas semánticas, contraste suficiente, comunicación no solo por color, controles utilizables 375 px.
- Gráficos solo cuando hay datos; evitar exceso de métricas irrelevantes o duplicadas. Microcopy bancario comprensible (ej.: “Cuota estimada”, no “cuota_base”).
- Mensajes de error específicos: "Falta indicar plazo", "Hay dos boletas para el mismo mes", "No puedo calcular TCEA sin los cargos"; no volcar excepciones de Python.

## 11. Entregables del Sprint 5

ÚNICO sprint, PR consolidado `feature/sprint5-flujo-documentos-cards-ia`. Codex puede dividir internamente la implementación en commits de etapas, pero debe entregar un flujo funcional vertical completo y revisable sin varios sprints separados.

Entregar: código + tests + capturas desktop/móvil + `docs/SPRINT_5.md` + matriz de aceptación cumplida/no cumplida + ejemplo de recorrido completo + lista de limitaciones y pendientes para piloto privado. No fusionar automáticamente. No introducir claves en repo. No añadir dependencias de pago.

## 12. Controles pendientes para piloto con clientes reales (fuera de este sprint)

La app pública actual no es adecuada para documentos o datos personales de clientes reales. Un piloto autorizado requiere, como mínimo: organización responsable, fundamento legal y avisos de tratamiento; infraestructura privada y control de proveedor LLM; autenticación fuerte/MFA y roles; permisos por expediente; cifrado y secret management; almacén de documentos seguro, retención, borrado, backups y auditoría; validación de archivos hostiles; políticas crediticias aprobadas y versión de reglas; modelo/riesgo validado cuando proceda; revisión humana; evaluaciones de seguridad y privacidad y aprobación formal. Un entorno on-prem/local debe realmente ejecutarse dentro de infraestructura controlada. Estas capacidades no deben simularse ni afirmarse implementadas.

---

**Criterio de éxito:** un analista que nunca usó Triple-T puede completar una evaluación guiada y obtener un resumen comprensible sin saber comandos, sin habilitar Gemini y sin cargar información real. Después puede preguntar voluntariamente por el significado de una alerta o escenario, recibiendo explicación fundada en los datos calculados.
