# Mensaje listo para Codex — Sprint 5 UNIFICADO

Trabaja en `JuanClimacoPrada/Triple-T`. Lee íntegramente los adjuntos:
- `01_ARQUITECTURA_ACTUAL.md` (mapa del código revisado).
- `02_SRS_SPRINT5_UNIFICADO.md` (**fuente de verdad del sprint**, sustituye el SRS 1.0 anterior).
- `04_CRITERIOS_ACEPTACION.md` (matriz obligatoria).

**Objetivo:** convertir Triple-T en un copiloto crediticio guiado, fácil de utilizar sin capacitación. Implementa EN UN SOLO SPRINT los cuatro bloques conectados: (A) conversación de captura y evaluación guiada sin IA; (B) requerimiento contextual de respaldo documental de ingresos y, opcionalmente, de propiedad, procesados en backend local sin enviarlos a Gemini; (C) dashboard final muy visual con cuatro tarjetas, alertas breves, gráficos, escenarios, PDF y panel lateral intuitivo; (D) preguntas opcionales a Gemini *solo después* de obtener un análisis, limitadas a explicar hechos calculados y nunca a modificar el expediente.

**Flujo esperado:** inicio → solicitud → ingresos/gastos/deudas → historial → respaldo ingresos → posible patrimonio → confirmar datos → calcular → cards/gráficos/PDF → preguntas opcionales a IA.

**Requisitos clave:**
1. Al escribir «hola», saludo natural y 2–3 opciones claras; ninguna ayuda técnica larga, JSON ni texto de SDK.
2. Preguntas progresivas y botones «No sé», «No dispongo», «Agregar después», sin inferir 0 ni valores. Si el analista da varios campos, aceptarlos y preguntar solo el siguiente.
3. Solicitar una boleta/otro documento justificativo de ingresos. Si declara propiedad, solicitar constancia/título y manejarlo como patrimonio **declarado y NO verificado**; no tomarlo como garantía válida ni como ingreso. La extracción actual de boletas no sirve automáticamente para titularidad o documentos generales; extender con cuidado y confirmación explícita.
4. El procesamiento de documentos y el motor financiero funcionan sin IA. No subir documento, OCR, nombre de archivo ni notas a Gemini. No enviar documentos reales ni PII en el Streamlit público. Aclara en UI que el backend en Streamlit Cloud NO es el equipo local del usuario.
5. Cuando haya información suficiente, mostrar cards: cuota, DTI, disponible después de cuota y estado del expediente; si faltan valores, marcar `Pendiente` sin inventar 0. El gráfico, cronograma, escenario y PDF deben quedar accesibles sin ocupar toda la pantalla de chat.
6. Rediseñar panel izquierdo: inicialmente plegado, resumen útil, documentos, escenarios y ajustes avanzados secundarios. Labels bancarios claros, no campos internos.
7. Cambiar enrutamiento actual de Gemini: **ninguna llamada remota durante el flujo guiado ni carga documental**. Después del análisis, ofrecer opt-in «Preguntar a la IA sobre este análisis» y una explicación de alertas/escenarios, sobre facts allowlist derivados de Python. No edición autónoma, no números inventados; sanitizar respuestas o usar plantillas locales si la IA no supera validación. Mantener fallback y no intentar llamadas automáticas.
8. Mostrar un aviso discreto y claro de entorno de demostración; NO eliminar la protección de datos, no presentar la instancia pública como autorizada para clientes reales ni habilitar `private_pilot/production` sin controles. Lenguaje de producto profesional en el resto de la interfaz.
9. NO modificar sin justificación las fórmulas, umbrales ni reglas de negocio del motor; preservar los 9 escenarios estratégicos, simulaciones, evidencias, PDF, confirmaciones y reversión de datos. Actualizar las pruebas UI antiguas y ejecutar regresión; ninguna prueba real de Gemini sin consentimiento y credenciales privadas del dueño.
10. Priorizar una experiencia completa end-to-end antes de añadir funcionalidades accesorias. Evitar `st.rerun()` que pierda contexto, mostrar claramente la etapa y progreso.

**Entrega:** rama `feature/sprint5-flujo-documentos-cards-ia`, un solo Pull Request sin merge, `docs/SPRINT_5.md`, tabla RF/CA implementados, resultados de `python -m unittest discover -s tests -v`, capturas desktop y móvil, explicación de cualquier caso omitido, pruebas mock que demuestren que ninguna evidencia sale a Gemini, y procedimiento de prueba manual. No publicar claves, no integrar APIs pagas y no habilitar datos personales reales.

**Importante:** si existen requerimientos contradictorios en instrucciones anteriores, este SRS unificado tiene prioridad para el Sprint 5. Antes de cambiar el código revisa el HEAD vigente de `main` y reutiliza las implementaciones ya existentes.
