"""End-to-end check that the bet form works, in a real browser, on the live site.

Reports what the games dropdown actually contains, picks the first real game from it, fills
the rest, clicks Save, and reports what the page said. A form that offers the wrong fixtures
is worse than one that offers none, so the contents get checked too.

    ~/.hermes/hermes-agent/venv/bin/python verify_bet_save.py [url]

Creates one test record. Clean it up with:
    python3 -c "..."   (or see bets_pull.py --write for the read path)
"""
import asyncio
import sys

sys.path.insert(0, "/Users/cerebral/.hermes/skills/research/browser-automation/scripts")
from cdp_lib import CDP, connect, new_tab  # noqa: E402

URL = sys.argv[1] if len(sys.argv) > 1 else "https://waking-walrus-3vcd.here.now/bets.html"

INSPECT = """(() => {
  const g = document.getElementById('f-game');
  const out = { tag: g ? g.tagName : 'MISSING' };
  if (g && g.tagName === 'SELECT') {
    out.groups = [...g.querySelectorAll('optgroup')].map(o => o.label + ' (' + o.children.length + ')');
    out.options = [...g.querySelectorAll('option')].filter(o => o.value).map(o => o.value);
  }
  const n = document.getElementById('slateNote');
  out.note = n ? n.textContent : '';
  return JSON.stringify(out);
})()"""

FILL = """(() => {
  const set = (id, v) => {
    const e = document.getElementById(id);
    if (!e) return 'missing #' + id;
    e.value = v;
    e.dispatchEvent(new Event('input', { bubbles: true }));
    e.dispatchEvent(new Event('change', { bubbles: true }));
    return null;
  };
  const g = document.getElementById('f-game');
  let game;
  if (g && g.tagName === 'SELECT') {
    const opts = [...g.querySelectorAll('option')].filter(o => o.value);
    if (!opts.length) return 'NO GAMES IN THE DROPDOWN';
    g.value = opts[0].value;
    game = g.value;
    g.dispatchEvent(new Event('change', { bubbles: true }));
  } else {
    set('f-game', 'TEST fallback text');
    game = 'TEST fallback text (dropdown did not load)';
  }
  set('f-date', '2026-09-11');
  set('f-sel', 'TEST +2.5');
  set('f-odds', '1.95');
  set('f-stake', '5');
  set('f-note', 'browser probe from verify_bet_save.py');
  document.getElementById('betBuild').click();
  return game;
})()"""


async def main():
    tab = new_tab("about:blank")
    ws = await connect(tab["webSocketDebuggerUrl"])
    c = CDP(ws)
    await c.cmd("Runtime.enable")
    await c.cmd("Page.enable")
    await c.cmd("Network.setCacheDisabled", {"cacheDisabled": True})
    await c.navigate(URL)
    await asyncio.sleep(2)

    print("page     :", await c.eval_js("document.title"))
    import json
    # The dropdown fills from a fetch, so wait for it instead of trusting a fixed delay --
    # a cold edge copy of the snapshot can take a few seconds to arrive.
    info = {}
    for _ in range(20):
        info = json.loads(await c.eval_js(INSPECT))
        if info.get("options"):
            break
        await asyncio.sleep(1.5)
    print("games    :", info.get("tag"), "|", len(info.get("options", [])), "options")
    for g in info.get("groups", []):
        print("           ", g)
    for o in info.get("options", [])[:3]:
        print("            e.g.", o)
    print("note     :", info.get("note", ""))

    game = await c.eval_js(FILL)
    print("chosen   :", game)
    await c.eval_js("document.getElementById('betSave').click()")
    msg = ""
    for _ in range(12):
        await asyncio.sleep(1.5)
        msg = await c.eval_js("document.getElementById('betMsg').textContent")
        if msg and "Saving" not in msg:
            break
    print("after save:", msg)
    ok = msg.startswith("Saved to the record") and "TEST fallback" not in (game or "")
    print("verdict  :", "SAVED" if ok else "NOT SAVED")
    await c.close()


asyncio.run(main())
