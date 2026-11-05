"""WHY -- the pack's own "POR QUE PODRIA DEJAR DE FUNCIONAR" list.

Transcribed from suite_flow.md, which is the pack's own rendered output. It is
part of their deliverable contract ("Todo reporte termina con POR QUE PODRIA
DEJAR DE FUNCIONAR"), so it is reproduced rather than reinvented.
"""
WHY = [
    "El edge puede ser un artefacto del periodo muestreado: un solo regimen de volatilidad/tendencia no prueba robustez.",
    "Los costos (comision, slippage, funding) son parametros asumidos; con otro tier o liquidez peor el edge neto desaparece.",
    "Barras de 5 min con entrada al cierre ignoran la latencia real y el impacto en el libro; el slippage real es no lineal en tamano.",
    "El modelo se reajusta periodicamente: si la relacion flujo->retorno cambia (estructura de mercado, competencia), la calibracion se degrada.",
    "Con senal debil (AUC cercano a 0.5) basta un pequeno error de calibracion para convertir edge positivo en negativo tras costos.",
    "Backtest sobre una sola moneda/exchange: sin validacion cruzada entre activos, el riesgo de sobreajuste por seleccion es alto.",
    "Eventos de cola (liquidaciones en cascada, gaps, caidas de API, funding extremo) no estan bien representados en la muestra.",
]
