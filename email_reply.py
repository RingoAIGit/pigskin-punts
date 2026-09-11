"""Email the Week 1 markdown reply as an attachment.

Ringo's account (emailringoai@gmail.com) as sender. Two recipients:

    python3 email_reply.py neil    -> Neil only (nzneilpatton@icloud.com)
    python3 email_reply.py andy    -> Andy direct (andykp01@gmail.com), Neil cc'd

Password read from ~/.hermes/.gmail_password (app password).
"""
import mimetypes
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formataddr

FROM = ("Ringo", "emailringoai@gmail.com")
NEIL = "nzneilpatton@icloud.com"
ANDY = "andykp01@gmail.com"
ATTACH = "/Users/cerebral/Documents/pigskin-punts/reply-to-curly.md"
PW_FILE = os.path.expanduser("~/.hermes/.gmail_password")

SITE = "https://waking-walrus-3vcd.here.now/"

BODY_NEIL = """Neil,

Attached: the markdown document — my full response to your agent's proposal, Week 1.

Short version:
  - The key-number correction: his count is two-sided, roughly double. Mine was right at 3,
    too low everywhere else. Both fixed.
  - The de-vig change: he's directionally right, and the criticism lands on my method too.
    It moves every edge, so it needs agreeing and validating, not adopting.
  - The game that fell off the board: structurally right, now fixed. His New England
    number rests on a weaker reference than the one he's asking me to share.

The site restructured the way you asked — betting first, method in its own page:
""" + SITE + """

Four pages: The card, Bets (with the entry form), Results and analysis, Method.

-- Ringo
"""

BODY_ANDY = """Andy,

Ringo here — Neil's agent on the Pig Skin Punts card. Your agent sent over a proposed
operating agreement for the two of us; this is my reply, attached as markdown so nothing
gets mangled in a chat window.

The short version:

  - Key numbers. His table counts games where EITHER team lands on the key. A half point
    is only decisive when the favourite does — roughly half that number. I reproduced his
    column exactly on all seven keys, so this is a definitional difference rather than a
    disagreement about football. The cleanest check: when the number is 3, the favourite
    wins by exactly 3 in 9.14% of games (n=569). One push in eleven. His 16.16% would make
    it one in six. He did find real errors in my other rows, and those are fixed.

  - De-vig. He's right in principle, and the criticism lands on my method too — my
    median-of-books strips margin proportionally per book. But the fix moves every edge on
    the board (short favourites gain ~2-2.5 points, longshots lose more), so I'd rather we
    agree it and validate it against closing lines than adopt it because it reads better.
    Either way, Week 1 qualifies nothing under both methods.

  - The game that fell off the board. Structurally right, and now fixed — TAB only carries
    open events, so Thursday games get priced when the lines post rather than on Friday.
    The factual claim about New England doesn't hold on my reference: my 9-book median puts
    that price at -4.36%, worse than the Carolina side he says it beats.

Taken in full: sealed cards covering the reasoning, an explicit passes list, immutable
line snapshots, sharing my weekly US consensus output, the two-layer split of contest and
money, conflicts tracked rather than dropped, and the sample-size caveat — I checked his
simulation and the numbers hold.

Still open, and it's a decision for you and Neil: the weekly exposure cap, card size,
whether conflicts are kept and tracked, and the gate value. All four are written up here:

""" + SITE + """

That's the card, the bet log with an entry form, the results and the analysis, and the
method behind it. Your agent's card can live in the same place each week once we settle how
it gets there — my preference is a GitHub issue, so neither of us owns the timestamp.

-- Ringo
"""

BODIES = {"neil": (BODY_NEIL, "Pig Skin Punts — reply to Curly's agent (markdown attached)", [NEIL], []),
          "andy": (BODY_ANDY, "Pig Skin Punts — Week 1: reply to your agent's proposal",
                   [ANDY], [NEIL])}


def main():
    who = (sys.argv[1] if len(sys.argv) > 1 else "neil").lower()
    if who not in BODIES:
        sys.exit(f"unknown recipient '{who}' — use neil or andy")
    body, subject, to, cc = BODIES[who]

    if not os.path.exists(PW_FILE):
        sys.exit(f"missing password file: {PW_FILE}")
    pw = open(PW_FILE).read().strip()

    msg = EmailMessage()
    msg["From"] = formataddr(FROM)
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg.set_content(body)

    if os.path.exists(ATTACH):
        with open(ATTACH, "rb") as f:
            msg.add_attachment(f.read(), maintype="text", subtype="markdown",
                               filename=os.path.basename(ATTACH))
        print(f"attached: {os.path.basename(ATTACH)} ({os.path.getsize(ATTACH)} bytes)")
    else:
        print(f"WARNING: no attachment at {ATTACH} — sending body only")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(),
                          timeout=45) as s:
        s.login(FROM[1], pw)
        refused = s.send_message(msg)
    if refused:
        print("REFUSED:", refused)
        sys.exit(1)
    print(f"SMTP accepted for delivery -> {', '.join(to + cc)}")


main()
