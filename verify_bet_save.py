"""End-to-end check that the bet form saves, using a real browser on the live site.

Fills the form, clicks Build then Save, and reports what the page said. This is the actual
user path -- if this passes, the feature works for Neil, not just for curl.

    ~/.hermes/hermes-agent/venv/bin/python verify_bet_save.py [url]
"""
import asyncio
import sys

sys.path.insert(0, "/Users/cerebral/.hermes/skills/research/browser-automation/scripts")
from cdp_lib import CDP, connect, new_tab  # noqa: E402

URL = sys.argv[1] if len(sys.argv) > 1 else "https://waking-walrus-3vcd.here.now/bets.html"

FILL = """(() => {
  const set = (id, v) => {
    const e = document.getElementById(id);
    if (!e) return 'missing #' + id;
    e.value = v;
    e.dispatchEvent(new Event('input', { bubbles: true }));
    e.dispatchEvent(new Event('change', { bubbles: true }));
    return null;
  };
  const errs = [
    set('f-date', '2026-09-11'),
    set('f-game', 'TEST GAME (browser, delete me)'),
    set('f-market', 'spread'),
    set('f-sel', 'TEST -2.5'),
    set('f-odds', '1.95'),
    set('f-stake', '5'),
    set('f-by', 'neil'),
    set('f-agent', 'ringo'),
    set('f-note', 'browser probe from verify_bet_save.py')
  ].filter(Boolean);
  if (errs.length) return 'FIELD ERRORS: ' + errs.join(', ');
  document.getElementById('betBuild').click();
  return document.getElementById('betLine').textContent;
})()"""


async def main():
    tab = new_tab("about:blank")
    ws = await connect(tab["webSocketDebuggerUrl"])
    c = CDP(ws)
    await c.cmd("Runtime.enable")
    await c.cmd("Page.enable")
    await c.cmd("Network.setCacheDisabled", {"cacheDisabled": True})
    await c.navigate(URL)
    await asyncio.sleep(3)

    print("page       :", await c.eval_js("document.title"))
    print("save button:", await c.eval_js(
        "(()=>{const b=document.getElementById('betSave');return b?b.textContent:'MISSING'})()"))
    print("built      :", await c.eval_js(FILL))

    await c.eval_js("document.getElementById('betSave').click()")
    msg = ""
    for _ in range(12):
        await asyncio.sleep(1.5)
        msg = await c.eval_js("document.getElementById('betMsg').textContent")
        if msg and "Saving" not in msg:
            break
    print("after save :", msg)
    print("verdict    :", "SAVED" if msg.startswith("Saved to the record") else "NOT SAVED")
    await c.close()


asyncio.run(main())
