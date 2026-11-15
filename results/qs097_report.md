# QS-097 "Cross-asset confirmation" — veredicto de campaña

## VEREDICTO: KILLED — cero de veinticuatro celdas pasa la batería estándar

La tarjeta especificaba Donchian(20) con confirmación cross-asset (BTC y ETH
sobre su EMA(50) y dos de los otros perps sobre la suya), salida por mínimo de
diez barras o confirmación perdida, stop de dos ATR, máximo ciento cincuenta
barras, un episodio por señal. Portada fiel (`code/qs097_engine.py`) con el
ejecutor del catálogo importado por identidad (G1 sizing, G3 funding real,
stop primero con fills de hueco), auditada con veinticinco respuestas
conocidas ANTES de ningún dato real (la primera corona de fallos fue toda del
test: geometrías que nunca rompían el canal, el low del burst dentro de la
ventana de diez, y un umbral de confirmación heredado del default). Cada
celda se juzgó aislada con `bt.py one` (REGLA 1): costes de once puntos
básicos por ida y vuelta, funding real cobrado en asentamientos, control de
coste cero y bootstrap propios dentro de cada artefacto.

Las ventanas activas empiezan todas en 2025-06-01 (aproximadamente): la regla
no-trade por datos stale del panel veta todo hasta que HYPE — el activo más
joven del universo — tiene historia y EMA(50) calientes. Los tercios, el OOS
setenta-treinta y la concentración se miden dentro de esa ventana activa
(veinticuatro mil barras aproximadas en 1h, cincuenta mil en 15m).

## Las veinticuatro celdas (run_id citado por línea; costes 11 bps RT)

1h, variante long:

- BTCUSDT `f9ac0714adfcb2a4` — PF 0.807, net -11.04%, n 184, tercios 1/3 → FAIL
- ETHUSDT `8631be9d3eea772e` — PF 1.085, net +5.16%, n 173, tercios 2/3, conc 516.2% → FAIL
- SOLUSDT `a0e52120fc8bb050` — PF 0.920, net -6.08%, n 181, tercios 2/3 → FAIL
- HYPEUSDT `6f5ec1d20c40a815` — PF 1.181, net +10.55%, n 162, tercios 2/3, conc 321.0%, IC [-16.51, +35.64] → FAIL
- SUIUSDT `278592daf188a5d8` — PF 0.979, net -1.61%, n 150, tercios 1/3 → FAIL
- JUPUSDT `58d3c47abbc41ee5` — PF 0.849, net -6.98%, n 158, tercios 2/3 → FAIL

1h, variante two_side (hipótesis separada según la tarjeta):

- BTCUSDT `2053d078008e9ba3` — PF 0.902, net -9.22%, n 332, tercios 0/3 → FAIL
- ETHUSDT `c07e26b442263679` — PF 1.234, net +25.99%, n 306, tercios 2/3, OOS PF 1.407, conc 154.3%, IC [-7.14, +26.58] → FAIL (concentración y significancia)
- SOLUSDT `58e34a754c1a0d61` — PF 0.844, net -16.95%, n 344, tercios 1/3 → FAIL
- HYPEUSDT `2bb4435b71808cbb` — PF 0.925, net -6.09%, n 309, tercios 2/3 → FAIL
- SUIUSDT `69d9e9bb940152d6` — PF 1.192, net +26.08%, n 295, tercios 2/3, OOS PF 0.852, conc 217.8% → FAIL
- JUPUSDT `c44289c67cc1cd3b` — PF 0.846, net -13.46%, n 326, tercios 0/3 → FAIL

15m (doce celdas, todas FAIL): BTC `7bfdf5fec22dc920`/`026417912bb9d1e7`,
ETH `9f388abb917f9538`/`d538a00e5e379317`, SOL `d5be17501172e803`/
`2b37499cbdb014f2`, HYPE `29e0c4dfb1e15619`/`19c528aa2536da3e`,
SUI `3d5e11570a5b19d5`/`89c38757396ebb7a`, JUP `415317676d8da03d`/
`3a9dfc9747761b52` — PF entre 0.561 y 0.917, net entre -15.80% y -24.31%,
tercios cero de tres en las doce. La propia tarjeta lo anticipaba
("costs matter most"); aquí está medido.

## Por qué muere (medido dentro de los artefactos)

- **Costes**: en la mejor celda (ETH 1h two_side) el control de coste cero da
  +49.90% y con los costes del repo queda en +25.99% — un drag de +23.91pp
  sobre trescientos seis trades. En 15m el drag se come el libro entero.
- **Concentración**: el mejor quinto de trades es el 154.3% del PnL en ETH
  two_side, el 217.8% en SUI, el 321.0% en HYPE long y el 516.2% en ETH long.
  El patrón de siempre: unos cuantos aciertos sosteniendo el libro.
- **Significancia propia**: ningún IC bootstrap excluye el cero (el más
  cercano, ETH two_side: [-7.14, +26.58], P de media menor o igual a cero
  0.157).
- **La confirmación cross-asset no arregla el breakout**: frente a los
  breakouts de un solo activo ya medidos en el repo, el filtro quita trades y
  no mejora el PF por trade; en BTC y JUP empeora el net.

## Notas de ejecución del porte

- El panel completo (seis perps) se hashea en cada celda: la confirmación
  necesita a todos aunque el libro sea de un símbolo.
- Ventana activa: las métricas (tercios, OOS, concentración) se miden desde
  la primera barra con el panel completo y caliente — la lección xsf
  aplicada; el return es el del libro completo (plano antes de la ventana).
- Funding real cobrado: entre setenta y cuatro y ciento doce dólares por
  libro en la ventana activa, consistente con un libro que pasa parte del
  tiempo en el mercado.

## Próximo paso según doctrina

Ninguna re-corrida lo revive. Si la hipótesis cross-asset sigue viva para el
usuario, los candidatos declarados de esta familia no existen — la puerta es
la misma de siempre: un registro forward en papel, o una variante con costes
de maker que el ejecutor actual no certifica en OHLC (regla de fill-model).
