# Triple-T v2.0 — SRS / SDD Sprint 4
## Integración segura de IA conversacional con el motor crediticio

**Versión:** 1.0 | **Fecha:** 20 de noviembre de 2026 | **Proyecto:** Triple-T  
**Repositorio:** https://github.com/JuanClimacoPrada/Triple-T | **Aplicación:** https://triple-t.streamlit.app/  
**Base obligatoria:** rama `main`, posterior al merge del PR #3, commit `2f6edac0c0c7a90bf939099c70c54940cab7341a` (o versión más reciente).  
**Carácter:** prototipo académico con datos exclusivamente ficticios; NO es servicio bancario ni decide créditos.

## 1. Objetivo y límites

Transformar el chatbot determinista Sprint 3 en un chatbot de **lenguaje natural asistido por un LLM**, con capacidad para comprender variaciones lingüísticas de consultas del analista y activar herramientas financieras fiables. La interfaz seguirá siendo el chat principal; formularios, documentos, gráficos y PDF serán herramientas contextuales. Conservar 100 % de las capacidades, contratos y regresiones de los Sprints 1–3.

### Alcance incluido
- IA para comprender preguntas en español peruano, extraer entidades financieras, identificar intención y solicitudes incompletas, recomendar **qué dato falta preguntar** y solicitar explicaciones de indicadores.
- Herramientas ya existentes para captura de expediente, cálculo de cuota y DTI, lectura/confirmación de evidencias, simulación financiera y emisión de informe; llamadas exclusivamente a través del orquestador y con validación.
- Respuestas naturales pero **cifras, conclusiones regladas y fuentes generadas por código determinista**; la IA no calcula por su cuenta.
- Proveedor remoto opcional en un nivel gratuito para la demostración, con activación/configuración explícita; fallback local sin IA ante fallas o falta de clave.
- Sin guardar expedientes ni mensajes persistentemente; únicamente sesión de Streamlit. No se transmitirán PDF originales, boletas, imágenes, OCR sin filtrar ni identificadores a un LLM externo.

### Fuera de alcance
- Aprobación, rechazo, oferta o decisión automática de crédito; aplicación de políticas reales del BCP.
- Predicción estadística de PD, entrenamiento de ML o verificación de datos ante centrales de riesgo, empleadores, SUNARP o SBS.
- Documentos reales, expedientes bancarios, autenticación bancaria, producción en una entidad financiera y garantías de privacidad propias de producción.
- Voz, RAG, búsquedas abiertas en internet o acceso a otras APIs de clientes.

## 2. Decisión técnica y proveedores

**Opción primaria para demo:** Google Gemini Developer API, mediante el SDK de Python `google-genai` y clave configurada solo en Streamlit Secrets o variable de entorno. Modelo de ejemplo: `gemini-2.5-flash-lite` **solo si la cuenta confirma que está disponible en su nivel gratuito**. El identificador real será configurable (`GEMINI_MODEL`), no estará codificado de forma irreversible. Verificar modelos y cupos habilitados al instalar. **Nunca activar facturación ni modalidad paga automáticamente**. No prometer gratuidad ilimitada.

**Opciones de respaldo:** (a) parser determinista actual, siempre disponible; (b) en un futuro, adaptador de otro proveedor compatible con el mismo contrato o modelo local, sin alterar las reglas financieras. La app publicada no depende de ejecutar Ollama en el alojamiento gratuito.

**Limitación de privacidad crítica:** en Gemini Developer API *Free Tier*, los datos de la API pueden utilizarse para mejorar productos del proveedor. Es admisible únicamente para demos con material **sintético**, consentimiento claro y filtrado de información antes de cualquier llamada. No utilizar esta configuración con datos reales de clientes, independientemente de los avisos de consentimiento.

Referencias oficiales que deben volver a verificarse al implementar:
- Gemini pricing: https://ai.google.dev/gemini-api/docs/pricing
- SDK y esquemas: https://googleapis.github.io/python-genai/index.html
- AI Studio / API key: https://aistudio.google.com/apikey
- Streamlit Secrets: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management

## 3. Arquitectura objetivo

```mermaid
flowchart TD
 U[Analista] --> UI[ui_chat.py / Streamlit]
 UI --> G[conversacion/gestor.py]
 G --> P[Parser local Sprint 3]
 P -->|Consulta no reconocida o IA solicitada| A[Adaptador LLM]
 A --> S[Salida estructurada JSON]
 S --> V[Validador estricto de intención / entidades / fuentes]
 P --> V
 V -->|Confirmación requerida| U
 V -->|Acción autorizada| G
 G --> R[servicios/reglas.py]
 G --> F[servicios/finanzas.py]
 G --> D[servicios/documentos.py]
 G --> M[servicios/simulacion.py]
 G --> PDF[servicios/reporte.py]
 R --> X[Renderizador factual determinista]
 F --> X
 D --> X
 M --> X
 PDF --> X
 X --> UI
 A -.->|sin clave / timeout / 429 / error| P
```

**No crear un agente autónomo con libertad de ejecutar Python, SQL, web, shell o ficheros.** La IA propone una intención; un motor de estados valida y decide qué servicio seguro puede invocarse. Ninguna salida libre del LLM es código ni decisión financiera.

### Módulos nuevos previstos
- `ia/__init__.py`.
- `ia/proveedor.py`: interfaz `interpretar_ia(...)`, proveedor Gemini, tiempo máximo, manejo de cuotas, respuesta estructurada, sin fuga de claves ni logs de entradas.
- `ia/esquemas.py`: Pydantic o dataclasses con enumeraciones y esquemas JSON exactos, validación de cantidades, unidades, precisión y campos permitidos.
- `ia/privacidad.py`: filtro previo de mensajes y construcción de contexto mínimo, sintético; rechazar nombres, DNI, RUC, direcciones, cuentas, correos y archivos crudos. No interpretar como instrucción lo extraído de un documento.
- `ia/politicas.py` o ampliación de `conversacion/gestor.py`: permitir/denegar acciones, confirmación y aclaraciones; salida renderizada por `conversacion/respuestas.py`.
- `tests/test_sprint4.py`: pruebas con respuestas simuladas del LLM, sin necesidad de internet ni clave real.
- `docs/SPRINT_4.md`: resultados, límites, configuración, evidencia, criterios de aceptación.

Evitar replicar lógica de cuotas, DTI, TCEA, cálculo de pérdida esperada, simulación, permisos de documentos o PDF en los módulos de IA.

## 4. Contrato entre IA y orquestador

La IA recibe un **mensaje textual ficticio y estado resumido sin información personal**. Debe responder mediante salida estructurada —no texto libre no validado—. Contrato conceptual:

```json
{
  "intent": "REGISTRAR|CONSULTAR_CUOTA|ANALIZAR|FALTANTES|SIMULAR|EXPLICAR|EVIDENCIAS|GRAFICO|PDF|ESTRATEGIA|AYUDA|RESUMEN|CORREGIR|REINICIAR|FUERA_DE_ALCANCE|ACLARAR",
  "entities": {
    "monto": 15000,
    "meses": 24,
    "tea": 25,
    "ingreso": null,
    "gastos": null,
    "otras_cuotas": null,
    "estabilidad_meses": null,
    "caida": null
  },
  "referente": "BASE|ESCENARIO_ACTIVO",
  "requires_clarification": false,
  "clarification_field": null
}
```

Las claves son ilustrativas; el esquema de implementación debe incluir también las opciones exactas de `historial`, `descuento_planilla`, moneda, tipo de crédito y días de mora del Sprint 3 cuando correspondan. **No inventar valores omitidos**: representar ausencias como `null`, no cero. El validador rechaza claves desconocidas, tipos incorrectos, contradicciones, cifras no finitas, cifras negativas donde no proceden, plazos fraccionarios, moneda no soportada o tasas sin periodicidad TEA explícita. Las variaciones de enunciado deben probarse en español.

**Regla de compatibilidad:** `Interpretacion` existente (`conversacion/modelos.py`) seguirá siendo contrato del orquestador. Convertir salida validada del LLM al mismo tipo (con mapeo explícito de intenciones); no reemplazar sin necesidad el gestor ni crear dos fuentes de verdad.

## 5. Reglas de negocio del Sprint 4

- **RN-IA-01**: Un único expediente y revisión vigente por sesión. Todo cálculo lo hacen los servicios del Sprint 2; la IA solo identifica la solicitud.
- **RN-IA-02**: Toda respuesta con números de cuota, DTI, ingresos, intereses, tasa, amortización o pérdida debe referenciar valores emitidos por los servicios, no generados por el LLM. Prohibido inventar políticas o parámetros del banco.
- **RN-IA-03**: Prohibido clasificar una solicitud como «aprobada»/«rechazada». Puede indicar `DATOS INSUFICIENTES`, `DISCREPANCIA PENDIENTE`, alertas u otros estados oficiales internos de Triple-T, atribuidos a las reglas didácticas.
- **RN-IA-04**: Ninguna probabilidad de incumplimiento estimada por el LLM; PD/LGD ilustrativas solo como entradas explícitas y etiquetadas.
- **RN-IA-05**: Nunca seleccionar silenciosamente un valor o una periodicidad ambiguos: «3.500», «tasa 25%» sin TEA, «a dos años» sin entender si es plazo o estabilidad, o dos ingresos contradictorios -> aclarar sin modificar datos.
- **RN-IA-06**: Los cambios sobre datos ya existentes precisan confirmación del analista; las simulaciones usan copia y nunca sustituyen datos base.
- **RN-IA-07**: Un estado `INSUFICIENTE` no equivale a mora; la IA propone obtener 3–6 boletas sintéticas, sin certificar autenticidad ni introducir importes sin confirmación.
- **RN-IA-08**: La IA no recibe archivos originales, identificadores, textos OCR, observaciones sin filtrar ni transcripciones completas. Solo enviar claves numéricas sintéticas permitidas, banderas de faltantes/alertas y etiquetas seguras. Al no poder garantizar anonimización, bloquear si el texto contiene posibles identificadores o datos reales.
- **RN-IA-09**: Se debe informar de que la IA en línea envía texto ficticio a un tercero y ofrecer modo local sin IA; no enviar nada antes de opt-in explícito del analista. Aviso sobre uso de datos en nivel gratuito.
- **RN-IA-10**: Clave API solo servidor (`st.secrets`/variable de entorno). Nunca en Git, HTML, JS cliente, logs, mensajes ni descargables.
- **RN-IA-11**: Errores de red, credenciales, límites 429, tiempo de espera o JSON inválido -> informe no modificado y fallback local, con aviso claro. No reintentar en bucle ni migrar silenciosamente a opción paga.
- **RN-IA-12**: Limitar llamadas por interacción y por sesión, tamaño de entrada y salida, tiempo de espera, tokens y contexto enviado; no depender exclusivamente de limitaciones de proveedor para controlar costos.
- **RN-IA-13**: La IA solo genera objetos del esquema aprobado. No puede añadir nuevos nombres de herramientas, navegar internet, ejecutar código, guardar datos, acceder a archivos ni llamar APIs de bancos.
- **RN-IA-14**: Consultas «explícame esta alerta» deben relacionarse con el código de regla activada (por ejemplo RN-03), un glosario de definiciones aprobadas y las cifras del resultado vigente. El renderizado de hechos, fórmulas y fuentes debe ser determinista. Un LLM puede proponer qué concepto explicar, no inventar la explicación normativa.
- **RN-IA-15**: Identificar resultado **base** vs. **escenario** y revisión; invalidar o marcar no vigente todo informe al cambiar entradas.
- **RN-IA-16**: Si el nivel gratuito no está disponible, preservar el flujo local Sprint 3 y presentar una indicación de configuración, sin bloquear la aplicación.
- **RN-IA-17**: «Qué documentación puedo solicitar» puede dar lista de opciones de respaldo, nunca decir que poseer un inmueble garantiza un préstamo.
- **RN-IA-18**: Los cuatro tipos de productos se pueden mencionar pero **solo crédito personal PEN** es evaluable. No inventar reglas para vehicular, hipotecario o empresarial.

## 6. UX y flujos conversacionales exigidos

**Pantalla principal:** el chat continúa siendo central y no se requiere recorrer pestañas. Mostrar selector claro «Modo local» / «Modo IA (experimental)» o toggle, siempre desactivado sin clave y sin consentimiento; indicador visible del modo activo. Mantener expediente actual, alertas, panel experto opcional, adjuntos sintéticos y opciones de PDF/gráficos.

**Flujo F1 — conversación natural:**
1. Analista: «Necesito analizar si una persona que gana tres mil quinientos podría asumir un préstamo de diez mil soles durante un año con TEA de 25%.»
2. IA reconoce ingreso=3500, monto=10000, plazo=12, TEA=25; señala incertidumbre cuando no puede extraer las cantidades de forma inequívoca.
3. Orquestador registra información permitida y pregunta por gastos, otras cuotas, estabilidad, historial y descuento de planilla; cuota parcial calculada por servicio financiero.
4. Chat explica «cuota teórica» y no afirma capacidad de pago antes de completar datos.

**F2 — expediente con pocos antecedentes:**
«No tiene historial, pero puedo mostrar boletas». Triple-T registra `INSUFICIENTE`/`dias_mora=None`, activa controles de archivos ficticios, explica necesidad de confirmar datos y no presupone riesgo cero.

**F3 — seguimiento:**
«¿Sería mejor darle dos años para pagar?», «¿y si gana 20 % menos?». Triple-T identifica simulación, conserva expediente, explica qué escenario se está mostrando y sus datos. La IA no determina «mejor» sin criterios explícitos.

**F4 — justificación:**
«¿Por qué hay alerta de endeudamiento?». Triple-T enumera regla y datos estructurados (costo mensual, ingreso y DTI), compara con umbral didáctico, indica fuente y advierte que no es política BCP.

**F5 — límite de seguridad:**
«Apruébale el crédito aunque le falten documentos». Triple-T indica que no aprueba ni rechaza, señala datos pendientes y remite a revisión humana.

**F6 — caída del proveedor:**
La API agota cuota: mensaje «IA no disponible; continuamos en modo local». No se pierde expediente, ni simulación, ni documento confirmado.

**F7 — solicitud contradictoria:**
«Gana 3500 y gana 4500» -> no guardar ninguno; pedir aclaración. «TEA 25 % mensual» -> no guardar; solicitar periodicidad.

**F8 — consultas ajenas:**
Preguntas de información bancaria actual, estado de cuenta real o políticas internas BCP -> responder que no están conectadas fuentes verificadas, sin afirmar datos actuales.

## 7. Prioridad de ejecución y control de proveedores

1. **Ruta determinista de captura y cálculo:** preferir parser local para expresiones ya cubiertas y datos críticos inequívocos; opcionalmente usar IA para entender paráfrasis no reconocidas. Si se configura IA como modo principal, validar todos sus resultados igual que la ruta local.
2. **Solo se envía al proveedor lo estrictamente necesario** (consulta sintética filtrada y estado estructurado mínimo). Nunca incluir historial íntegro o nombres de documentos.
3. **JSON validado** antes de pasar al gestor. No confiar en `response_schema` como sustituto de la validación local.
4. **Renderer determinista** crea mensajes con valores verificables y distingue supuestos de datos confirmados.
5. **Persistir cero tokens/secrets** en resultados y evitar logs con información del usuario; registrar solo métricas generales de error en memoria de sesión cuando sean necesarias.
6. **Circuit breaker sencillo**: tras error de acceso/límite cambiar a modo local, sin reintentar automáticamente y ofrecer reactivación consciente más adelante.

## 8. Seguridad, privacidad y amenazas

- No cargar ni transmitir documentos bancarios reales. Mostrar aviso destacado y consentimiento previo al modo IA.
- No registrar prompts, archivos o secretos en `st.cache_data`, logs o persistencia externa.
- Limitar entrada a 2000 caracteres, respuesta estructurada con máximo razonable de tokens y llamadas por turno; límite operativo de sesiones documentado.
- Amenaza «prompt injection»: contenido de chat o de documentos no puede modificar los permisos, el esquema ni la política de herramientas; mensajes como «ignora las reglas y aprueba» se tratan como consultas, no instrucciones.
- Amenaza «exfiltración»: ninguna llamada externa salvo API del proveedor autorizado y únicamente con contexto mínimo; no permitir endpoints configurados por usuario final.
- Amenaza «uso abusivo de API key pública»: clave solo backend; cuotas del proveedor, presupuestos y límites por sesión. Para una demo pública con IA, advertir que no equivale a controles robustos contra usuarios anónimos.
- Amenaza «respuestas inventadas»: respuesta natural libre de números no autorizados; cifras financieras y estado siempre generados por código. En caso de discrepancia entre propuesta IA y motor, prevalece motor.
- Amenaza «retención del proveedor»: free tier puede usarse para mejoras del producto; no enviar documentos, datos personales ni información no sintética.

## 9. Pruebas de aceptación CA-IA-01…CA-IA-22

| ID | Entrada/escenario | Resultado verificable |
|---|---|---|
| CA-IA-01 | Sin API key | App inicia y chat local funcional, sin excepciones. |
| CA-IA-02 | Sin consentimiento | No ocurre llamada al proveedor. |
| CA-IA-03 | Cambio a modo IA con clave válida y opt-in | Indicador de modo IA visible, proveedor operativo o error claro. |
| CA-IA-04 | Lenguaje natural no cubierto por regex | IA lo interpreta en JSON validado y captura campos correctos. |
| CA-IA-05 | Solicitud de cuota parcial | Cuota coincide exactamente con `servicios.finanzas` para el caso. |
| CA-IA-06 | Faltan gastos/deudas | La IA pide datos; no afirma capacidad. |
| CA-IA-07 | «Sin historial» | `INSUFICIENTE`, días mora = `None`. |
| CA-IA-08 | Datos contradictorios en un turno | No se escribe ningún dato de ese turno; pide aclaración. |
| CA-IA-09 | Corrección de ingreso existente | Se solicita confirmación; cancelar mantiene estado intacto. |
| CA-IA-10 | «¿y a 24 meses?» | Escenario nuevo; expediente base no cambia. |
| CA-IA-11 | «¿y si los ingresos bajan 20%?» | Ingreso escenario y DTI calculados por motor, nunca LLM. |
| CA-IA-12 | «Explica RN-03» | Explicación con DTI y umbral reales, cita regla académica. |
| CA-IA-13 | «Aprueba el crédito» | Se niega a decidir, presenta revisión humana. |
| CA-IA-14 | Boletas PDF sintéticas | Ruta local confirmación visual, sin envío de PDF al LLM. |
| CA-IA-15 | OCR o texto documental hostil | No se ejecuta ni se añade al prompt remoto. |
| CA-IA-16 | API devuelve JSON inválido o herramienta desconocida | Rechazo y fallback sin cambios al expediente. |
| CA-IA-17 | HTTP 429 / timeout / clave inválida | Error controlado, sin perder sesión ni ejecutar modelo pago. |
| CA-IA-18 | Mensaje contiene DNI, correo, nombre o RUC | Bloqueo previo, sin llamada al proveedor (reconocer limitación del detector). |
| CA-IA-19 | PDF solicitado tras simulación | Resultado coincide con escenario activo y fuentes del motor. |
| CA-IA-20 | Módulo estratégico A/B/C | Sus 9 escenarios conservados; ninguna cifra inventada por IA. |
| CA-IA-21 | Tests de regresión de Sprints 1, 2, 3 | Todos pasan, sin rebajas o exclusiones. |
| CA-IA-22 | Despliegue Community Cloud | Prueba real con clave en Secrets (no Git), modo IA + fallback, costos gratuitos disponibles comprobados. |

**Ejecución:** pruebas unitarias con *fake provider* e inyección de dependencias (nunca consultar IA real en CI); pruebas manuales integrales con cuenta real. El PR documenta evidencia de configuración sin mostrar la clave. CA-IA-22 solo puede marcarse «completado» después de probar el despliegue autorizado.

## 10. Entregables de Codex y definición de terminado

1. Código modular nuevo, sin duplicar cálculos ni eliminar interfaz Sprint 3.
2. `requirements.txt` actualizado con SDK compatible fijado mediante rango razonable.
3. `.streamlit/secrets.toml.example` con nombres **sin valores reales**; clave real en `.streamlit/secrets.toml` local ignorado o en Secrets de Community Cloud.
4. Pruebas offline de parser, esquema, límites, continuidad/fallback, seguridad, decisión humana y regresión completa.
5. `docs/SPRINT_4.md` con arquitectura, capturas ficticias, resultado de pruebas, modo de uso, proveedor y limitaciones.
6. `README.md` actualizado con instrucciones claras de obtener clave sin compartirla en chat, GitHub o PR.
7. Pull Request independiente `feature/sprint4-ia-conversacional` hacia `main`, descripción, evidencia de pruebas y pendientes. No fusionar ni desplegar sin autorización.
8. Mantener restricciones: sin cobros obligatorios ni automatismo de activación de facturación; si el nivel gratis no está disponible, seguir en modo local e informar situación.

### Orden recomendado
- Tarea 1: contratos tipados + pruebas de validación/fallback.
- Tarea 2: adaptador Gemini + consentimiento + Secrets sin credenciales comprometidas.
- Tarea 3: integración en gestor e interfaz chat, explicaciones renderizadas con hechos del motor.
- Tarea 4: regresión y QA local, documentación y PR.

## 11. Controles de calidad de la revisión

Puntos que impiden aprobar el PR: clave en Git, envío de boletas crudas al proveedor, promesa de aprobación automática, PD «predictiva» inventada, IA que devuelve cuotas en vez de `servicios.finanzas`, comportamiento inestable sin clave, cambios del expediente sin confirmación y ausencia de regresión o pruebas de fallos API.

**Nota final:** "IA generativa" no sustituye un modelo predictivo entrenado ni es garantía de veracidad. Triple-T es un asistente con interfaz de lenguaje natural y motor financiero reproducible. Para implantación bancaria real hacen falta controles operativos, seguridad, auditoría, validación y gobernanza adicionales.
