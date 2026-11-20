PREGUNTAS = [
    ("ingreso", "¿Cuál es el **ingreso mensual** del solicitante en soles? Ejemplo: `3500`", float, 0, 10000000),
    ("gastos", "¿Cuánto gasta mensualmente, sin contar las cuotas de otras deudas?", float, 0, 10000000),
    ("otras_cuotas", "¿Cuánto paga al mes por **otras deudas**?", float, 0, 10000000),
    ("monto", "¿Cuánto dinero solicita (S/)?", float, 0.01, 10000000),
    ("meses", "¿En cuántos **meses** pagará el préstamo?", int, 1, 360),
    ("tea", "¿Cuál es la **tasa efectiva anual (TEA)** supuesta en %? Ejemplo: `25`", float, 0, 200),
    ("estabilidad_meses", "¿Cuántos meses de continuidad de ingresos tiene?", int, 0, 600),
    ("dias_mora", "¿Cuántos días de atraso o mora vigente registra en este caso ficticio?", int, 0, 10000),
]

CASOS = {
    "Optimista": dict(ingreso=45000, gastos=10000, otras_cuotas=0, monto=2000, meses=1, tea=18, estabilidad_meses=84, dias_mora=0),
    "Esperado": dict(ingreso=3500, gastos=1400, otras_cuotas=300, monto=10000, meses=12, tea=25, estabilidad_meses=24, dias_mora=0),
    "Pesimista": dict(ingreso=0, gastos=0, otras_cuotas=0, monto=20000, meses=24, tea=25, estabilidad_meses=0, dias_mora=60),
}
