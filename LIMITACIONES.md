# Límites del prototipo académico

## Alcance y reglas

- Solo crédito personal en PEN está habilitado en la interfaz Sprint 2. Los perfiles
  del Sprint 1 se conservan para compatibilidad; no habilitan otros productos.
- No hay verificación de autenticidad, identidad, empleo, propiedad ni centrales de riesgo.
  Confirmar una transcripción solo registra revisión del analista.
- El DTI total usa un umbral didáctico inicial de 30% y la discrepancia de ingresos
  10% del mayor valor. Ambos son configurables, no políticas oficiales.
- Las otras cuotas deben estar todas antes o todas después del neto declarado.
  Si la situación es mixta, hay que normalizar los importes y aclararla antes de calcular.
- Boletas: 3–6 meses distintos confirmados, sin elegir automáticamente entre duplicados.
  El neto admisible debe excluir bonos/extraordinarios; no se implementan reglas para
  incorporarlos como ingreso estable. Su importe excluido se registra aparte.
- Un caso completo sin evidencia documental puede mostrar cálculos declarados con
  revisión adicional; no se presenta como promedio documental validado.

## Cronograma y TCEA

- Cronograma nuevo: Decimal con 40 dígitos, TEA fija, meses iguales, pagos vencidos,
  sin gracia ni prepago. Se redondea al presentar; sumar filas visualmente redondeadas
  puede diferir algunos céntimos. El saldo interno final es cero.
- La API de amortización del Sprint 1 mantiene su redondeo mensual para no romper
  consumidores ni pruebas; la interfaz Sprint 2 usa `servicios.finanzas.cronograma`.
- Seguros, comisiones y otros gastos son supuestos del usuario, separados en cargos
  iniciales/mensuales y por pagador. No hay tarifas bancarias precargadas.
- TCEA solo referencial: una entrada inicial neta y pagos positivos fechados;
  raíz anual ACT/365. La interfaz propone fechas mensuales con ajuste al último día
  del mes y exige confirmarlas junto con todos los costos. No implementa feriados,
  cargos variables ni certifica costo regulatorio. Si faltan datos, TCEA pendiente.
- El tope TEA configurable es técnico; no se afirma que sea límite legal.

## Lectura local y seguridad

- PDF textual: `pypdf`; vista previa con `pypdfium2`. Máximo 10 MB por archivo,
  12 archivos por caso, 20 páginas, 2 MB por stream de página expandido, 12 megapíxeles
  por imagen. La vista gráfica y OCR de PDF se limitan a las primeras tres páginas.
- OCR opcional mediante Tesseract local con idiomas `spa+eng`, entrada/salida por
  tuberías y tiempo máximo de 20 segundos por imagen. No usa APIs ni escribe las
  evidencias en archivos. Si el binario/idiomas faltan, falla o no reconoce campos,
  la interfaz solicita transcripción manual explícita.
- En el entorno de QA se verificó el fallback real sin Tesseract; no se certifica
  exactitud OCR en Community Cloud. Se puede probar/instalar Tesseract allí después
  de revisión, sin convertirlo en requisito para ejecutar la app.
- El extractor reconoce etiquetas inequívocas (`Neto estable`, `Ingreso neto`,
  `Neto a pagar`) y mes ISO; no entiende todas las boletas ni formatos numéricos.
  Un candidato siempre requiere revisión, exclusión de extraordinarios y confirmación.
- Se detectan patrones de DNI/RUC, nombres etiquetados y correo, y se bloquean cuando
  aparecen. Esto NO garantiza anonimización: nombres no etiquetados, imágenes sin OCR
  o falsos negativos pueden pasar. La confirmación de archivo sintético es obligatoria.
  No cargar expedientes reales en esta instancia pública.
- Los parsers no están aislados en procesos de seguridad. Los límites reducen el
  riesgo de recursos excesivos pero no garantizan resistencia a todos los archivos
  hostiles. Producción bancaria necesita otra arquitectura, aislamiento, auditoría,
  control de acceso, cifrado, retención y validación normativa.
- No hay persistencia de expedientes ni cache compartida. Documentos, previews y
  resultados viven en memoria de sesión. Reiniciar limpia el estado accesible en
  esa sesión; no promete borrado físico inmediato en infraestructura del proveedor.
- El contenido documental es dato no confiable: no se ejecuta, no controla reglas
  ni se envía a modelos. Los PDF de salida escapan texto y no incluyen documentos
  crudos ni texto completo extraído.

## Despliegue y aceptación pendiente

- No se ejecutó despliegue ni merge. Se comprobó Streamlit localmente y mediante
  AppTest. **CA-20 queda parcialmente pendiente:** abrir esta versión en el despliegue
  objetivo Community Cloud tras revisión y autorización del responsable.
- CA-10 se entrega por la ruta de fallback admitida en el SRS; OCR exitoso no se
  anuncia como validado en Cloud. El paquete ausente/fallido no debe simular datos.
- El módulo estratégico conserva avisos de deprecación de `use_container_width`
  para mantener compatibilidad con Streamlit mínimo 1.40; no impiden ejecutar tests.

Referencias conceptuales y técnicas (no certificación regulatoria):
[SBS: créditos](https://www.sbs.gob.pe/usuarios/aprende-con-la-sbs/aprende-sobre-creditos),
[Streamlit: cargas](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader),
[pypdf: PdfReader](https://pypdf.readthedocs.io/en/latest/modules/PdfReader.html).
# IA opcional — Sprint 4

**Actualización Sprint 5:** se sustituye la interpretación remota de captura por
explicaciones opcionales posteriores al resultado confirmado. Solo se envían hechos
permitidos y una pregunta filtrada. La salida selecciona IDs; el texto se construye
con plantillas locales. No se ejecutaron pruebas de esta entrega por instrucción del
usuario. La matriz y los recorridos pendientes están en `docs/SPRINT_5.md`.

El procesamiento documental ocurre en el servidor de la aplicación (remoto en
Streamlit Cloud), no en el dispositivo del usuario. Patrimonio y otros respaldos
no cuentan como boletas ni alimentan ingresos o capacidad. No hay autenticación ni
verificación externa de titularidad/autenticidad. `APP_ENV` distinto de `demo` se
bloquea; el control no equivale a implementar un piloto privado.

Gemini permanece desactivado sin configuración y consentimiento. Solo consultas
ficticias: los filtros no garantizan anonimización. El nivel gratuito puede usar
contenido para mejorar productos; el borrado local no elimina retención del proveedor.
La disponibilidad gratuita debe comprobarla el responsable, no se consulta su cuenta.
Un límite por sesión no protege frente a múltiples sesiones anónimas. No publicar
una demo con IA activa sin controles operativos adicionales. La interpretación real
y Community Cloud aún requieren validación autorizada; ver `docs/SPRINT_4.md`.
