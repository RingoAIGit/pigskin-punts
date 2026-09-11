"""Verify the published site renders over the network."""
import asyncio
import json
import sys

sys.path.insert(0, "/Users/cerebral/.hermes/skills/research/browser-automation/scripts")
from cdp_lib import CDP, connect, new_tab  # noqa: E402

LIVE = sys.argv[1] if len(sys.argv) > 1 else "https://waking-walrus-3vcd.here.now/"

PROBE = r"""
(() => {
  const out = {rows:{}, hasCss:false, gateBars:0, docW:0, winW:0, title:document.title};
  out.hasCss = !!document.querySelector('link[href*="style.css"]') &&
    getComputedStyle(document.querySelector('.wordmark')).fontFamily.slice(0,20);
  ['tonightTable','edgesTable','keyTable'].forEach(id => {
    const e = document.getElementById(id);
    out.rows[id] = e ? e.querySelectorAll('tbody tr').length : 'MISSING';
  });
  const sp = document.getElementById('spikes'); out.rows.spikes = sp ? sp.querySelectorAll('.spike').length : 'MISSING';
  out.gateBars = document.querySelectorAll('#tonightGates .gate-row').length;
  out.docW = document.documentElement.scrollWidth; out.winW = window.innerWidth;
  out.failed = document.body.innerText.indexOf('failed to load') >= 0;
  return JSON.stringify(out);
})()
"""


async def main():
    page = new_tab("about:blank")
    ws = await connect(page["webSocketDebuggerUrl"])
    cdp = CDP(ws)
    await cdp.cmd("Runtime.enable")
    await cdp.cmd("Page.enable")
    await cdp.cmd("Emulation.setDeviceMetricsOverride",
                  {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})
    for path in ("", "week-01.html", "method.html", "protocol.html", "reply-to-curly.md",
                 "assets/data/week01.json"):
        r = await cdp.cmd("Network.enable")
        await cdp.navigate(LIVE + path)
        await asyncio.sleep(2.5)
        status = await cdp.eval_js(
            "(()=>{const e=document.querySelector('pre'); return document.body.innerText.slice(0,60)})()")
        raw = await cdp.eval_js(PROBE)
        try:
            d = json.loads(raw)
        except Exception:
            d = {"raw": str(raw)[:120]}
        print(f"{path or '(root)':28s} rows={d.get('rows')} gates={d.get('gateBars')} "
              f"css={d.get('hasCss')} failed={d.get('failed')} drag={d.get('docW',0) > d.get('winW',0)}")
    await cdp.close()

asyncio.run(main())
