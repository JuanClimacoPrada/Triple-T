# Sprint 5 unificado — flujo, documentos, tarjetas e IA posterior

Base revisada: `origin/main`, `c9c4e142bcf88ead260c653fd1ae0127906b2a86`.
Rama: `feature/sprint5-flujo-documentos-cards-ia`. Fecha: 21/11/2026.
Fuente de alcance: [SRS unificado](especificaciones/sprint5/02_SRS_SPRINT5_UNIFICADO.md),
precedido por la lectura de [Mensaje para Codex](especificaciones/sprint5/03_MENSAJE_PARA_CODEX.md).

## Estado de entrega y validación

Implementación para revisión, **sin pruebas ejecutadas** por petición expresa del
usuario («no hagas las pruebas»). Esta instrucción prevalece sobre las solicitudes
de ejecutar/adaptar tests y capturas de aceptación de los documentos. No se añadieron
tests, no se modificaron los existentes, no se ejecutó la aplicación para QA, no se
obtuvieron capturas desktop/móvil y no se realizaron llamadas reales ni simuladas
a Gemini. Solo lectura de código, revisión de diferencias y control de whitespace.

Resultado de `python -m unittest discover -s tests -v`: **NO EJECUTADO**. Los 77 tests
que pasaron en una entrega anterior no acreditan este Sprint. Las expectativas UI
heredadas siguen necesitando actualización antes de retomar la regresión. Ningún CA
se declara PASA sin ejecución. Cinco recorridos con participantes: pendientes, sin
resultados inventados. No se fusiona ni despliega automáticamente.

## Arquitectura implementada

- `experiencia/flujo.py`: estado de avance separado del estado financiero, campos
  diferidos, una pregunta a la vez, captura local, revisión aceptada por revisión,
  historial de cambios en memoria. No depende de Streamlit ni llama al proveedor.
- `experiencia/preguntas.py`: etiquetas, preguntas y estados legibles. El parser
  existente admite también «quiero 15000 en 24 meses» y «cuotas 300»; los datos
  contradictorios permanecen atómicos y los valores existentes requieren confirmación.
- `conversacion/gestor.py`: reutiliza validación, confirmación/cancelación, cálculo,
  escenarios y PDF. El modo guiado no muestra evaluaciones automáticas mientras captura.
  Toda mutación invalida revisión aceptada, resultado, escenario, informe y activación IA.
- `experiencia/evidencia.py` y `ui_documentos.py`: boletas, otros ingresos y patrimonio
  separados. Reutilizan lectura PDF/imagen/OCR en el servidor con confirmación explícita.
  Otros respaldos no producen candidatos de ingreso. Metadatos patrimoniales admitidos:
  tipo de bien, documento presentado, valor opcional, fuente, relación declarada, fecha
  y observación filtrada. Confirmación y descarte justificado; verificación externa
  siempre ausente. Duplicado exacto se detecta con hash en memoria; duplicados por mes
  permanecen bajo las reglas financieras existentes.
- `dominio/modelos.py`: agrega `Respaldo` separado de `Evidencia`; no altera fórmulas.
  `servicios/reporte.py` exporta metadatos y pendientes, nunca archivos/OCR completos.
- `experiencia/tarjetas.py`: cuatro indicadores con Pendiente para ausencias, estados
  de revisión humanos y diferencias calculadas entre resultados base/escenario.
- `ui_flujo.py`: inicio con acciones, progreso, revisión, cards 2x2 y CSS de columna
  única en móvil, una alerta destacada, detalle/escenario plegables, informe y preguntas
  posteriores. Sidebar cerrado al inicio con resumen, documentos, simulaciones,
  historial y herramientas avanzadas. Los nueve escenarios estratégicos se conservan.
- `experiencia/ambientes.py`: únicamente demo, fallo cerrado si APP_ENV es distinto.
  Un selector no habilita piloto privado ni producción. `GEMINI_ENABLED=false` bloquea
  consultas remotas desde la interfaz y su orquestador.

## Frontera de IA

El gestor ya no llama al intérprete remoto durante la captura, ni siquiera si recibe
los argumentos legacy de configuración IA. `ia.politicas.resolver` queda como ruta
local de compatibilidad. `Gemini` solo expone el adaptador `explicar` para el flujo nuevo.

`experiencia/ayuda_ia.py` exige resultado con cuota calculada, revisión aceptada vigente,
ausencia de cambio pendiente, consentimiento específico, configuración, habilitación
de servidor y presupuesto de sesión. Cambiar datos o crear un escenario revoca la
activación anterior. La explicación de un escenario utiliza primero el simulador local.

El contexto se construye por selección explícita: producto, monto/plazo/TEA, indicadores
numéricos de Python, umbral, códigos canónicos de alertas, conteo de evidencias, campos
pendientes y versión de reglas. No usa `asdict(expediente)` ni envía mensajes históricos,
documentos, imagen, OCR, nombre de archivo, observación, justificación de discrepancia
o ingreso personal identificable. Tampoco copia el texto libre de reglas que pudiera
contener anotaciones del analista; usa explicaciones canónicas por código.

La pregunta pasa por filtros conservadores. La respuesta solo puede contener IDs de
hechos y sugerencias de lista cerrada; se rechazan claves desconocidas/duplicadas,
importes adicionales, PD o texto de aprobación. Se renderizan plantillas locales a
partir de los hechos actuales. Errores de red, 404/429, timeout o salida inválida dan
explicación local, diagnóstico discreto y corte de sesión sin alterar datos ni PDF.
Se conservan límite de 20 llamadas, un intento por turno, 2000 caracteres de pregunta,
8000 de contexto, 1024 tokens, 4096 caracteres de respuesta aceptada y timeout.

## RF implementados (identificadores de trazabilidad de esta entrega)

El SRS no numera RF individuales; se usa la siguiente correspondencia para revisión.
«Implementado» describe código, **no aceptación verificada**.

| RF | Alcance SRS | Implementación |
|---|---|---|
| RF-S5-01 | §3 saludo/inicio | Flujo local y acciones de evaluación/simulación |
| RF-S5-02 | §3 preguntas/ausencias | Orden centralizado y diferidos sin asignar ceros |
| RF-S5-03 | §3 captura/corrección | Parser existente ampliado, confirmación/cancelación |
| RF-S5-04 | §4 respaldo ingresos | Boletas contextualizadas, confirmación y lectura en servidor |
| RF-S5-05 | §4 otros documentos/patrimonio | Respaldo separado, metadatos, sin efecto sobre capacidad |
| RF-S5-06 | §3 revisión | Tabla de fuentes y confirmación antes del resumen |
| RF-S5-07 | §5 cards/alertas | Cuatro ViewModels, Pendiente, alerta principal y detalle |
| RF-S5-08 | §5 escenarios/PDF | Motor existente, comparación, gráficos y revisión vigente |
| RF-S5-09 | §6 captura sin IA | Gestor y resolver exclusivamente locales |
| RF-S5-10 | §6 IA posterior | Opt-in por resultado, facts, esquema cerrado y plantillas |
| RF-S5-11 | §6 fallos/límites | Diagnóstico seguro y fallback sin mutaciones financieras |
| RF-S5-12 | §7 sidebar | Resumen, documentos, escenarios, historial y avanzados |
| RF-S5-13 | §2 entornos | Demo con aviso, servidor remoto aclarado, no producción |
| RF-S5-14 | §9 compatibilidad | Fórmulas/umbrales conservados, estrategia 3x3 secundaria |

## Matriz CA (no ejecutada)

Todos los estados siguientes son **PENDIENTE CON JUSTIFICACIÓN**: pruebas excluidas
por instrucción del usuario. La referencia indica dónde revisar, no una evidencia de PASA.

| CA | Referencia de implementación / comprobación pendiente | Estado |
|---|---|---|
| CA-01 | `ui_flujo.mostrar/opciones`, bienvenida sin tabla vacía | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-02 | `recibir_guiado`: saludo local | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-03 | `iniciar/siguiente` y progreso | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-04 | Parser: quiero/monto/plazo, siguiente TEA | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-05 | `diferir`: TEA pendiente sin valor | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-06 | Parser múltiple y orden de descuento de cuotas | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-07 | Diferidos, ausencia no equivale a cero | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-08 | Parser historial insuficiente y días nulos | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-09 | `mostrar_documentos`: uploader contextual, sin IA | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-10 | Promedio original `servicios.reglas` | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-11 | Solo boletas confirmadas; estados visibles | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-12 | Regla original de mes duplicado y descarte justificado | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-13 | Excepción documental localizada y transcripción manual | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-14 | Regla original de discrepancia y formulario de aclaración | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-15 | Respaldo patrimonial y metadatos locales | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-16 | Aviso explícito de ausencia de verificación/garantía | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-17 | Allowlist no contiene nombre/ID documental ni OCR | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-18 | Diferir evidencia y pendientes documentales visibles | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-19 | `cronograma` sin cambios; valor de referencia no ejecutado | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-20 | Cuatro tarjetas con cifras del resultado | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-21 | Null-safety y etiqueta Pendiente en DTI | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-22 | Una alerta principal; resto plegado | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-23 | Detalle con gráficos y cronograma del motor | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-24 | Simulador local, comparación y base intacta por diseño | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-25 | Invalidación del informe y controles por revisión | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-26 | Captura local sin enlace al adaptador remoto | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-27 | Gate posterior + consentimiento independiente | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-28 | `hechos`: selección explícita, no serialización del expediente | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-29 | Selección de IDs, plantillas locales | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-30 | Ediciones/simulaciones retornan al gestor local | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-31 | Contrato cerrado; texto/cifras libres no admitidos | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-32 | Error seguro y explicación local sin modificar PDF | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-33 | Invalidación central y revocación IA por revisión | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-34 | Sidebar inicial cerrado con etiquetas legibles | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-35 | CSS 2x2/1 columna; falta inspección real a 375 px | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-36 | Controles nativos y títulos semánticos; falta revisión con teclado | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-37 | Consentimiento sintético y detección parcial de PII; no garantiza detección total | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-38 | `entorno` bloquea toda modalidad distinta de demo | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-39 | `ui_estrategia` y motor 3x3 conservados | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-40 | NO EJECUTADO por instrucción; tests anteriores sin actualizar | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-41 | Sin participantes; cinco recorridos no realizados | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |
| CA-42 | PDF incluye fuentes, versión, supuestos y metadatos, no documento bruto | PENDIENTE CON JUSTIFICACIÓN: no ejecutado |

## Procedimiento manual para el usuario

1. Abrir demo; escribir «hola» y pulsar Iniciar evaluación. Escribir «Quiero 10000
   en 12 meses» y luego «TEA 25%». Responder ingreso 3500, gastos 1400, cuotas 300,
   no descontadas, continuidad 24 meses y sin mora. Verificar que solo se pregunte
   el siguiente campo pendiente y que no aparezca activación Gemini todavía.
2. Subir tres boletas sintéticas de meses distintos, revisar cada vista y confirmar
   fecha, neto y extraordinarios. Otra alternativa: no disponer de documentos, dejando
   sus pendientes visibles. No usar archivos personales.
3. Declarar un inmueble opcional y presentar documento sintético; completar metadatos
   sin nombres/direcciones/partidas reales, confirmar transcripción. Comprobar que su
   valor no aumenta ingreso ni capacidad. Continuar con pendientes si no hay documento.
4. Revisar fuentes y confirmar. Comparar cuota con el motor, DTI y saldo; no interpretar
   un estado como aprobación. Abrir detalle, simular 24 meses y comprobar diferencias
   sin sobrescribir base. Generar PDF y corregir ingreso: debe desaparecer el anterior.
5. Repetir sin historial, con boletas faltantes, con meses duplicados y con discrepancia
   de ingreso. Confirmar correcciones o cancelarlas; no elegir fuentes automáticamente.
6. Solo después de un resultado, consentir preguntas IA y preguntar por DTI. Revisar
   diagnóstico/fallback si falla. No compartir la clave. Desactivar con Seguir sin IA.
7. Repetir con `GEMINI_ENABLED=false` y sin clave: captura, documentos, cálculo y PDF
   deben funcionar sin llamadas. Probar entorno distinto de demo: pantalla bloqueada.
8. Revisar desktop/móvil y teclado; registrar capturas sin claves y fricciones reales.

## Límites y desviaciones explícitas

- No tests nuevos/adaptados, regresión, mocks ejecutados ni capturas por petición del
  usuario. La implementación requiere su revisión antes de considerar aceptación.
- No extractor universal para otros documentos: registro y metadatos manuales; no
  hay política que habilite sus importes como ingreso neto ni como garantía.
- El estado de avance es puro y en memoria; no es una auditoría durable ni permite
  recuperar una sesión cerrada. Se conserva cancelación de propuestas, no un historial
  de snapshots financieros con restauración arbitraria.
- El filtro PII es conservador e incompleto, especialmente sin OCR o con imágenes.
  Se exige declaración de material sintético; no se promete anonimización ni seguridad
  bancaria. El original nunca se transmite a Gemini; sí se sube al servidor al cargarlo.
- Una respuesta de IA solo organiza hechos permitidos; no es redacción libre ni
  comprensión universal. El parser local pide cifras/unidades ante lenguaje no cubierto.
- APP_ENV no desbloquea infraestructura privada. Autenticación, roles, custodia, cifrado,
  auditoría durable, retención, políticas oficiales y aprobación formal siguen fuera
  del sprint; deben implementarse antes de cualquier piloto con clientes reales.
