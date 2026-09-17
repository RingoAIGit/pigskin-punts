"""Render + function verification for the Pig Skin Punts site.

Checks every page at desktop and mobile widths, then exercises the bet-entry
form for real (fill, build, copy) rather than trusting the markup.

Run: ~/.hermes/hermes-agent/venv/bin/python verify_render.py [base_url]
"""
import asyncio
import base64
import json
import os
import sys

sys.path.insert(0, "/Users/cerebral/.hermes/skills/research/browser-automation/scripts")
from cdp_lib import CDP, connect, new_tab  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8899/"
OUT = "/tmp/psp"
PAGES = ["index.html", "bets.html", "results.html", "method.html",
         "week-01.html", "protocol.html"]

PROBE = r"""
(() => {
  const out = {clipped: [], overflow: [], rows: {}, strip: 0, gates: 0, svg: 0};
  document.querySelectorAll('p,h1,h2,h3,h4,li,td,th,dt,dd,label,.stat .value,.wordmark,.tagline,.chip,.edge,.field input,.field select')
    .forEach(el => {
      if (el.scrollWidth > el.clientWidth + 1)
        out.clipped.push({t:(el.tagName+': '+(el.textContent||el.value||'').trim().slice(0,40)), sw:el.scrollWidth, cw:el.clientWidth});
    });
  document.querySelectorAll('main *').forEach(el => {
    if (el.closest('.table-wrap') || el.closest('pre') || el.closest('.spikes') || el.closest('.chart')) return;
    if (el.scrollHeight > el.clientHeight + 3 && getComputedStyle(el).overflowY !== 'visible' && el.clientHeight > 0)
      out.overflow.push({t:(el.className||el.tagName), sh:el.scrollHeight, ch:el.clientHeight});
  });
  ['tonightTable','edgesTable','keyTable','betsTable','resultsTable','passesTable','resultsTeaser','boardTable'].forEach(id => {
    const e = document.getElementById(id);
    if (e) out.rows[id] = e.querySelector('table') ? e.querySelectorAll('tbody tr').length : 'empty-state';
  });
  out.strip = document.querySelectorAll('#recordStrip .stat').length;
  out.gates = document.querySelectorAll('.gate-row').length;
  out.svg = document.querySelectorAll('#bankrollChart svg').length;
  out.failed = document.body.innerText.indexOf('failed to load') >= 0 ||
               document.body.innerText.indexOf('failed to load') >= 0;
  out.docW = document.documentElement.scrollWidth; out.winW = window.innerWidth;
  return JSON.stringify(out);
})()
"""

FORM = r"""
(() => {
  const set=(id,v)=>{const e=document.getElementById(id); e.value=v;
    e.dispatchEvent(new Event('input',{bubbles:true}));
    e.dispatchEvent(new Event('change',{bubbles:true}));};
  // The game field is a select filled from slate.json, which is rebuilt every deploy, so
  // a hardcoded game name silently stopped matching the slate and the probe was building
  // a line with "(game?)" in it — a check that no longer checked. Take a real option.
  const gs = document.getElementById('f-game');
  const opt = Array.from(gs.options).find(o => o.value && !o.disabled);
  set('f-game', opt ? opt.textContent.trim() : '');
  set('f-sel','Rams -3.5');
  set('f-odds','1.88'); set('f-stake','5.00'); set('f-note','render check probe');
  document.getElementById('betBuild').click();
  const mail = document.getElementById('betMail').getAttribute('href') || '';
  const line = document.getElementById('betLine').textContent;
  return JSON.stringify({
    game: opt ? opt.textContent.trim() : null,
    hidden: document.getElementById('betOut').hidden,
    line: line,
    mailOk: mail.indexOf('mailto:emailringoai@gmail.com') === 0 && mail.indexOf('1.88') > 0,
    placeholder: line.indexOf('(game?)') >= 0,
    mailLen: mail.length
  });
})()
"""


async def shot(cdp, name):
    r = await cdp.cmd("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": True})
    path = os.path.join(OUT, name)
    with open(path, "wb") as f:
        f.write(base64.b64decode(r["data"]))
    return path


async def main():
    os.makedirs(OUT, exist_ok=True)
    page = new_tab("about:blank")
    ws = await connect(page["webSocketDebuggerUrl"])
    cdp = CDP(ws)
    await cdp.cmd("Runtime.enable")
    await cdp.cmd("Page.enable")

    for width, label in ((1320, "desktop"), (390, "mobile")):
        await cdp.cmd("Emulation.setDeviceMetricsOverride",
                      {"width": width, "height": 900, "deviceScaleFactor": 1,
                       "mobile": width < 500})
        for p in PAGES:
            await cdp.navigate(BASE + p)
            await asyncio.sleep(2.0)
            raw = await cdp.eval_js(PROBE)
            try:
                d = json.loads(raw)
            except Exception:
                print(f"[{label}] {p:15s} PROBE FAILED {str(raw)[:120]}")
                continue
            flags = []
            if d["docW"] > d["winW"]:
                flags.append(f"H-DRAG {d['docW']}>{d['winW']}")
            if d["clipped"]:
                flags.append(f"CLIP {len(d['clipped'])}")
            if d["overflow"]:
                flags.append(f"OVFL {len(d['overflow'])}")
            if d["failed"]:
                flags.append("LOAD-FAIL")
            print(f"[{label}] {p:15s} strip={d['strip']} gates={d['gates']} svg={d['svg']} "
                  f"rows={d['rows']} {' '.join(flags) or 'OK'}")
            for c in d["clipped"][:3]:
                print(f"      clip: {c['t']}  {c['sw']}>{c['cw']}")
            for o in d["overflow"][:3]:
                print(f"      ovfl: {o['t']}  {o['sh']}>{o['ch']}")

    # --- functional test of the bet form (mobile, thumb-sized) ---
    await cdp.navigate(BASE + "bets.html")
    await asyncio.sleep(2.0)
    print("\n--- bet form ---")
    print(await cdp.eval_js(FORM))
    await asyncio.sleep(1.0)
    msg = await cdp.eval_js("document.getElementById('betMsg').textContent")
    print("after copy click:", msg)
    print("form fields present:", await cdp.eval_js(
        "document.querySelectorAll('#betForm .field').length"))

    # --- screenshots ---
    await cdp.cmd("Emulation.setDeviceMetricsOverride",
                  {"width": 1320, "height": 900, "deviceScaleFactor": 1, "mobile": False})
    for p in ("index.html", "bets.html", "results.html"):
        await cdp.navigate(BASE + p)
        await asyncio.sleep(2.2)
        print("shot:", await shot(cdp, p.replace(".html", "-v2.png")))
    await cdp.close()

asyncio.run(main())
