# s101 — STRATEGIES 101-150 (adjunto del 13 de noviembre de 2026)

## VEREDICTO: KILLED — cero de treinta y siete celdas pasa la batería de
pantalla; el patrón dominante es la ruina por costes en intradía

Pack de cincuenta prompts (fuente de registro byte-idéntica
`code/prompts_101_150.txt`, sha ba1b3491…; pre-registro
`results/s101_pre_registration.md` con el triaje: treinta y siete celdas
corren, trece se saltan por NO-DATA bajo la regla #19 del propio pack).
Motor `code/s101_engine.py` sobre el núcleo `Book` auditado de la campaña
p100. Convenciones declaradas en cada artefacto: señal al cierre, entrada
en la apertura siguiente, stop-first, costes repo uniformes (cinco bps de
comisión más medio de deslizamiento por lado), riesgo cero coma cinco por
ciento por trade, contadores diarios del pack (tres pérdidas; seis trades
en libros de un-tres minutos), funding en settlements reales para los
perps (NVDA/SPCX sin fichero: declarado), setenta-treinta cronológico sin
purga. La criba es la batería estándar de casa vía bt.py.

Verificación: los treinta y siete artefactos verifican bit-for-bit
(`results/_s101_verify.txt`). La corrida limpia duró mil ochocientos
veintiún segundos tras el pre-vuelo `code/_s101_preflight.py`
(treinta y siete de treinta y siete celdas OK en slices de sesenta días),
que sustituyó las tres pasadas fallidas previas de la sesión.

## Las treinta y siete celdas (run_id citado por línea)

Las celdas ordenadas por id; veredicto de pantalla por línea.

| # | run_id | net % | PF | OOS PF | n |
|---|---|---|---|---|---|
| 101 | `e7b92b1b89d5f276` | -100.00 | 0.1415 | 0.1430 | 5207 |
| 102 | `c506fd0adbd4e600` | -95.06 | 0.5039 | 0.4704 | 987 |
| 103 | `5f7997379c6c67b2` | -100.00 | 0.0217 | 0.0193 | 2307 |
| 104 | `45377cf8d76cf870` | -2.74 | 0.5071 | 0.6019 | 36 |
| 105 | `cb2a8bf973407629` | -100.00 | 0.4224 | 0.4098 | 5813 |
| 106 | `1d9c8193435ba9ae` | -92.21 | 0.1468 | 0.0987 | 401 |
| 107 | `aa8d97985e1ddce0` | -99.99 | 0.1677 | 0.0911 | 1789 |
| 108 | `7c28664df39c6858` | -100.00 | 0.0444 | 0.0443 | 2375 |
| 109 | `4432dede2f8f32e6` | -17.21 | 0.3469 | 0.2930 | 64 |
| 110 | `df1d38071d9c61e4` | -100.00 | 0.2131 | 0.2200 | 2319 |
| 112 | `ef1b509946ff13ed` | -99.36 | 0.0000 | 0.0000 | 689 |
| 115 | `09db212c3fa7b950` | -99.67 | 0.6875 | 0.6152 | 3394 |
| 116 | `f2be1b3c0ddaf570` | -100.00 | 0.7823 | 0.5285 | 8502 |
| 117 | `b3d22f048e9805dd` | -100.00 | 0.2795 | 0.0593 | 5155 |
| 118 | `34f5f0a4b8f84155` | -99.37 | 0.1539 | 0.0516 | 2516 |
| 119 | `c75546575962bb1b` | -34.66 | 0.2047 | 0.0516 | 92 |
| 120 | `ba0f14004fbc8c60` | -99.99 | 0.5493 | 0.3646 | 2821 |
| 121 | `3d91371a976554bc` | -32.36 | 0.6764 | 0.5694 | 282 |
| 122 | `863024b993d365a8` | -90.61 | 0.2471 | 0.2139 | 608 |
| 123 | `210e2b955910a9b1` | -96.01 | 0.5641 | 0.5466 | 1600 |
| 124 | `f68cf96fba165cbb` | -70.65 | 0.3466 | 0.4758 | 390 |
| 125 | `aa48efc00c3ae007` | -71.07 | 0.3686 | 0.2759 | 363 |
| 126 | `c610f745c09ac71f` | -99.98 | 0.0657 | 0.0699 | 1561 |
| 127 | `0e2eba0dc0298fd2` | -92.04 | 0.5803 | 0.4582 | 1258 |
| 128 | `be7b0959b4f22310` | 0.00 | 0.0000 | 0.0000 | 0 |
| 129 | `e5dcae9eb4569512` | -100.00 | 0.3264 | 0.1600 | 2157 |
| 130 | `fbef16f95de51bd0` | -96.95 | 0.2503 | 0.1701 | 805 |
| 131 | `0acb2b9fd49dd1e4` | -99.68 | 0.5447 | 0.4095 | 2819 |
| 133 | `18937ea1d7cf3e82` | -24.54 | 0.7757 | 0.7088 | 297 |
| 134 | `0c2ce8f1f84a11ea` | 227.37 | 1.0249 | 0.8110 | 6089 |
| 135 | `d82c834934c0bdf0` | -99.51 | 0.5160 | 0.5087 | 3447 |
| 138 | `46a8ce34bf84ad03` | -12.65 | 0.8684 | 0.9656 | 297 |
| 139 | `659b5fe9c4f617d4` | -99.97 | 0.5234 | 0.4749 | 3014 |
| 140 | `07cce0ab15f5cf3e` | -88.43 | 0.5432 | 0.4331 | 909 |
| 141 | `99ef4ec447372fc0` | -22.62 | 0.5750 | 0.2814 | 252 |
| 144 | `9c63f85f4b6aeac8` | -32.97 | 0.0557 | 0.0081 | 67 |
| 150 | `ba5ca6d345c7e023` | -9.09 | 0.0000 | 0.0000 | 17 |

Bandera por celda (una línea por run_id):

- `e7b92b1b89d5f276`: FAIL — ruina del libro
- `c506fd0adbd4e600`: FAIL — pérdida neta
- `5f7997379c6c67b2`: FAIL — ruina del libro
- `45377cf8d76cf870`: FAIL — pérdida neta
- `cb2a8bf973407629`: FAIL — ruina del libro
- `1d9c8193435ba9ae`: FAIL — pérdida neta
- `aa8d97985e1ddce0`: FAIL — ruina del libro
- `7c28664df39c6858`: FAIL — ruina del libro
- `4432dede2f8f32e6`: FAIL — pérdida neta
- `df1d38071d9c61e4`: FAIL — ruina del libro
- `ef1b509946ff13ed`: FAIL — ruina del libro
- `09db212c3fa7b950`: FAIL — ruina del libro
- `f2be1b3c0ddaf570`: FAIL — ruina del libro
- `b3d22f048e9805dd`: FAIL — ruina del libro
- `34f5f0a4b8f84155`: FAIL — ruina del libro
- `c75546575962bb1b`: FAIL — pérdida neta
- `ba0f14004fbc8c60`: FAIL — ruina del libro
- `3d91371a976554bc`: FAIL — pérdida neta
- `863024b993d365a8`: FAIL — pérdida neta
- `210e2b955910a9b1`: FAIL — pérdida neta
- `f68cf96fba165cbb`: FAIL — pérdida neta
- `aa48efc00c3ae007`: FAIL — pérdida neta
- `c610f745c09ac71f`: FAIL — ruina del libro
- `0e2eba0dc0298fd2`: FAIL — pérdida neta
- `be7b0959b4f22310`: FAIL — pérdida neta
- `e5dcae9eb4569512`: FAIL — ruina del libro
- `fbef16f95de51bd0`: FAIL — pérdida neta
- `0acb2b9fd49dd1e4`: FAIL — ruina del libro
- `18937ea1d7cf3e82`: FAIL — pérdida neta
- `0c2ce8f1f84a11ea`: FAIL — pérdida neta
- `d82c834934c0bdf0`: FAIL — ruina del libro
- `46a8ce34bf84ad03`: FAIL — pérdida neta
- `659b5fe9c4f617d4`: FAIL — ruina del libro
- `07cce0ab15f5cf3e`: FAIL — pérdida neta
- `99ef4ec447372fc0`: FAIL — pérdida neta
- `9c63f85f4b6aeac8`: FAIL — pérdida neta
- `ba5ca6d345c7e023`: FAIL — pérdida neta

## Lectura por familias

- **Escalping uno-tres minutos (103, 109, 119, 126, 129 y los spreads de
  tres minutos): ruina.** La aritmética de la casa otra vez: miles de
  trades con once bps de ida y vuelta consumen el libro entero; los
  contadores diarios del pack (seis trades por día) limitaron la frecuencia
  y aun así la ruina llegó.
- **Estructura / traps de cinco-quince minutos: pérdidas del veinte al
  cien por ciento** con PF neto entre cero coma cero dos y cero coma
  nueve — ningún bloque alcanza el uno.
- **La mejor celda del pack** es la 138 (stop-run continuation en
  quince minutos): PF neto cero coma ochenta y seis, menos doce coma seis
  por ciento — pierde, y falla la batería igualmente.
- **La única con PF bruto por encima de uno** es la 134 (Renko en SUI, PF
  bruto uno coma cero dos) y aun así OOS PF cero coma ochenta y uno con
  sesenta y siete por ciento de pérdida OOS.
- **128 (wick ≥ 2 ATR en HYPE 5m): cero trades en toda la ventana** —
  el umbral del prompt es casi imposible por construcción; se declara
  medido-muerto tal cual el prompt lo pide.
- **NVDA/SPCX**: ventanas de cuatro-seis meses (frágiles por la regla #18
  del propio pack); ambas pierden.

## Los trece NO-DATA (regla #19 del pack: no se finge)

111 liquidaciones; 113 open interest; 114 spot ETH ausente; 132 calendario
macro; 136 tick data; 137 order book; 142 NVDA 1m ausente; 143 NVDA 3m
(necesita 1m); 145 SMH ausente; 146 SPCX 1m ausente; 147 SPY ausente
(símbolo disparador); 148 VIX ausente; 149 breadth ausente.

## Veredicto

**Campaña s101: KILLED — cero de treinta y siete celdas supera la batería
de pantalla; no hay etapas posteriores (WF / neighborhood) que correr.** El
patrón es el mismo que el resto del corpus: filo bruto ausente o marginal
(ninguna celda alcanza PF bruto muy por encima de uno salvo la Renko en el
límite) y la muralla de once bps convierte cada familia intradía en ruina
compuesta. Sin transferencia de fallo entre hermanas (REGLA 1): cada celda
falleció sobre sus propios artefactos.

