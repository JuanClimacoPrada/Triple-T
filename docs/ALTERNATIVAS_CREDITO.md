# Comparación de alternativas de crédito

Triple-T compara tres condiciones de un mismo préstamo personal en soles. El
flujo usa un caso sintético, el resultado financiero base y el mismo motor que
calcula la amortización. La comparación tecnológica de la Ficha N.° 16 conserva
su propia evaluación y sus nueve resultados.

## Flujo del analista

1. Completa la captura guiada y confirma el caso. También puedes cargar el caso
   sintético Esperado desde Desarrollo en una sesión local con
   `TRIPLE_T_HERRAMIENTAS_DEV=true` y registrar los pendientes.
2. Abre **Alternativas**. A parte de las condiciones del expediente, B duplica
   el plazo hasta 360 meses y C parte del 80% del monto, a céntimos. Si el límite
   impide diferenciar alguna opción, completa sus condiciones en el editor.
3. Revisa la matriz y las consecuencias de cada alternativa. Las tres caídas
   iniciales de ingreso admisible son 0%, 10% y 30%. Se editan por alternativa,
   en orden creciente. El motor mantiene los gastos y las otras cuotas y aplica
   el tratamiento de planilla del expediente. Las tasas y cargos de alternativa
   son supuestos del ejercicio. Los vencimientos proyectados se identifican y
   el motor calcula TCEA únicamente con flujos de costos y fechas completos.
4. Pulsa **Seleccionar alternativa A**, B o C, revisa los tres escenarios y
   escribe una justificación breve sin datos personales. Confirma o cancela.
   El registro guarda la revisión, hora de Lima, condiciones, supuestos,
   evaluación y justificación dentro de la sesión.
5. Abre **Informe** y prepara el PDF. Incluye las nueve combinaciones,
   ponderación, consecuencia comparativa, recomendación y elección vigente.
   Una edición del caso, de costos, de evidencia o de la matriz invalida la
   elección y el informe. También se comprueba la versión de reglas y ponderación.

## Ponderación académica

| Criterio | Peso | Escala de 0 a 100 |
| --- | ---: | --- |
| DTI | 30% | 100 hasta el umbral configurado, 0 desde 60% por defecto, descenso lineal entre ambos |
| Capacidad | 25% | Saldo después de cuota dividido por el 30% del ingreso admisible base, limitado a 0–100 puntos |
| Resistencia | 20% | Proporción de los tres escenarios con saldo no negativo y DTI dentro del umbral |
| Intereses | 15% | Descenso lineal de 100 a 0 entre intereses iguales a cero y al 50% del principal de la alternativa |
| Cobertura | 10% | Capital financiado dividido por monto solicitado, con tope de 100 puntos |

La configuración de escala vive en `EscalaPuntuacion`. Si el umbral DTI de la
sesión llega al 60% o lo supera, el límite de puntuación mínima queda 30 puntos
porcentuales por encima del umbral. La interfaz y el PDF muestran la escala
efectiva. El promedio de los tres puntajes es aritmético y carece de probabilidades
asignadas. DTI y capacidad están correlacionados porque usan el mismo flujo.

Los datos bloqueantes o un DTI indefinido dejan puntajes pendientes. Cuando se
puede calcular con respaldo aún insuficiente, la evaluación queda preliminar.
Las alertas de cada escenario permanecen visibles. La recomendación prioriza
para revisión las opciones que resisten los tres escenarios sin alertas relevantes,
o indica que ninguna reúne esas condiciones. La escala mide ventajas del préstamo
dentro del ejercicio académico. La PD hipotética y el score Sentinel son indicadores
separados y carecen de efecto en la ponderación.

## Conversación y privacidad

Gemini se activa desde el chat mediante consentimiento explícito para el modo
de demostración. Interpreta la consulta admisible en español junto con la etapa,
hechos del motor y referencias de sesión permitidas. El historial bruto,
documentos, OCR, nombres de archivo, notas y secretos permanecen fuera de la
petición. El filtro reduce la exposición de texto personal, pero requiere que
el usuario introduzca únicamente material sintético. Se preservan el modelo
configurado, la confirmación de nivel gratuito, el máximo de 20 llamadas por
sesión, el timeout y el modo local ante fallos.

El contrato de respuesta acepta intenciones, referencias, entidades acotadas y
hechos identificados. Python valida la respuesta, toma los valores de los hechos
calculados y gestiona los cambios. Las correcciones y registros semánticos se
proponen para confirmación. La selección se confirma en el comparador y una
simulación mantiene el expediente base. La justificación se introduce en el
formulario local.

Ejemplos para comprobar después del despliegue del propietario en
[Triple-T](https://triple-t.streamlit.app/), con el caso Esperado:

- «¿Cuánto tendría que soltar cada mes?» y «¿De cuánto queda la letra?».
- «¿Cuánta parte del sueldo se va pagando deudas?».
- «Compara A con B y dime por qué una sale más cara».
- «¿Qué pasa si le damos dos años?» y «¿Y si se le cae el ingreso 30%?».
- «¿Qué pierde si reduce el monto?» y «¿Por qué aparece TCEA pendiente?».
- «Me quedo con la segunda». Luego revisa y confirma B con una justificación.

La equivalencia de redacciones con un modelo real necesita validación manual
con consultas sintéticas y consentimiento. El proveedor simulado verifica el
contrato y el flujo de Triple-T. [Referencia del SDK para salida estructurada](https://googleapis.github.io/python-genai/index.html#json-response-schema).

## Trazabilidad con la Ficha N.° 16

| Paso y requisito | Implementación | Evidencia local | Estado |
| --- | --- | --- | --- |
| 2. Variables del caso y calidad de evidencia | `servicios/reglas.py`, `servicios/simulacion.py` | Suite financiera y casos de planilla, documentos y cargos | Verificado |
| 3. Tres condiciones de préstamo y nueve escenarios | `servicios/alternativas.py`, `ui_alternativas.py` | Pruebas de matriz, edición, límites y expediente inmutable | Verificado |
| 4. Puntuación y escenarios de estrés | `servicios/alternativas.py` | Pesos, valores extremos, DTI N/D, alertas y recomendación | Verificado |
| 5. Consecuencias, decisión del analista y PDF | `experiencia/comparador.py`, `servicios/reporte.py` | Integración de Streamlit para elección, edición y PDF | Verificado |
| Conversación transversal y privacidad | `experiencia/ayuda_ia.py`, `ia/contrato_semantico.py`, `ia/privacidad.py` | Pruebas de proveedor simulado, confirmación y recuperación local | Contrato local verificado. Comprensión remota pendiente |

La suite local ejecutó **104 pruebas satisfactorias** con
`python -m unittest discover -s tests -v` y `GEMINI_ENABLED=false`.
La prueba integral comprobó la selección, su cancelación, el contenido del
PDF y su invalidación después de editar un escenario. Las pruebas de Gemini
utilizaron un proveedor simulado y verificaron parámetros extraídos, referencias
del turno anterior, privacidad y respuestas inválidas. Queda pendiente evaluar
la comprensión del modelo remoto con configuraciones autorizadas.

En Edge local se verificó el flujo del caso Esperado a la pestaña Alternativas
con anchos de 1440 y 390 px. Las tres tarjetas y la matriz quedaron dentro de
la pantalla. La tabla permite desplazar sus columnas dentro del panel en móvil.
