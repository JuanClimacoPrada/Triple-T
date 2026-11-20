# Sprint 1: motor financiero académico

## Revisión inicial

Base: `df9c04f`. `app.py` contenía el chat de ocho parámetros, tres casos ficticios,
calculadora de pérdida esperada y comparación estratégica. `motor.py` agrupaba
cuota francesa, reglas comunes y los nueve escenarios. Las ocho pruebas originales
pasaban. No había políticas diferenciadas por producto ni tabla de amortización.

## Definiciones acordadas antes de implementar

Se separan cuatro perfiles configurables conservando las reglas académicas:
cuota/ingreso >30%, mora >30 días y continuidad de ingresos <6 meses.
El indicador heredado de estabilidad favorable a partir de 12 meses se conserva;
no equivale al umbral de alerta. No son políticas del BCP ni normas regulatorias.

| Producto | Definiciones pendientes, sin valores inventados |
| --- | --- |
| Personal | Montos, plazos, límite de servicio total de deuda y documentación |
| Vehicular | Cuota inicial, valor del vehículo, garantía, porcentaje financiable |
| Hipotecario | Tasación, cuota inicial, garantía, porcentaje financiable |
| Empresarial | Cobertura de deuda, estacionalidad, capital de trabajo, garantías |

Los perfiles son instancias independientes en `reglas_credito.py`. Se pueden
configurar los umbrales y un límite opcional de servicio total de deuda, sin
introducir decisiones automáticas. `evaluar(s, reglas=...)` permite una política
explícita para simulaciones y pruebas; la interfaz usa el perfil seleccionado.

Convenciones aceptadas:

- Soles, pagos mensuales vencidos, TEA fija, sistema francés, meses de igual duración.
- Sin periodos de gracia ni pagos extraordinarios.
- Personas: ingreso neto después de descuentos de nómina y antes de gastos del
  hogar/deudas. Registrar cada gasto u obligación una sola vez.
- Empresas: ingreso representa flujo neto mensual antes de deuda. Registrar cero
  en gastos si ya se descontaron del flujo. No confundir ventas con flujo neto.
- No se incluyen seguros, comisiones, impuestos, tasación, gastos notariales o
  registrales ni cargos por mora. La TEA no es la TCEA. Referencia conceptual:
  [SBS: Aprende sobre créditos](https://www.sbs.gob.pe/usuarios/aprende-con-la-sbs/aprende-sobre-creditos).

## Cálculos y límites

`TEM = (1 + TEA/100)^(1/12) - 1`.
Cuota teórica: `monto × TEM / (1 - (1 + TEM)^(-meses))`; a tasa cero, monto/plazo.
Se usan `log1p`/`expm1` para evitar cancelación numérica con tasas pequeñas.

- Flujo disponible previo = ingreso − gastos − otras cuotas.
- Capacidad por flujo = máximo de cero y flujo disponible previo.
- Capacidad según reglas = máximo de cero y menor de: flujo previo,
  ingreso × límite de cuota, e ingreso × límite total − otras cuotas (si se define).
- Saldo disponible = flujo previo − cuota teórica; se muestra negativo si hay déficit.
- Endeudamiento actual/total = otras cuotas / ingreso y (otras cuotas + nueva cuota)
  / ingreso. Son ratios de servicio mensual de deuda, no de saldos de principal.
- Cobertura de cuota = flujo previo / cuota. No se aplica un umbral no acordado.
- Sin ingreso, ratios sobre ingreso son N/D; no se divide por cero.

El cronograma usa Decimal, redondea importes a céntimos con ROUND_HALF_UP y ajusta
la última cuota al principal restante. Capital + interés = cuota y la suma del
capital es el monto. Los totales mostrados junto al cronograma suman esas filas;
el informe original conserva los totales teóricos sin redondeo mensual.
Montos del cronograma deben tener hasta dos decimales. El límite técnico de 1200
filas no es un límite de producto. La interfaz conserva los límites técnicos
heredados: hasta 360 meses, TEA 0–200% y montos hasta S/ 10 millones.

El simulador permite variar monto, plazo y tasa y exportar el cronograma CSV.
Los campos vacíos bloquean el informe; datos negativos, no finitos, booleanos,
tipos incorrectos y plazos fraccionarios se rechazan. Un déficit produce alertas
y recomendación de revisión humana, nunca aprobación/rechazo automático.

La calculadora de pérdida esperada se conserva, pero PD y LGD empiezan vacías:
solo se calcula si el usuario introduce ambos supuestos ficticios.
No se estima PD, no hay ML entrenado ni recopilación de información personal.
Las tres alternativas y nueve combinaciones originales se conservan sin cambiar
inversiones, reducciones ni fórmula estratégica. La Ficha N.° 16 original no está
incluida en el repositorio: la regresión verifica la matriz existente.

## Validación y despliegue

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m streamlit run app.py
```

Las pruebas cubren referencias numéricas, identidades contables del cronograma,
casos límite, aislamiento de perfiles, compatibilidad del motor y recorridos
Streamlit con AppTest. Las pruebas de interfaz requieren instalar Streamlit.
Se conserva Python 3.11+, Streamlit y la biblioteca estándar; no se agregan
servicios comerciales ni secretos. Community Cloud debe recibir también
`reglas_credito.py`. La rama se entrega para revisión, sin desplegar ni fusionar.
