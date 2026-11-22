# Interfaz profesional integrada

La interfaz adapta los archivos visuales entregados (`triple_t_pro_layout.py` y
`triple_t_pro_styles.css`) al flujo y expediente existentes. Usa el flyer como
referencia de colores, navegación lateral, conversación central y panel derecho.
Los importes, score, riesgo y porcentajes ilustrativos del paquete no se utilizan.

## Funcionamiento

- Navegación: análisis, simulador, expediente, historial de sesión y ayuda.
- Conversación con burbujas, etapas y controles contextuales. Admite «No lo sé»,
  «Agregar después» y «¿Por qué necesitas ese dato?», sin consultar a Gemini.
- Panel progresivo calculado por el motor: cuota, DTI y saldo disponible. La
  vista preliminar no confirma datos, crea informes ni habilita la asistencia IA.
- Comparación del expediente base y escenario vigente; barras calculadas para
  el plazo elegido y hasta dos plazos adicionales, con el mismo monto y TEA.
  Son cuotas base teóricas, sin cargos, no ofertas de entidades financieras.
- Gráfico de uso del ingreso basado en gastos, otras cuotas, nuevo pago y saldo
  calculados. No inventa una composición de ingresos por fuente. Cuando falta
  capacidad calculable o existe déficit, muestra una explicación en su lugar.
- Documentos, confirmación de transcripciones, simulaciones, detalles,
  amortización, PDF y análisis estratégico mantienen sus módulos existentes.
- HTML dinámico escapado, iconos SVG locales, sin fuentes externas ni nuevas
  dependencias. Tema claro y distribución adaptable mediante CSS.

## Ajuste de conversación

El historial utiliza `st.container(autoscroll=True)` para seguir los mensajes
nuevos con las burbujas HTML personalizadas. La entrada se coloca inmediatamente
debajo del historial, antes de los controles contextuales. Las sugerencias se
agrupan horizontalmente y saltan de línea cuando falta ancho. Las etapas quedan
en un desplegable encima del historial, con la etapa actual visible en su título.
El aviso sobre revisiones anteriores se concentra en ese desplegable.

Se requiere Streamlit 1.57 o posterior para usar estas opciones nativas; el mínimo
se actualiza en `requirements.txt`. No se inyecta JavaScript ni se crean iframes.
Este ajuste tampoco se ha probado en ejecución: la validación automatizada y
visual sigue pendiente de autorización del responsable.

## Panel por pestañas e indicadores

El resumen incorpora capacidad de pago mensual (`capacidad_neta`) además de
cuota, DTI y saldo. Es la disponibilidad antes del nuevo pago, limitada a cero;
no es una aprobación ni se presenta como porcentaje. Indicadores muestra también
`capacidad_umbral`, ingreso admisible, umbral académico, nuevo pago/ingreso,
intereses y TCEA. Si el motor no puede calcularlos, permanecen pendientes.

El panel se organiza en Resumen, Indicadores, Gráficos, Detalle, Simular e Informe
e IA. Cada pestaña contiene un área de desplazamiento de 480 px para que las
tablas y formularios no extiendan toda la página. Score y Sentinel quedan en
Indicadores; los controles posteriores a la confirmación conservan su bloqueo.
Las fórmulas del motor no cambian. Validación visual y automatizada pendiente de
autorización; no se han ejecutado pruebas para este ajuste.

## Configurar servicios externos

`SENTINEL_URL` se configura en Secrets de Streamlit o como variable de entorno.
Debe ser una URL HTTPS externa fija, sin credenciales, parámetros ni fragmentos.
La variable de entorno tiene prioridad. Desde la mejora de riesgo hipotético,
una URL ausente o vacía usa el portal oficial de referencia; una URL explícita
inválida mantiene visible «Consultar Sentinel» deshabilitado.

El enlace abre otra pestaña con `noopener noreferrer` y `no-referrer`; no añade
datos del expediente. La tarjeta muestra «No disponible»: no hay API de Sentinel
ni fuente autorizada de score integrada. El responsable debe configurar el
destino adecuado para su acceso al servicio.

Gemini conserva el consentimiento explícito y la restricción a explicaciones
sobre resultados confirmados. El nuevo panel no realiza consultas remotas.
Los documentos siguen procesándose en el servidor; nunca se envían a Gemini.
La captura guiada y los cálculos continúan independientes de su disponibilidad.

## Estado de validación de esta entrega

**Nota posterior:** el cambio de riesgo hipotético actualiza y ejecuta las pruebas
automatizadas con autorización expresa. Véase `RIESGO_HIPOTETICO.md`. El texto
siguiente documenta el estado histórico de la entrega inicial del diseño.

Por instrucción del responsable, se prepara primero el PR para su merge manual.
**No se ejecutaron pruebas automatizadas, arranque de la aplicación ni revisión
visual de escritorio o móvil en esta entrega.** Tampoco se generaron capturas.
Las pruebas existentes permanecen sin cambios; las de UI de versiones anteriores
requieren adaptación al flujo guiado antes de poder dar una validación vigente.

Después de que el responsable comunique el merge se solicitará autorización para
adaptar y ejecutar las pruebas, revisar ambos tamaños de pantalla y obtener las
capturas. Quedan pendientes la fidelidad visual observada, el ajuste de selectores
CSS a la versión instalada de Streamlit y la regresión funcional completa.

La interfaz implementada no constituye una validación bancaria, una aprobación o
rechazo de crédito, ni una verificación de autenticidad documental. Se mantienen
las restricciones de la instancia de demostración respecto a datos reales.
