# Evaluación del riesgo crediticio: demostración

## Alcance y procedencia

Triple-T no tiene un modelo de PD entrenado ni calibrado. La probabilidad de no
incumplimiento presentada es exclusivamente el complemento aritmético de una
PD supuesta introducida por el analista. Nunca se deduce del DTI, score, patrimonio
o capacidad financiera. No representa probabilidades reales de un cliente.

Los escenarios Optimista, Esperado y Pesimista comienzan vacíos. Cada uno admite
PD y LGD en porcentaje de 0 a 100, exposición en soles no negativa y horizonte
explícito de 1 a 1200 meses (límite técnico, no política crediticia). No es posible
guardar una PD sin horizonte. La fuente es fija: supuesto manual del analista para
demostración; no se puede cambiar su etiqueta a modelo validado.

- No incumplimiento hipotético (%) = 100 − PD (%).
- Pérdida esperada ilustrativa (S/) = exposición × PD/100 × LGD/100.
- Ausencia de PD: «No disponible», distinta de una PD explícita de cero.
- La pérdida exige los tres parámetros, incluso si una PD explícita es cero.
- No se anualizan probabilidades ni se descuenta la pérdida. Los horizontes
  diferentes muestran una advertencia, al igual que un orden incoherente de PD.

Los supuestos y el score simulado viven solo en la sesión y se limpian al cambiar
la revisión del expediente o reiniciarlo. No se incorporan al motor, al PDF
financiero ni a los hechos enviados a Gemini. Las tres alternativas estratégicas
y sus nueve escenarios permanecen independientes y disponibles.

## Sentinel y score

`SENTINEL_URL` usa `https://www.misentinel.com.pe/home` como valor de referencia
cuando no está configurada o está vacía. La variable de entorno prevalece sobre
Secrets. Una URL explícita inválida deshabilita el enlace. Se admite HTTPS sin
credenciales, consulta, fragmento ni direcciones IP. El enlace no añade parámetros
del expediente, abre otra pestaña y usa `noopener noreferrer` y `no-referrer`.

El score verificado permanece «No disponible». Se puede registrar por separado
un score de demostración con confirmación explícita, fecha no futura, escala
ilustrativa elegida (cero al máximo indicado) y fuente fija «Registro manual de
demostración; no consultado en Sentinel». No hay transformación de score a PD.
No se guardan nombres, identificadores, documentos ni fuentes de texto libre.

`ProveedorScore` define el contrato futuro de una consulta verificable.
`SentinelNoIntegrado` falla explícitamente: no hace red, scraping ni utiliza
endpoints o credenciales supuestos. Una implementación empresarial necesitará
contrato y API documentada, autorización de acceso, consentimiento/base legal,
controles de acceso, trazabilidad y tratamiento de datos fuera de la instancia demo.

## Modelos futuros

`ProveedorPD`, `EstimacionModelo` y `EvidenciaValidacion` son contratos separados
de `EscenarioHipotetico`. No están conectados a la interfaz pública ni habilitan
resultados validados por marcar una casilla. `ModeloNoDisponible` falla cerrado.

Antes de implementar un proveedor real se deberá definir incumplimiento y
horizonte, documentar autorización y representatividad de datos históricos,
prevenir fuga de información, separar entrenamiento y evaluación temporal fuera
de muestra, evaluar discriminación y calibración, documentar sesgos/estabilidad
y obtener revisión independiente. El contrato requiere referencias a esas
evidencias, versión del modelo y aprobación; la existencia del contrato por sí
sola no acredita validación. Métricas y criterios de aceptación deben definirse
con los responsables antes de habilitarlo. Se necesitarán monitoreo y control de
versiones; no hay entrenamiento ni umbrales de desempeño inventados en esta entrega.

## Privacidad y validación

Gemini recibe únicamente un tema de lista cerrada y los hechos numéricos/canónicos
permitidos por `hechos()`. No recibe el texto libre de la pregunta, notas, OCR,
nombres de archivos, score simulado ni supuestos probabilísticos. Se mantienen el
consentimiento, la confirmación del análisis, los límites de llamadas y el modo local.

La suite incluye cálculos extremos, valores no finitos, horizonte obligatorio,
fuentes fijas, fecha/escala/confirmación de score, proveedor deshabilitado, enlace
sin datos y aislamiento del contenido enviado a un proveedor simulado. Las pruebas
de Streamlit ejercitan edición, confirmación, reinicio, simulación, PDF y registro
de riesgos. No utilizan Gemini real, claves ni datos personales.

Resultado: **87 pruebas satisfactorias**, sin omisiones, ejecutando
`.venv/Scripts/python.exe -m unittest discover -s tests -v`.
Se actualizaron las expectativas antiguas del flujo guiado (confirmación previa,
avisos y tabla estratégica) sin retirar sus comprobaciones funcionales.

La referencia oficial del portal fue accesible mediante consulta web. Los atributos
de navegación se verifican automáticamente sobre el HTML del enlace. La comprobación
interactiva del clic quedó bloqueada por el navegador integrado (error de pertenencia
de pestaña a la sesión); no se afirma una validación visual completa del navegador.
