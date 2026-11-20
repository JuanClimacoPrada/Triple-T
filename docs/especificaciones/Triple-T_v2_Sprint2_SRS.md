# Triple-T v2.0 — Sprint 2
## Especificación funcional, reglas de negocio, validaciones, excepciones y aceptación

**Proyecto:** Triple-T — Sistema académico de apoyo a decisiones crediticias (caso PETI BCP, brecha B01)
**Versión de especificación:** 1.0 (20-11-2026)
**Repositorio de referencia:** https://github.com/JuanClimacoPrada/Triple-T
**Aplicación:** https://triple-t.streamlit.app/
**Estado:** Requisitos para implementar. Ninguna condición representa una política oficial del BCP.

## 0. Propósito y principios

Triple-T orienta al **analista humano** al evaluar una solicitud de crédito, documentar la procedencia de los datos, identificar vacíos, calcular indicadores financieros, simular condiciones y emitir un informe explicable. No aprueba, rechaza ni fija precios crediticios automáticamente.

**Invariantes obligatorios:**
1. Nunca crear datos, certificados, historial, propiedades, probabilidades de incumplimiento (PD), valoraciones o conclusiones que no estén sustentados.
2. Diferenciar siempre **dato declarado**, **extraído de archivo, pendiente de confirmar**, **confirmado por el analista** y **verificado contra fuente autorizada**. En este sprint no existe verificación contra SBS, RENIEC, SUNARP, empleadores ni otras entidades. Confirmar una transcripción **NO verifica la autenticidad** del documento.
3. Ante falta de datos esenciales, discrepancias, documentos ilegibles o cálculo no aplicable: mostrar **PENDIENTE / NO EVALUABLE**, nunca completar silenciosamente.
4. La ausencia de historial crediticio **no es igual a mora** ni justifica rechazo automático; requiere evidencia alternativa y revisión.
5. Trabajar únicamente con datos **ficticios/anónimos**. No introducir nombres, DNI, datos financieros auténticos ni documentos reales al despliegue público. La arquitectura podrá evolucionar, pero esta instancia no es infraestructura bancaria.
6. Motor Python determinista y auditable para cualquier número financiero. Una IA conversacional futura podrá pedir datos y explicar salidas, pero no sustituir el motor ni modificar supuestos sin autorización del usuario.

## 1. Alcance, dependencias y exclusiones

**Dependencia:** integrar cambios del Sprint 1 en una rama revisada; analizar estado de `main` antes de modificar. Mantener `app.py`, `motor.py`, tests, módulo de tres alternativas × tres escenarios del trabajo N.º 16, casos de demostración y exportación CSV.

**Sprint 2 (alcance comprometido):**
- Producto **crédito personal** en PEN; campos configurables para futuras categorías sin activar reglas inexistentes de créditos vehiculares, hipotecarios y empresariales.
- Formulario editable + chat guiado para registrar datos y origen de cada campo; separación estricta de captura, validación, cálculo, presentación y exportación.
- Carga de archivos sintéticos PDF, JPG, JPEG, PNG; extracción local cuando sea posible, evidencias de procedencia y paso obligatorio de confirmación.
- Tratamiento del historial insuficiente, promedio de 3–6 meses de boletas verificadas visualmente por el analista, discrepancias y documentación patrimonial declarada.
- Simulador de monto, plazo, TEA y caída de ingresos; cuota, relación deuda/ingreso, dinero disponible, amortización y gráficos.
- Informe descargable PDF que diferencie declaraciones, confirmaciones, supuestos y limitaciones.
- Pruebas unitarias, de integración, manejo de errores, seguridad básica y manual de prueba.

**Fuera de alcance de Sprint 2:**
- Datos personales reales, verificación de DNI, consulta de centrales de riesgo, entidades de propiedad, transacciones bancarias o bases internas del BCP.
- Emisión de créditos, aprobación/rechazo automáticos, garantías legalmente constituidas, autenticación bancaria o conexión al core bancario.
- Predicción de PD por Machine Learning no entrenado o no validado; valoración automática de inmuebles; probabilidad de pérdida presentada como real.
- TCEA rotulada como definitiva si faltan cargos, fechas o flujo neto de desembolso.
- Procesamiento OCR garantizado para todos los documentos; si la lectura falla, se habilita transcripción manual explícita.

## 2. Modelo de datos mínimos

### 2.1. Solicitud de crédito personal

| Campo | Tipo / unidad | Obligatorio para cálculo | Comentario |
|---|---|---|---|
| `tipo_credito` | enum | Sí | `PERSONAL` activo en sprint 2 |
| `moneda` | enum | Sí | `PEN` en sprint 2 |
| `monto_solicitado` | decimal S/ | Sí | > 0 |
| `plazo_meses` | entero | Sí | 1–360 para simulación general; restricciones por producto configurables |
| `tea_pct` | decimal % anual | Sí | ≥ 0, tope de interfaz configurable y no confundido con límite legal |
| `ingreso_mensual_declarado` | decimal S/ | Sí para evaluación de capacidad | ≥ 0 |
| `gastos_mensuales` | decimal S/ | Sí | ≥ 0, sin duplicar deudas |
| `cuotas_otros_creditos` | decimal S/ | Sí | ≥ 0, evitar contar dos veces descuentos de boleta |
| `meses_estabilidad_ingreso` | entero | Sí para estabilidad | ≥ 0 |
| `historial_crediticio_estado` | enum | Sí | `DESCONOCIDO`, `INSUFICIENTE`, `SIN_MORA_DECLARADA`, `MORA_DECLARADA` |
| `dias_mora` | entero o null | Condicional | Nulo si no se conoce. Cero solo cuando se declara explícitamente sin mora |
| `cargos_mensuales` | desglose | Para cálculo total de pagos | Seguro/comisiones/gastos **supuestos** separados |
| `cargos_unicos` | desglose | Condicional | Costos iniciales y quién los paga |
| `fecha_evaluacion` | fecha | Sí | Mostrar fecha de simulación |

**NUNCA requerir DNI para evaluar el prototipo.** Etiquetar la fuente y el estado de evidencia de ingresos.

### 2.2. Registro de evidencia

Cada documento/valor extraído debe asociar:
- `documento_id` aleatorio de sesión, `tipo_documento`, `nombre_archivo_sanitizado`, `pagina_o_region`, `texto_fuente_breve`, `campo`, `valor_extraido`, `estado` (`PENDIENTE`, `CONFIRMADO`, `DESCARTADO`, `ILEGIBLE`), `fuente` (`DECLARADO`, `EXTRAIDO`, `CONFIRMADO_ANALISTA`), `fecha_documento`, `observacion`.
- **No almacenar el documento íntegro** ni su contenido en archivos permanentes o registros de aplicación; mantenerlo temporalmente en memoria, con aviso de limitaciones del entorno.
- Si un OCR ofrece una puntuación de confianza, mostrarla solo como calidad de extracción, **no como certeza de autenticidad**. No inventar confianza cuando la biblioteca no la proporcione.

## 3. Reglas de negocio (RN)

| ID | Regla operativa | Comportamiento obligatorio |
|---|---|---|
| RN-01 | Producto activo | Solo personal en Sprint 2. Otro producto muestra «Próximamente; no evaluable aún». No aplicar reglas de personal a hipotecario/empresarial. |
| RN-02 | Capacidad de pago | `saldo_pre_cuota = ingresos_admisibles - gastos - otras_cuotas`; `saldo_post_cuota = saldo_pre_cuota - pago_mensual_total_nuevo`. Si negativo, alerta de déficit. |
| RN-03 | Endeudamiento | `DTI_total = (otras_cuotas + pago_mensual_total_nuevo) / ingresos_admisibles`. Si ingreso cero/desconocido, mostrar `N/D`, jamás 0%. Umbral **didáctico configurable** inicial 30%; `>` activa alerta; igualdad no. |
| RN-04 | Historial insuficiente | No equiparar con mora. Emitir «historial insuficiente: se requiere evidencia complementaria y revisión humana». |
| RN-05 | Boletas de pago | Aceptar entre 3 y 6 meses **diferentes**, con importe neto admisible confirmado por analista. Media de meses válidos. Menos de 3: evidencia insuficiente, sin promedio «validado». Incluir desglose y rango. |
| RN-06 | Ingresos variables | Pagos extraordinarios, bonos, reintegros, depósitos que no son ingresos y conceptos ambiguos se separan; excluidos de ingreso estable salvo confirmación y regla explícita. No confundir neto con bruto. |
| RN-07 | Consistencia de ingresos | Comparar ingreso declarado y promedio documental. Si diferencia >10% del mayor de ambos (parámetro didáctico configurable), detener recomendación preliminar hasta aclaración. Si uno es cero y otro positivo, discrepancia. |
| RN-08 | Doble conteo | Preguntar si cuotas existentes ya están descontadas del ingreso neto; evitar duplicar descuento de planilla y `otras_cuotas`. Si es ambiguo, solicitar confirmación antes de calcular capacidad. |
| RN-09 | Patrimonio | Registrar existencia/valor **declarados**, fuente documental y verificación pendiente. Nunca convertir un título de propiedad en garantía constituida ni en liquidez mensual. |
| RN-10 | Estabilidad de ingresos | `<6` meses alerta didáctica; `6–11` revisión; `>=12` continuidad favorable solo como señal auxiliar. No sustituye evidencia de pago. |
| RN-11 | Mora | `DESCONOCIDO`: pendiente; mora 1–30: advertencia; mora >30: alerta crítica para revisión. Mora ausente no se infiere de no haber historial. Umbral didáctico, no política bancaria. |
| RN-12 | Cuota francesa | `TEM=(1+TEA/100)^(1/12)-1`; `C=M* TEM/(1-(1+TEM)^(-n))`, con TEA=0 => `M/n`. Desglosar interés, amortización, saldo e importe adicional. |
| RN-13 | Cargos/TCEA | Registrar cargos por separado según momento y quién paga. Calcular TCEA **referencial** por flujo efectivo solo si se conocen todos los flujos pertinentes; en otro caso «TCEA no calculable con los datos disponibles». No afirmar costo regulatorio definitivo. |
| RN-14 | Simulador | Monto, plazo, TEA y caída de ingresos % modificables, siempre desde una copia de los datos base. La simulación no cambia el expediente original. |
| RN-15 | Clasificación explicable | Estados: `DATOS INSUFICIENTES`, `DISCREPANCIA PENDIENTE`, `ALERTAS RELEVANTES`, `REVISIÓN ADICIONAL`, `CONDICIONES PRELIMINARES FAVORABLES`. Mostrar reglas activadas, campos, cifras y limitaciones. Nunca mostrar aprobado/rechazado. |
| RN-16 | PD/EL | PD y LGD solo como **supuestos etiquetados**. `EL = EAD × PD × LGD` únicamente para un escenario ilustrativo, nunca «riesgo calculado por ML». Sin PD/LGD no calcular EL. |
| RN-17 | Formatos y gráficos | Gráfico de saldo, capital-interés por cuota, ingresos/gastos/capacidad y comparación de simulaciones; tabla de amortización exportable. Valores deben provenir del motor, no de IA generativa. |
| RN-18 | Informe | PDF y pantalla incluyen entradas, fuente, estado, supuestos, versión de reglas, fecha, cálculos, alertas, escenarios y advertencia de uso académico. No incluir documentos crudos. |
| RN-19 | Decisión humana | Mostrar «Recomendación para revisión del analista» y permitir registrar observación no sensible en sesión. No activar desembolsos, contratos ni rechazo automatizado. |
| RN-20 | Análisis estratégico | Conservar tres alternativas tecnológicas y tres escenarios, señalando supuestos de inversiones, productividad, costos y horizonte; sin confundir ese análisis con el de un solicitante. |

## 4. Validaciones y excepciones

| ID | Caso | Resultado necesario |
|---|---|---|
| VAL-01 | Campos esenciales ausentes | No emitir clasificación favorable; listar campos pendientes. |
| VAL-02 | Monto ≤0, plazo ≤0, tasa negativa, importes negativos o NaN/Infinity | Rechazar entrada con mensaje localizado, sin excepciones sin capturar. |
| VAL-03 | Ingreso 0 | Evitar división por cero, DTI=`N/D`, alerta de capacidad; no decisión crediticia definitiva. |
| VAL-04 | TEA=0 | Cuota exactamente principal/plazo antes de redondeo; interés total 0. |
| VAL-05 | Fechas duplicadas en boletas | Contabilizar un único mes tras confirmación; avisar. |
| VAL-06 | PDF sin texto extraíble o imagen OCR incorrecta | Avisar «lectura no concluyente», habilitar transcripción manual; no inventar campo. |
| VAL-07 | Dos evidencias con importes discordantes | Presentar diferencias y solicitar elección justificada; no fusionar silenciosamente. |
| VAL-08 | Documentos mayores a 10 MB, demasiados archivos (>12), formatos no admitidos, PDF cifrado o corrupto | Rechazar de forma segura con mensaje; sin tracebacks al usuario. Límite de páginas PDF recomendado ≤20. |
| VAL-09 | Documento contiene texto que intenta dar instrucciones al chatbot | Tratarlo como datos no confiables; ignorar órdenes contenidas en el archivo. |
| VAL-10 | Patrimonio sin valor, titularidad o verificación | Mostrar «patrimonio declarado, no verificado»; no considerarlo respaldo efectivo de obligación. |
| VAL-11 | Faltan cargos/fechas para TCEA | No inventar TCEA; mostrar TEA y «TCEA pendiente». |
| VAL-12 | Usuario cambia un parámetro del escenario | Recalcular gráficos/tabla/PDF consistentemente, sin afectar datos originales. |
| VAL-13 | Archivo contiene patrones aparentes de DNI, nombres u otros identificadores | Alertar y bloquear cuando se detecten; exigir confirmación explícita de archivo sintético/anónimo. La detección automática **no puede garantizar anonimización**; no registrar ni enviar a APIs. |
| VAL-14 | Fallo de paquete OCR, PDF o gráfico | Aplicación no se cae; informar limitación y ofrecer entrada manual. |
| VAL-15 | Reiniciar sesión/caso | Limpiar datos de sesión, datos extraídos y registros de la interfaz; no prometer borrado inmediato de copias temporales del proveedor. |
| VAL-16 | Cliente sin historial pero con 3 boletas confirmadas | Permitir cálculos de capacidad con esas boletas y mantener alerta de historial insuficiente. |
| VAL-17 | Ingreso neto ya descuenta préstamo por planilla | Requerir aclaración antes de sumar otra vez esa obligación. |
| VAL-18 | Sesiones simultáneas distintas | No compartir información, cargas ni resultados entre sesiones. |

## 5. Cálculos, redondeo y trazabilidad

- Trabajar con importes en unidades monetarias de precisión estable (`Decimal` recomendado); redondear a dos decimales al **mostrar** y ajustar último pago para cerrar saldo, no redondear repetidamente los saldos internos.
- Tabla: período, saldo inicial, cuota base, interés, amortización, seguros/cargos, pago total, saldo final. La suma de amortizaciones debe igualar principal dentro de tolerancia de S/ 0.01; saldo final ≈ S/ 0.
- Para simulación de ingresos: `ingreso_escenario = ingreso_base × (1 - caída_pct/100)`; 0–100%; volver a calcular DTI y saldos, no alterar cuotas del préstamo si monto/plazo/tasa no cambian.
- Costos iniciales y recurrentes se listan por separado; solo estimar TCEA mediante tasa interna de retorno de flujos del prestatario **si datos completos y consistentes**. Los criterios exactos se revisarán según el producto y normativa aplicable.
- Mostrar el origen de cada número: «Ingresado», «Extraído y confirmado», «Calculado», «Supuesto». Incluir versión del modelo de reglas y fórmula aplicada.

## 6. Contrato de interfaz y arquitectura recomendados

Módulos sugeridos, adaptables a cambios ya hechos por Codex:
```
app.py                 # UI Streamlit; formularios, chat, tabs
motor.py               # cálculo financiero puro (mantener compatibilidad)
dominio/modelos.py     # dataclasses/tipos Solicitud, Evidencia, Escenario, Resultado
servicios/documentos.py # validación y lectura PDF/imagen con fallback manual
servicios/reglas.py    # motor de reglas y explicación trazable
servicios/simulacion.py# parámetros e invariantes de simulación
servicios/reporte.py   # PDF a partir de resultados calculados
visualizaciones.py     # gráficos de los mismos resultados
pruebas/ o tests/       # suite automatizada y fixtures ficticias
```

**Interfaz:** pasos de pantalla `1 Datos`, `2 Evidencias`, `3 Confirmar`, `4 Analizar`, `5 Simular`, `6 Reporte`; el chat asiste, pero también existen campos editables, indicadores claros y retorno a pasos anteriores. No exigir que el usuario repita ocho respuestas para corregir una sola.

**Documentos:** preferir extracción local: PDF textual mediante paquete open source y OCR en imágenes cuando exista dependencia ligera y compatible con despliegue; no invocar APIs comerciales ni descargar archivos durante la evaluación. Si OCR de JPG/PNG no funciona en la infraestructura gratuita, entregar degradación visible a transcripción manual y registrar la limitación. No anunciar «imagen analizada» cuando no ocurrió.

**Privacidad:** límites en tipos/tamaños, bytes solo temporales, no persistir evidencias; no crear logs con contenido documental; no enviar archivos a APIs externas; desactivar cualquier integración que registre datos. Rechazar expresamente expedientes reales en esta versión académica pública. Auditoría real, identidad, retención y cifrado se exigirían en otra arquitectura bancaria, fuera del prototipo.

## 7. Criterios de aceptación verificables (CA)

| ID | Entrada / acción | Resultado esperado |
|---|---|---|
| CA-01 | Seleccionar crédito personal | Se puede evaluar y simular; otros tres productos quedan claramente no habilitados. |
| CA-02 | Caso sintético de S/ 10,000, 12 meses, TEA 0% | Cuota base S/ 833.33 aproximada, interés 0 y saldo final ≈ 0. |
| CA-03 | Caso sintético 10,000, 12 meses, TEA 25% | Cuota base aproximada S/ 938.46 (confirmar en test independiente), tabla con 12 cuotas, amortización total ≈ S/ 10,000. |
| CA-04 | Ingreso 3,500, gastos 1,400, deudas 300 y nuevo préstamo 10,000/12/25% | DTI incluye cuota nueva + 300; alerta si supera 30%, aunque cuota sola no supere 30%. |
| CA-05 | Ingreso 0 | DTI `N/D` y revisión por capacidad; no error ni rechazo automático. |
| CA-06 | Tres boletas sintéticas de distintos meses con netos 3,000; 3,300; 3,600 | Tras confirmación: promedio S/ 3,300, tabla por mes y procedencia; historial insuficiente sigue etiquetado como tal. |
| CA-07 | Boletas con netos 3,000; 3,300; 3,600 e ingreso declarado 4,500 | Se muestra discrepancia (>10% relativo), no recomendación favorable hasta aclaración. |
| CA-08 | Solo dos meses de boletas | Aviso evidencia insuficiente; se muestran datos, sin inventar promedio confirmatorio. |
| CA-09 | Un PDF textual de demostración que contiene monto neto | Se presenta valor, página/frase de origen y botón confirmar/descartar; no se importa sin intervención. |
| CA-10 | PDF escaneado o JPG/PNG sintético | Se intenta OCR local si está disponible; si no, fallback explícito manual; jamás dato inventado. |
| CA-11 | PDF cifrado/corrupto y archivo mayor a límite | Error comprensible, sistema continúa, sin fugas de contenido ni traceback. |
| CA-12 | Cliente sin historial y con documento patrimonial simulado | Se muestra patrimonio como no verificado, sin convertirlo en garantía, y se solicita revisión. |
| CA-13 | Modificar plazo de 12 a 24 meses sin cambiar otros datos | Disminuye cuota base si TEA positiva; se recalculan interés total, tabla y visualizaciones; no se altera solicitud original. |
| CA-14 | Simular caída de ingresos 20% | Ingreso escenario=0.8×ingreso base; recalcular DTI y saldo; no se altera expediente original. |
| CA-15 | Añadir seguros/cargos conocidos | Mostrarlos separados, pago mensual total correcto; TCEA referencial solo si flujos están completos. |
| CA-16 | Descargar PDF | Contiene parámetros, etiquetas fuente/estado, cálculos, escenarios, alertas, fecha y aviso académico; cifras coinciden con pantalla. |
| CA-17 | Comparar alternativas estratégicas | Siempre aparecen 3 alternativas × 3 escenarios con hipótesis explícitas y sin «ML entrenado» falso. |
| CA-18 | Reiniciar evaluación | No quedan datos del caso anterior visibles o reutilizables en sesión nueva; dos sesiones diferentes no se cruzan. |
| CA-19 | Texto malicioso incrustado en documento | No se ejecuta como instrucción ni cambia umbrales o genera afirmaciones bancarias. |
| CA-20 | Ejecutar pruebas automatizadas y abrir Streamlit | Todas las pruebas pasan, sin regresión del motor de Sprint 1, y pantalla carga en despliegue objetivo. |

## 8. Definición de terminado (Definition of Done)

Sprint 2 se considerará completo **solo si**:
- Todos los CA-01…CA-20 se comprueban o se documenta formalmente un CA limitado por infraestructura y se corrige antes de declarar esa función como implementada.
- Se ejecuta la batería de pruebas unitarias e integración, incluyendo PDF y una imagen sintética; sin regresiones de `tests/test_motor.py`.
- Los cálculos, alertas y PDF son reproducibles para la misma entrada; existe al menos un caso de verificación manual de amortización.
- Existe documentación actualizada en `README.md` y un registro `LIMITACIONES.md` con seguridad, privacidad, alcance, umbrales académicos y alternativas técnicas.
- Las funcionalidades del Sprint 1 permanecen, las alertas nunca son «aprobado»/«rechazado», el programa no usa datos reales ni credenciales.
- Se presenta pull request a una rama distinta de `main`, con resumen, pruebas ejecutadas, capturas y instrucciones de despliegue; no desplegar ni fusionar sin revisión del responsable.

## 9. Matriz de trazabilidad para la ficha académica

| Apartado de la Ficha N.° 16 | Evidencia del software |
|---|---|
| Paso 1: problema B01 | Introducción/motivo del proyecto y advertencia académica |
| Paso 2: variables | Formulario + definición de datos, evidencia y resultados |
| Paso 3: tres alternativas y escenarios | Módulo estratégico 3×3 + simulador de condiciones individuales diferenciado |
| Paso 4: lógica predictiva | Reglas y cálculos transparentes, **simulación**, no PD inventada |
| Paso 5: construcción | Enlace de Streamlit + repositorio GitHub + pruebas |
| Paso 6: sustentación | Tres casos sintéticos, documentos simulados, gráfico, PDF e interpretación |

## 10. Verificaciones normativas y fuentes de orientación (no reemplazan asesoría profesional)

- SBS, *Aprende sobre créditos*: distingue TEA de TCEA; esta última incorpora interés, comisiones y gastos: https://www.sbs.gob.pe/usuarios/aprende-con-la-sbs/aprende-sobre-creditos
- SBS, *Marco normativo* (incluye Reglamento para la Evaluación y Clasificación del Deudor, Res. SBS 11356-2008, sujeto a normas modificatorias): https://www.sbs.gob.pe/autorizacion-de-nuevas-empresas/marco-normativo-y-documentos-de-apoyo
- ANPD, *Nuevo Reglamento de la LPDP*, DS 016-2024-JUS, vigente desde 31-03-2025: https://www.gob.pe/institucion/anpd/campa%C3%B1as/128319-nuevo-reglamento-de-proteccion-de-datos-personales
- Streamlit, documentación `st.file_uploader` y manejo de sesiones: https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader

## 11. Instrucción de ejecución para Codex

1. Leer esta especificación, inspeccionar el último código de GitHub y verificar si existe PR pendiente del Sprint 1. **No sobrescribir trabajo nuevo**.
2. Presentar un breve plan de módulos y riesgos y marcar dependencias con Sprint 1.
3. Implementar RN, VAL y CA incrementalmente, priorizando **cálculos correctos y trazabilidad** sobre efectos visuales.
4. Crear únicamente documentos ficticios de prueba. La extracción debe ser local y sin servicios pagos.
5. Si una función no resulta viable en Streamlit Community Cloud, no fingir su funcionamiento: implementar fallback manual y describir la limitación.
6. Correr tests; adjuntar evidencia; preparar PR; no fusionar ni desplegar sin autorización.
