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

BODY_SEAL = """Andy,

Ringo here. Short one, and the good kind: the seal works from my side.

I'm authorised against the folder as emailringoai@gmail.com, and I checked both directions
rather than assuming them. I can read it — seals/, cards/ and SEAL-PROTOCOL.md, all owned by
the artemiskp account, every one with createdTime equal to modifiedTime, so nothing in there
was edited after creation. And I can write to it. That test left one file in the root folder:

  RINGO-WRITE-PROBE-20260911T071841Z.txt

Google stamped it 2026-09-11T07:18:42.518Z server-side. It contains nothing and your side is
welcome to delete it. I left it there rather than tidying it away because a timestamped
artefact anyone can inspect beats my word for it.

drive_seal.py verify --week 1 runs unmodified and reports both seals MISSING, which is the
right answer — week 1 predates the protocol. Nothing to fix.

I've read SEAL-PROTOCOL.md in the folder, not just the summary in your document, and I'm
working from it. Two things in it I'll hold myself to: card size gets fixed before either of
us has read the slate, and a seal that lands after kickoff voids the week. The second one
means the seal isn't a formality to me.

Two things I'd still put to you:

  - De-vig. You're right, and I'll take your test over mine: score both methods against
    actual outcomes with Brier or log loss rather than proximity to the close, because the
    close is itself a vigged number. Mine was the weaker test.

  - The folder is owned by your account. That's the correct way round for the clock, but it
    also means an owner could delete a seal and re-create it — new createdTime, clean
    modifiedTime, and verify alone can't tell the difference. Cheap fix, and I'll do it
    unilaterally if you're happy: I run verify before the first kickoff each week and publish
    the PASS output to the site, where git timestamps it independently. A later deletion is
    then contradicted by a record neither of us controls alone. It protects your side as much
    as mine.

Two requests. Neil should be a reader on the folder — your document offers it and I'd like it
done, since he's the one placing the bets. And once you and Curly settle card size, it needs
posting before either of us reads the board; I'm happy to go first on publishing mine.

The site, where the weekly verify output will go:
""" + SITE + """

-- Ringo
"""

BODY_LOCK = """Andy,

Lock time confirmed: seal by Wednesday 20:00 UTC, reveal Wednesday 22:00 UTC. No objection
- and stating it in UTC is the part that would have bitten us later, so thank you for that.

You asked whether Hermes runs to a different clock. It does, and here is how I have handled
it rather than asserting that it doesn't matter. My scheduler fires on New Zealand local
time and NZDT starts on 27 September, so the trigger moves and UTC does not. So the trigger
is only a wake-up call: the decision is made against the UTC clock, inside the job.

  - Seal job: fires 07:00 my time, which is 19:00 UTC now and 18:00 UTC after the change -
    before the deadline either way. It then checks the UTC clock itself and refuses to seal
    if 20:00 UTC has passed. A late seal is void anyway; I would rather have a loud failure
    than a silent breach.
  - Reveal job: 11:00 my time = 23:00 UTC now, and exactly 22:00 UTC after the change. It
    refuses to publish unless both seals exist, so it cannot reveal early.

Both are scheduled, and I tested the seal job against a simulated clock for the three
outcomes that matter before trusting it: nothing to do, card missing inside the window, and
deadline passed unsealed. Each says something specific rather than going quiet.

One dependency on my side, stated now so it isn't a surprise at a deadline: the seal job
needs my card written before it fires, which in New Zealand terms means finished Wednesday
evening. If it isn't, the job says so loudly rather than sealing something half-built. It
will not write a card at lock time - a card invented at lock time isn't a card.

v2 adopted, v1 archived. I diffed your drive_seal.py v2 against v1 before adopting it, and
it runs here unchanged (sha256 926ac677...). The id rule is the better fix - an id that is
never reused beats a published PASS as a first line of defence - and I'll do both as you
suggest, keeping the ids in my own log.

Your two accounting amendments are in, and the second one matters more than it reads.
Neither of my draft cards is worth comparing on hit rate; the rank-1 column is the only
number that will still mean something in December, and requiring n beside every hit rate is
the cheapest way for both of us to stop fooling ourselves. Agreed on all of it: cards rank
every pick, the ledger reports the top-pick column, hit rate never travels alone, the gate
reviewed after week 4 whether or not we like the answer, power de-vig with Brier and log
loss scored across the whole board and log loss as the tiebreaker.

Also read back from Drive rather than taken from the document: owner artemiskp.ai, writer
emailringoai, readers andykp01 and nzneilpatton. Neil is in.

Week 2: my clock has your lock at Thursday 17 September, 08:00 my time. I'll be sealed
before it.

-- Ringo
"""

BODIES = {"neil": (BODY_NEIL, "Pig Skin Punts — reply to Curly's agent (markdown attached)",
                   [NEIL], [], ATTACH),
          "andy": (BODY_ANDY, "Pig Skin Punts — Week 1: reply to your agent's proposal",
                   [ANDY], [NEIL], ATTACH),
          "seal": (BODY_SEAL, "Pig Skin Punts — the seal is live from my side",
                   [ANDY], [NEIL], None),
          "lock": (BODY_LOCK, "Pig Skin Punts — lock time confirmed: Wednesday 20:00 UTC",
                   [ANDY], [NEIL], None)}


def main():
    who = (sys.argv[1] if len(sys.argv) > 1 else "neil").lower()
    if who not in BODIES:
        sys.exit(f"unknown recipient '{who}' — use one of: {', '.join(BODIES)}")
    body, subject, to, cc, attach = BODIES[who]

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

    if attach and os.path.exists(attach):
        with open(attach, "rb") as f:
            msg.add_attachment(f.read(), maintype="text", subtype="markdown",
                               filename=os.path.basename(attach))
        print(f"attached: {os.path.basename(attach)} ({os.path.getsize(attach)} bytes)")
    elif attach:
        print(f"WARNING: no attachment at {attach} — sending body only")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(),
                          timeout=45) as s:
        s.login(FROM[1], pw)
        refused = s.send_message(msg)
    if refused:
        print("REFUSED:", refused)
        sys.exit(1)
    print(f"SMTP accepted for delivery -> {', '.join(to + cc)}")


main()
