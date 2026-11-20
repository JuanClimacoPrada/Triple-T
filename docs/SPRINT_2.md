# Sprint 2: evidencia, simulación y reporte

## Base revisada y decisiones

Rama: `feature/sprint2-evidencia-y-simulacion`, creada desde `origin/main` en
`b579a5a` (PR #1 del Sprint 1 ya fusionado). No se sobrescribieron cambios nuevos.
Especificación: Triple-T v2.0 Sprint 2 SRS v1.0 del 20-11-2026.

Incompatibilidades resueltas explícitamente:

1. Solo personal activo (RN-01). Se preservan APIs y perfiles heredados sin exponer
   evaluación para productos con políticas no definidas.
2. El umbral nuevo aplica al DTI total, no solo cuota/ingreso. La API heredada mantiene
   su contrato y tests; la UI llama al servicio nuevo.
3. Cronograma Sprint 2 conserva precisión interna. La API anterior de redondeo mensual
   se mantiene como compatibilidad.
4. La TCEA utiliza convención referencial ACT/365 y fechas explícitamente confirmadas,
   sin pretender conformidad normativa. Se declara pendiente cuando faltan flujos.

## Módulos

- `dominio/modelos.py`: expediente y evidencia inmutables, cargos, configuración,
  resultados y versión `2.0.0-academico`.
- `servicios/finanzas.py`: Decimal, cronograma, fechas mensuales y TCEA fechada.
- `servicios/reglas.py`: RN-01…RN-15, clasificación, campos, mensajes y cifras.
- `servicios/documentos.py`: límites, extracción, preview, OCR opcional,
  detección básica de identificadores, confirmación/descarte.
- `servicios/simulacion.py`: copia del expediente y caída sobre ingresos admisibles,
  conservando historial y evidencia originales.
- `servicios/reporte.py`: PDF en memoria con fuentes, estado, parámetros, reglas,
  cargos, fechas, escenarios y cronograma, sin documentos crudos.
- `app.py`: pasos 1–6, formularios editables, chat numérico, estado por sesión,
  limpieza e invalidación de aclaración cuando cambian ingresos/evidencias.
- `visualizaciones.py`: gráficos derivados de los mismos resultados.
- `ui_estrategia.py`, `casos.py`: módulo 3×3 y demostraciones conservados.
- `motor.py`: API anterior y calculadora EL ilustrativa intactas.

## Matriz de aceptación

| Criterio | Evidencia automatizada/manual | Estado |
| --- | --- | --- |
| CA-01 | test_ca01_productos_no_habilitados; test_simulacion_modificable_y_productos | Local verificado |
| CA-02/03 | test_ca02_ca03_cuotas_y_precision; verificación manual abajo | Verificado |
| CA-04 | test_ca04_dti_total_y_igualdad | Verificado |
| CA-05 | test_ca05_ingreso_cero; prueba UI con cero | Verificado |
| CA-06 | test_ca06_historial_insuficiente | Verificado |
| CA-07 | test_ca07_discrepancia_y_resolucion | Verificado |
| CA-08 | test_ca08_meses_insuficientes_y_duplicados | Verificado |
| CA-09 | test_ca09_extraccion_y_confirmacion; test_confirmacion_obligatoria | Verificado |
| CA-10 | test_ca10_imagen_y_ocr_fallback; test_ocr_falla_y_limite_paginas | Fallback verificado, OCR Cloud no certificado |
| CA-11 | test_ca11_archivos_invalidos_y_limites; paquetes/imagen corrupta | Verificado |
| CA-12 | test_ca12_patrimonio_no_es_capacidad | Verificado |
| CA-13/14 | test_ca13_ca14_simulacion_inmutable; pruebas UI y evidencia preservada | Verificado |
| CA-15 | test_ca15_cargos_tcea_fechas; cargos de terceros | Verificado con convención referencial |
| CA-16 | test_ca16_pdf_trazable; PDF sintético renderizado con Poppler e inspeccionado | Local verificado |
| CA-17 | test_nueve_combinaciones y test_nueve_escenarios_identicos del Sprint 1 | Verificado |
| CA-18 | test_sesiones_aisladas_y_limpieza_evidencias y reinicio | Verificado |
| CA-19 | test_ca19_no_ejecutar_texto | Verificado |
| CA-20 | suite completa + arranque local Streamlit + navegador | Cloud pendiente de revisión/despliegue autorizado |

No se declara completo el hito de despliegue objetivo ni certificada la lectura OCR
automática. Ver `LIMITACIONES.md` antes de aprobar el PR.

## Manual de prueba con datos ficticios

1. Instalar `requirements.txt`; ejecutar `python -m unittest discover -s tests -v`.
2. Arrancar `python -m streamlit run app.py`. Cargar caso esperado y abrir Analizar.
   Cuota S/ 938.46, DTI 35.38%, saldo S/ 861.54: RN-03 debe estar activa.
3. Seleccionar vehicular/hipotecario/empresarial: debe decir no evaluable; el módulo
   estratégico permanece disponible.
4. Usar `docs/evidencias-sprint2/boleta-sintetica-2026-08.pdf` y los de septiembre/octubre.
   Confirmar archivos sintéticos, leer y revisar cada página/frase. Ningún candidato
   entra al promedio antes de confirmar. Confirmar visualmente los tres importes.
5. Declarar ingreso 3300, historial insuficiente, sin mora inferida: promedio 3300.
   Declarar 4500: discrepancia pendiente. Seleccionar fuente documental, justificar y
   registrar aclaración: usar 3300. Cambiar un ingreso invalida esa aclaración.
6. Cargar imagen sintética: si Tesseract no está disponible, la lectura lo indica.
   Añadir transcripción manual, indicar fecha/origen y confirmar explícitamente.
7. Duplicar una boleta y confirmar: debe solicitar descarte justificado del duplicado.
8. Simular 24 meses y caída 20%; comprobar cuota menor e ingreso 2640 sobre base 3300.
   El formulario base mantiene sus importes. Comparar gráficos y CSV.
9. Registrar seguro mensual 20 y comisión inicial 100. Pago total = cuota +20;
   TCEA pendiente hasta confirmar fechas, desembolso y completitud de cargos.
10. Generar PDF base y de simulación. Revisar fecha, versión, fuentes, estado,
    cifras, cargos, alertas, supuestos y cronograma. No incluye archivos crudos.
11. Reiniciar: campos, evidencias, previews, PD/LGD y observaciones vacíos.
    Otra sesión de navegador no recibe datos del caso anterior.

## Comprobación financiera independiente

Para S/ 10,000 / 12 meses / TEA 25%, cálculo con Decimal de 40 dígitos:
cuota = `938.4632560753013665945355393611184337160`.
Primera cuota: interés ≈187.6926512, amortización ≈750.7706049, saldo ≈9249.2293951.
Total intereses ≈1261.5590729; saldo final interno 0. A TEA cero, cuota =10000/12,
interés total 0. Se comparó contra el motor del Sprint 1 y los tests de referencia.

## Evidencias y reproducción

`python scripts/generar_evidencias_demo.py` genera únicamente fixtures sintéticas y
un PDF de demostración. Los archivos de QA están en `docs/evidencias-sprint2/`.
Las capturas del navegador se obtienen con `scripts/capturar_sprint2.cjs` contra
`localhost:8502` y Playwright (herramienta de desarrollo, no dependencia de la app).
El entorno de prueba usa Python 3.12 y Streamlit 1.67.0.

Resultado local: **56 pruebas aprobadas**, con regresiones del Sprint 1, PDF, imagen
sintética, estados, límites, fallback, TCEA, simulación y sesiones aisladas.
Navegador Edge sin interfaz visible: arranque, caso esperado, indicadores y carga de
tres PDF sintéticos con confirmación pendiente verificados. Las capturas muestran
el análisis y el paso de confirmación; los cuatro folios del PDF se revisaron
renderizados con Poppler, sin recortes ni solapamientos.

No se despliega ni fusiona automáticamente. Después de revisión, el responsable
puede desplegar la rama aprobada en Community Cloud con entrada `app.py`, Python
3.11+ y dependencias gratuitas. Verificar allí CA-20 antes de cerrar el Sprint.
