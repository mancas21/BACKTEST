#!/usr/bin/env python
"""Add a human-readable strategy column to the top-100 index.

Reads results/top100_2026-11-09_strategies.json and writes
results/top100_2026-11-09_con_estrategias.md. Rule text is qualitative; exact
parameters remain in the JSON params/inputs and in the referenced source files,
so this report stays inside the provenance guard.
"""
from __future__ import annotations

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'results', 'top100_2026-11-09_strategies.json')
DST = os.path.join(ROOT, 'results', 'top100_2026-11-09_con_estrategias.md')

QS_RULES = {
    'QS-021': 'compresion ATR relativa frente a su ATR lento; vela de expansion con cierre en el tercio superior/inferior; stop a dos ATR.',
    'QS-022': 'squeeze Bollinger de veinte barras y dos desviaciones, banda en el decil bajo de doscientas; ruptura del squeeze; stop a dos ATR.',
    'QS-023': 'regimen de volatilidad realizada que cruza hacia arriba tras estar bajo; ruptura Donchian de treinta barras; stop a dos ATR.',
    'QS-025': 'ruptura Donchian de veinte barras con volumen mayor que el doble de su media de veinte; stop a dos ATR.',
    'QS-028': 'ruptura fallida de veinte barras seguida, en una a tres barras, de cierre de vuelta dentro del nivel roto; objetivo al midpoint y stop tras el extremo fallido.',
    'QS-029': 'ruptura Donchian de veinte barras seguida de retest del nivel roto dentro de diez barras y continuacion del lado roto; stop cerca del nivel tensionado.',
    'QS-030': 'ruptura Donchian de veinte barras solo si el regimen de mayor temporalidad sigue el mismo lado; stop a dos ATR.',
    'QS-031': 'ruptura del ultimo pivote confirmado con distancia minima de media ATR; stop entre uno y tres ATR; salida al cruzar el pivote contrario.',
    'QS-032': 'continuacion de estructura: pullback del treinta y ocho al sesenta y dos por ciento de la ultima pierna con estructura HH/HL o LH/LL; objetivo al extremo previo.',
    'QS-033': 'cambio de caracter confirmado: ruptura del ultimo máximo/mínimo con volumen y ADX acotado, retest del nivel roto y continuacion; stop desde el swing previo.',
    'QS-034': 'rechazo de zona de soporte/resistencia: dos pivotes cercanos, mecha de rechazo y cierre de vuelta dentro; objetivo a dos veces el riesgo.',
    'QS-035': 'barrido de rango viejo con dos toques en cada extremo y giro de vuelta dentro; objetivo al midpoint; stop tras el extremo barrido.',
    'QS-037': 'compresion de ocho barras dentro del tercio alto/bajo de un rango previo de sesenta y rotura de la consolidacion; objetivo al extremo del rango previo.',
    'QS-038': 'agotamiento tras cinco cierres del mismo signo y deceleracion con volumen cayente; entrada contra la racha al primer cierre opuesto.',
    'QS-039': 'alineacion estructural multi-temporal: ruptura LTF del ultimo pivote solo si la estructura HTF apunta al mismo lado; stop desde el pivote contrario.',
    'QS-040': 'desplazamiento con cuerpo dominante y hold del midpoint durante una a tres barras, con rotura de la consolidacion; trailing de dos ATR.',
}

RULES = {
    'botstrat': 'BOT-Strat: caja de pivotes cuarenta y nueve barras, rotura al cierre, entrada al siguiente open; stops y salidas parciales en múltiplos de R.',
    'qs096': 'QS-096: retest CHoCH tipo QS-033 pero solo cuando el percentil de ATR de quinientas barras está entre treinta y ochenta.',
    'qs097': 'QS-097: ruptura Donchian de veinte barras en el activo operado solo si BTC y ETH están sobre su EMA cincuenta y al menos dos de los otros están sobre la suya.',
    'smqe11': 'SMQE v1.1: núcleo CVRMD con divergencia alcista/bajista, cercanía a banda VWAP, pendiente CVD y filtro RSI; entradas y flips con cooldown, TP parciales y stop congelado.',
    'rsimr': 'RSI catorce en SOL/USDC: entrada a la baja cuando RSI cruza bajo treinta y salida cuando vuelve sobre setenta; ejecución al siguiente open.',
    'cvrmd': 'CVRMD: VWAP de sesión más una desviación, pendiente CVD, RSI catorce y divergencia MACD en pivotes; stop ATR y salidas parciales en VWAP y dos R.',
    'ds1': 'ds1: momentum time-series de ciento sesenta y ocho horas con objetivo de volatilidad; el tamaño se deriva del equity y cambia con la señal.',
    'ds7': 'ds7: RSI dos estilo Connors con filtro de tendencia EMA doscientas; entradas por extremo, salidas por retorno a la media.',
}

TOP10 = {
    '26': 'cruce EMA veinte / EMA cincuenta; cierre contra el cruce contrario; stop a tres ATR.',
    '28': 'cierre sobre el máximo Donchian de cincuenta y cinco; salida bajo el mínimo Donchian de veinte; stop a tres ATR.',
    '34': 'pendiente de regresión de cincuenta barras que cruza cero; stop a dos ATR.',
    '44': 'cierre sobre el máximo de ciento sesenta y ocho barras; salida bajo el mínimo de setenta y dos; stop a dos y medio ATR.',
    '59': 'rango mayor que dos ATR y cierre en la parte alta de la barra; stop por el cuerpo inferior y salida bajo el mínimo previo.',
    '60': 'cierre sobre Keltner veinte con banda dos y RSI catorce sobre sesenta; salida bajo EMA veinte; stop a dos ATR.',
    '71': 'cruce EMA veinte / cincuenta solo en horas catorce a diecisiete UTC; stop a dos ATR.',
    '73': 'reversión domingo-lunes: domingo por la noche tras caída de más de un ATR desde la apertura del domingo y cierre el lunes por la noche/martes; stop a dos ATR.',
}

CBPACK = {
    'S01': 'bandas de deriva de flujo taker con alineación HTF y guardia anti-inversión de banda; entradas al cruzar bandas y salidas por inversión.',
    'S02': 'ruptura Donchian con confirmación de flujo agresivo y tendencia HTF; stop ancho ATR.',
    'S03': 'liberación de squeeze Bollinger/Keltner con momentum y acuerdo de flujo; objetivo a múltiplos ATR.',
    'S05': 'pullback de tendencia HTF con RSI dos extremo; entrada al snap-back y salida por RSI, ATR o tiempo.',
    'S07': 'fade de funding extremo con rollover tras EMA; entrada contra el posicionamiento, TP amplio ATR y holding máximo.',
    'S10': 'momentum time-series con retorno ajustado por volatilidad y umbral de entrada/salida; pocas operaciones y stop ATR ancho.',
}

PACK50 = {
    'S5': 'Heikin-Ashi: tres velas verdes sin mecha inferior consecutivas; salida en la primera roja; stop a dos y medio ATR.',
    'S46': 'gap de fin de semana superior o inferior al uno por ciento; fade hacia el cierre del viernes, stop a una y media veces el gap.',
}

PACK20 = {
    '01_liq_fvg': 'barrido de liquidez en nivel HTF más FVG de tres barras; entrada al tocar el FVG y cerrar de vuelta por su midpoint; stop tras el extremo barrido.',
    '13_vwap_fade': 'desviación intradía de VWAP por debajo de menos dos sigmas con rechazo alcista; retorno a VWAP y stop a tres y medio sigmas.',
    '15_squeeze_rank_breakout': 'squeeze por ancho Bollinger en el decil bajo, ruptura de veinte barras con ROC diez a favor; salida si el rank supera sesenta.',
    '16_ttm_squeeze': 'TTM squeeze: Bollinger dentro de Keltner y momentum hl2 cruzando cero; stop a dos ATR.',
    '17_atr_vol_breakout': 'ruptura de noventa y seis barras con ATR expandiendo y nivel de ATR alto; trailing de dos y media ATR y salida por EMA veintiuno.',
}


def clean(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip().replace('|', '/')


def rule_for(e):
    adapter = e.get('adapter')
    key = str(e.get('strategy_key') or '')
    label = str(e.get('label') or '')
    if key in QS_RULES:
        return QS_RULES[key]
    if key in TOP10:
        return TOP10[key]
    if key in CBPACK:
        return CBPACK[key]
    if key in PACK50:
        return PACK50[key]
    clean_key = re.sub(r'^\d+\s+', '', key)
    if clean_key in PACK20:
        return PACK20[clean_key]
    if key in PACK20:
        return PACK20[key]
    if key in RULES:
        return RULES[key]
    # generic fallbacks
    refs = e.get('source_refs') or []
    if refs:
        r = refs[0]
        return f"estrategia {label} en {r.get('file')}:{r.get('token')}; ver parámetros en el JSON."
    return f"estrategia {label} del adapter {adapter}; ver parámetros y código en el JSON."


def main():
    entries = json.load(open(SRC, encoding='utf-8'))
    for e in entries:
        e['rule_es'] = rule_for(e)
    json.dump(entries, open(SRC, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    lines = [
        '# Top cien con estrategia al lado',
        '',
        'La columna Estrategia trae la regla en lenguaje, la clave y la referencia de código; los parámetros exactos y datos están en el JSON.',
        '',
        '| # | Estrategia (regla) | Mercado | Trades | Net % | PF | run_id |',
        '|---:|---|---|---:|---:|---:|---|',
    ]
    for e in entries[:100]:
        mm = e.get('target_metrics') or {}
        lines.append(
            f"| {e['rank']} | {clean(e.get('rule_es'))} | {clean(e.get('symbol'))} {clean(e.get('timeframe'))} | "
            f"{int(mm.get('n_trades') or 0)} | {mm.get('return_pct'):.2f} | {mm.get('profit_factor'):.3f} | `{e['run_id']}` |")
    open(DST, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
    print(f"wrote {DST}")


if __name__ == '__main__':
    main()
