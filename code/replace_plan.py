p = r"C:\Users\Lenovo\trading-engines\tradingview-bridge\telegram-bot.mjs"
lines = open(p, encoding="utf-8").read().splitlines(keepends=True)
# Replace 1-based lines 303..338 (let plan ... neutral closing brace)
assert lines[302].strip() == "let plan = '';", lines[302][:40]
assert lines[336].strip().startswith("plan = `"), lines[336][:40]
assert lines[337].strip() == "}", lines[337][:40]
new_block = """  let plan = '';
  const p = Number(price) || 0;
  // REAL (audit 2026-09-21): canonical builder math, same as
  // atas-bridge/orderflow_calls.build_plan (entry ±0.05%, stop 0.85×med,
  // T1 ≥ 1.5×stop, T2 1.8×med×p90/med). A plan posts to /calls ONLY when
  // fires = vetoes pass + trigger + 3-poll persistence + cost gate.
  // Legacy ±0.15%/T1-1.16x geometry is gone; so is band gating (R10 v3.3).
  const _planBody = (direction, entryLow, entryHigh, sl, t1, t2) => {
    const tag = direction === 'long' ? '🟢 PLAN LONG' : '🔴 PLAN SHORT';
    const inv = direction === 'long' ? 'cierre < SL' : 'cierre > SL';
    import('http').then(h=>{
      const body=JSON.stringify({symbol:ticker,direction,entry_low:Number(entryLow.toFixed(2)),entry_high:Number(entryHigh.toFixed(2)),sl:Number(sl.toFixed(2)),t1:Number(t1.toFixed(2)),t2:Number(t2.toFixed(2)),note:`tg-bot live-anchored ${p.toFixed(2)}`});
      const req=h.request({hostname:'127.0.0.1',port:8000,path:'/calls',method:'POST',headers:{'Content-Type':'application/json'}},()=>{});
      req.on('error',()=>{}); req.write(body); req.end();
    }).catch(()=>{});
    return `${tag}\\nEntry: ${entryLow.toFixed(2)} – ${entryHigh.toFixed(2)} (live $${p.toFixed(2)} ±0.05%)\\nStop: ${sl.toFixed(2)} (invalida ${inv})\\nT1: ${t1.toFixed(2)} | T2: ${t2.toFixed(2)} (med ${expMed.toFixed(2)}% / p90 ${expP90.toFixed(2)}% · T1/SL ${_t1OverSl.toFixed(2)} · cost ${_costR.toFixed(3)}R)`;
  };
  if (fires && compScore > 0) {
    plan = _planBody('long', _mid - _half, _mid + _half, (_mid - _half) - _slD, (_mid + _half) + _t1D, (_mid + _half) + _t2D);
    try { await lxRequest(`/calls`); } catch(_){}
  } else if (fires && compScore < 0) {
    plan = _planBody('short', _mid - _half, _mid + _half, (_mid + _half) + _slD, (_mid - _half) - _t1D, (_mid - _half) - _t2D);
    try { await lxRequest(`/calls`); } catch(_){}
  } else {
    const why = [];
    if (!tradePlanAllowed) why.push(...blockReasons);
    if (Math.abs(compScore) < MIN_SCORE) why.push(`trigger ${Math.abs(compScore).toFixed(1)}<${MIN_SCORE}`);
    if (!persistOk) why.push(`persist [${_streak.join(',')}]`);
    why.push(...gateRejects);
    plan = `🟡 SIN PLAN — ${why.join(' · ') || 'sin dirección'}`;
  }
"""
lines[302:338] = [new_block]
open(p, "w", encoding="utf-8").write("".join(lines))
print("plan block replaced OK")
