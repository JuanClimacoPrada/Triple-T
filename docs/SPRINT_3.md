# Sprint 3 — chat principal

Base verificada: `origin/main`, `d5329f3`, merge PR #2. Rama:
`feature/sprint3-chat-principal`. No se modificó main ni se desplegó.

## Implementación y decisiones

- `conversacion/intenciones.py`: parser puro tipado, sin cálculos financieros ni red.
- `conversacion/gestor.py`: captura, propuestas de corrección, confirmaciones, estado,
  evidencias, escenarios e informes, delegando cálculos a los servicios existentes.
- `conversacion/modelos.py`: estado y mensajes de una única sesión.
- `conversacion/respuestas.py`: plantillas construidas con resultados del motor.
- `ui_chat.py`: chat principal, herramientas adyacentes, panel experto y 3×3 secundario.
- `ui_resultados.py`: presentación reutilizada del Sprint 2; `app.py` solo inicia la UI.

El parser reconoce un vocabulario acotado; no es IA generativa ni comprensión universal
del español. Si un mensaje contiene ambigüedades/contradicciones, no guarda ninguna
entidad de ese turno. Pide TEA explícita; no convierte tasas nominales o mensuales.

Separadores: `3.500` es ambiguo y se pide aclarar. Se aceptan miles con coma en grupos
de tres (`3,500`) conforme al diálogo del SRS y decimales con uno/dos dígitos (`25,5`).
Separadores mixtos se rechazan. Años se convierten a meses únicamente como unidad.

Correcciones de datos existentes se proponen y requieren un botón de confirmación.
Las consultas «¿y si…?» generan escenario: mantienen parámetros del escenario activo
o de la base si no hay escenario, y lo explican. «Qué datos tienes» vuelve a la base.
Una cuota parcial utiliza `cronograma`, sin afirmar capacidad ni inventar cargos.
Si la capacidad está bloqueada, se permite simular solo condiciones de préstamo;
la caída de ingreso exige resolver primero los pendientes del motor.

Cambios del expediente invalidan escenario/PDF. Cambios de ingresos o evidencias
invalidan aclaraciones. Un cambio de contrato exige reconfirmar flujos/costos para TCEA.
El historial de mensajes anteriores se marca como no vigente cuando cambia la revisión.
No se mantienen informes anteriores descargables después de una modificación.

Los candidatos documentales siguen pendientes hasta confirmar. No se envía texto de
documentos al parser conversacional. La detección básica de identificadores se aplica
antes de incorporar mensajes; no garantiza anonimización. Todo permanece en sesión.

## Ejemplos soportados

1. «Cliente gana 3500 soles, solicita 10000 soles a 12 meses con TEA 25%».
2. «¿Cuál es la cuota?» — cuota teórica, sin afirmar capacidad con datos pendientes.
3. «Gastos 1400 y otras cuotas 300»; «estabilidad 24 meses»; «no están descontadas».
4. «No tiene historial crediticio» — no equivale a mora; subir boletas sintéticas.
5. «Subir boletas» — cargar, revisar página/frase, confirmar o descartar.
6. «Corrige ingreso a 4500» — confirmar cambio, aclarar discrepancia con justificación.
7. «¿Y a 24 meses?»; «¿qué ocurre si el ingreso cae 20%?».
8. «Muéstrame la evolución del saldo y genera PDF».
9. «Compara A, B y C»; «qué falta»; «explica esta alerta»; «reiniciar».

## Matriz de aceptación

| CA-S3 | Evidencia |
| --- | --- |
| 01 | AppTest de inicio sin pestañas; captura `chat-inicial.png` |
| 02 | Parser de cuatro entidades; fuentes DECLARADO_EN_CHAT |
| 03 | Gestor: cuota parcial 938.46, capacidad pendiente |
| 04 | Gestor: DTI total 35.38%, RN-03 |
| 05 | Parser/gestor: INSUFICIENTE y mora None |
| 06 | AppTest: herramientas de boletas adyacentes al chat |
| 07 | PDF sintético: candidatos pendientes, fuente y página |
| 08 | Confirmaciones: promedio 3300 y CONFIRMADO_ANALISTA |
| 09 | Discrepancia con ingreso 4500 |
| 10 | Resolución documental justificada e invalidación posterior |
| 11 | Plazo 24 en copia, base intacta |
| 12 | Caída 20%, ingreso admisible 2800 sobre base 3500 |
| 13 | Escenario activo compartido entre gráficos y cronograma |
| 14 | PDF contiene la cuota del escenario activo; se invalida al cambiar |
| 15 | Negativa a decidir, resumen de alertas para analista |
| 16 | Faltantes basados en campos realmente ausentes |
| 17 | Tasa sin periodicidad: aclaración, sin guardar |
| 18 | Ingreso 3.500: aclaración, sin guardar |
| 19 | Acceso al 3×3 existente y regresión numérica |
| 20 | Confirmación de reinicio y separación de sesiones AppTest |
| 21 | 77 pruebas aprobadas; salida en `evidencias-sprint3/tests.txt` |
| 22 | Arranque/navegador local; Community Cloud pendiente tras aprobación |

Las 56 comprobaciones anteriores se conservan: las siete de UI se adaptaron al chat
y al reinicio confirmado; las 49 de motor/servicios permanecen intactas. Se escribieron
21 pruebas adicionales antes de que el usuario solicitara no implementar más pruebas.
Se respetó esa indicación: no se amplió la suite después. La verificación de navegador
se limitó a arranque y conversación con datos múltiples, capacidad y escenario.

## Limitaciones y entrega

- Cloud no comprobado ni desplegado; CA-S3-22 mantiene ese paso pendiente.
- Se mantiene el fallback OCR y las limitaciones de privacidad/TCEA del Sprint 2.
- No se añadieron dependencias, claves, servicios comerciales, PD ni políticas bancarias.
- No se completó un nuevo recorrido browser exhaustivo de todos los controles de
  adjuntos/PDF; están cubiertos por las pruebas existentes y del gestor, con esta
  limitación visual explicitada en el PR.
- Los scripts de captura del Sprint 2 describen su UI histórica de pestañas; no son
  el recorrido de la interfaz actual.

Ejecutar: `python -m pip install -r requirements.txt`,
`python -m unittest discover -s tests -v`, `python -m streamlit run app.py`.
