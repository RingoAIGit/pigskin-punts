"""Focused checks: the passes table, and the bet form's copy path."""
import asyncio
import json
import sys

sys.path.insert(0, "/Users/cerebral/.hermes/skills/research/browser-automation/scripts")
from cdp_lib import CDP, connect, new_tab  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8899/"


async def main():
    page = new_tab("about:blank")
    ws = await connect(page["webSocketDebuggerUrl"])
    cdp = CDP(ws)
    await cdp.cmd("Runtime.enable")
    await cdp.cmd("Page.enable")
    await cdp.cmd("Emulation.setDeviceMetricsOverride",
                  {"width": 390, "height": 844, "deviceScaleFactor": 2, "mobile": True})

    await cdp.navigate(BASE + "results.html")
    await asyncio.sleep(2.2)
    print("passes table:", await cdp.eval_js(
        "(()=>{const h=document.getElementById('passesTable');"
        "const t=h&&h.querySelector('table');"
        "return t ? t.querySelectorAll('tbody tr').length + ' rows | ' + "
        "(t.querySelector('tbody tr').textContent.trim().slice(0,70)) : 'NO TABLE'})()"
    ))
    print("bankroll chart:", await cdp.eval_js(
        "document.querySelectorAll('#bankrollChart svg path').length + ' path(s), text=' + "
        "(document.querySelector('#bankrollChart svg') ? "
        "document.querySelector('#bankrollChart svg').textContent : 'none')"))
    print("analysis paras:", await cdp.eval_js(
        "document.querySelectorAll('main .panel h3').length + ' panel headings'"))

    await cdp.navigate(BASE + "bets.html")
    await asyncio.sleep(2.0)
    print("\n-- form --")
    print(await cdp.eval_js("""
    (() => {
      const set=(id,v)=>{const e=document.getElementById(id); e.value=v;
        e.dispatchEvent(new Event('input',{bubbles:true}));
        e.dispatchEvent(new Event('change',{bubbles:true}));};
      set('f-game','Panthers @ Bears'); set('f-sel','Bears -3'); set('f-odds','1.60');
      set('f-stake','5'); set('f-by','Neil'); set('f-agent',"Curly's agent");
      document.getElementById('betBuild').click();
      document.getElementById('betDiscord').click();
      return document.getElementById('betLine').textContent;
    })()
    """))
    await asyncio.sleep(1.5)
    print("clipboard/copy message:", repr(await cdp.eval_js(
        "document.getElementById('betMsg').textContent")))
    print("mailto ok:", await cdp.eval_js(
        "(document.getElementById('betMail').getAttribute('href')||'').slice(0,52)"))
    await cdp.close()

asyncio.run(main())
