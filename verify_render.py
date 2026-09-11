"""Render verification for the Pig Skin Punts site.

Drives the local headless Chrome on :9223, loads each page at desktop and mobile
widths, runs the overflow / clipping / data-render probe, and writes screenshots.

Run: ~/.hermes/hermes-agent/venv/bin/python verify_render.py
"""
import asyncio
import base64
import json
import os
import sys
import urllib.request

sys.path.insert(0, "/Users/cerebral/.hermes/skills/research/browser-automation/scripts")
from cdp_lib import CDP, connect, new_tab  # noqa: E402

BASE = "http://127.0.0.1:8899/"
OUT = "/tmp/psp"
PAGES = ["index.html", "week-01.html", "method.html", "protocol.html"]

PROBE = r"""
(() => {
  const out = {clipped: [], overflow: [], rows: {}, jsErr: !!window.__jsErr};
  document.querySelectorAll('p,h1,h2,h3,h4,li,td,th,dt,dd,.stat .value,.wordmark,.tagline,.chip,.edge,.seal .hash,.spike .val').forEach(el => {
    if (el.scrollWidth > el.clientWidth + 1)
      out.clipped.push({t:(el.tagName+': '+el.textContent.trim().slice(0,44)), sw:el.scrollWidth, cw:el.clientWidth});
  });
  document.querySelectorAll('main *').forEach(el => {
    if (el.closest('.table-wrap') || el.closest('pre') || el.closest('.spikes')) return;
    if (el.scrollHeight > el.clientHeight + 3 && getComputedStyle(el).overflowY !== 'visible' && el.clientHeight > 0)
      out.overflow.push({t:(el.className||el.tagName), sh:el.scrollHeight, ch:el.clientHeight});
  });
  ['tonightTable','edgesTable','keyTable'].forEach(id => {
    const e = document.getElementById(id);
    out.rows[id] = e ? e.querySelectorAll('tbody tr').length : 'MISSING';
  });
  const sp = document.getElementById('spikes');
  out.rows.spikes = sp ? sp.querySelectorAll('.spike').length : 'MISSING';
  out.rows.tonightGates = document.querySelectorAll('#tonightGates .gate-row').length;
  const gw = document.querySelector('#tonightGates .gate .bar'); 
  out.rows.firstBarLeft = gw ? gw.style.left : 'none';
  out.bodyChars = document.body.innerText.length;
  out.failed = document.body.innerText.indexOf('failed to load') >= 0;
  out.docW = document.documentElement.scrollWidth;
  out.winW = window.innerWidth;
  return JSON.stringify(out);
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
    from cdp_lib import connect as _c
    ws = await _c(page["webSocketDebuggerUrl"])
    cdp = CDP(ws)
    await cdp.cmd("Runtime.enable")
    await cdp.cmd("Page.enable")

    for width, label in ((1320, "desktop"), (390, "mobile")):
        await cdp.cmd("Emulation.setDeviceMetricsOverride", {
            "width": width, "height": 900, "deviceScaleFactor": 1, "mobile": width < 500})
        for p in PAGES:
            await cdp.navigate(BASE + p)
            await asyncio.sleep(2.0)
            raw = await cdp.eval_js(PROBE)
            try:
                d = json.loads(raw)
            except Exception:
                print(f"[{label}] {p}  PROBE FAILED: {str(raw)[:200]}")
                continue
            flag = []
            if d["docW"] > d["winW"]: flag.append(f"H-DRAG docW={d['docW']} winW={d['winW']}")
            if d["clipped"]: flag.append(f"CLIP {len(d['clipped'])}")
            if d["overflow"]: flag.append(f"OVFL {len(d['overflow'])}")
            if d["failed"]: flag.append("DATA-FAILED")
            print(f"[{label}] {p:15s} chars={d['bodyChars']:6d} rows={d['rows']} {' '.join(flag) or 'OK'}")
            for c in d["clipped"][:4]:
                print(f"      clip: {c['t']}  {c['sw']}>{c['cw']}")
            for o in d["overflow"][:4]:
                print(f"      ovfl: {o['t']}  {o['sh']}>{o['ch']}")
            if label == "desktop" and p in ("index.html", "week-01.html", "protocol.html"):
                print("      shot:", await shot(cdp, p.replace(".html", "") + ".png"))
    await cdp.close()

asyncio.run(main())
