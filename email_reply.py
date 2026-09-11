"""Email Neil the Week 1 markdown reply as an attachment.

Ringo's account (emailringoai@gmail.com) -> Neil (nzneilpatton@icloud.com).
Password read from ~/.hermes/.gmail_password (app password).
"""
import mimetypes
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage

FROM = "emailringoai@gmail.com"
TO = "nzneilpatton@icloud.com"
SUBJECT = "Pig Skin Punts — reply to Curly's agent (markdown attached)"
ATTACH = "/Users/cerebral/Documents/pigskin-punts/reply-to-curly.md"
PW_FILE = os.path.expanduser("~/.hermes/.gmail_password")

BODY = """Neil,

Attached: the markdown document — my full response to Curly's agent's proposal, Week 1.

Short version:
  - The key-number correction: his count is two-sided, roughly double. Mine was right at 3,
    too low everywhere else. Both fixed.
  - The de-vig change: he's directionally right, and the criticism lands on my method too.
    It moves every edge, so it needs agreeing and validating, not adopting.
  - The game that fell off the board: structurally right, now fixed. His New England
    number rests on a weaker reference than the one he's asking me to share.

The site is built and restructured the way you asked — betting first, method in its own
page:

  https://waking-walrus-3vcd.here.now/

Four pages: The card (this week's bets), Bets (the log, with the entry form), Results
(settled bets and the analysis), Method (the system).

Two things waiting on you:
  1. The here.now link expires about 4:50pm today. Claim it to keep it:
     https://here.now/c/vSROR8FWRXcS6lpU
  2. GitHub Pages needs two clicks to go permanent — Settings, Pages, deploy from branch
     main / root. Your token can't enable it from my side.

-- Ringo
"""


def main():
    if not os.path.exists(PW_FILE):
        sys.exit(f"missing password file: {PW_FILE}")
    pw = open(PW_FILE).read().strip()

    msg = EmailMessage()
    msg["From"] = FROM
    msg["To"] = TO
    msg["Subject"] = SUBJECT
    msg.set_content(BODY)

    if os.path.exists(ATTACH):
        ctype, _ = mimetypes.guess_type(ATTACH)
        maintype, subtype = (ctype or "text/markdown").split("/", 1)
        with open(ATTACH, "rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype,
                               filename=os.path.basename(ATTACH))
        print(f"attached: {os.path.basename(ATTACH)} "
              f"({os.path.getsize(ATTACH)} bytes)")
    else:
        print(f"WARNING: attachment not found at {ATTACH} — sending body only")

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=45) as s:
        s.login(FROM, pw)
        refused = s.send_message(msg)
    if refused:
        print("REFUSED:", refused)
        sys.exit(1)
    print(f"SMTP accepted for delivery -> {TO}")


main()
