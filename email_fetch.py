"""Fetch a message from Ringo's Gmail and save any attachments.

    python3 email_fetch.py                 # newest message from Andy
    python3 email_fetch.py --from X --save DIR

Saves attachments into DIR (default ~/Documents/Betting/incoming) without
clobbering an existing file, and prints the plain-text body.
"""
import argparse
import email
import imaplib
import os
import re
from email.header import decode_header

ACCOUNT = "emailringoai@gmail.com"
PW_FILE = os.path.expanduser("~/.hermes/.gmail_password")


def dec(v):
    if not v:
        return ""
    out = []
    for part, enc in decode_header(v):
        if isinstance(part, bytes):
            out.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(part)
    return "".join(out).strip()


def safe(name):
    name = os.path.basename(name or "attachment")
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="sender", default="andykp01@gmail.com")
    ap.add_argument("--save", default=os.path.expanduser("~/Documents/Betting/incoming"))
    ap.add_argument("--all", action="store_true", help="every message from sender, oldest first")
    args = ap.parse_args()

    os.makedirs(args.save, exist_ok=True)
    pw = open(PW_FILE).read().strip()
    M = imaplib.IMAP4_SSL("imap.gmail.com")
    M.login(ACCOUNT, pw)
    M.select("INBOX")

    typ, data = M.search(None, "FROM", f'"{args.sender}"')
    ids = data[0].split()
    if not ids:
        print(f"no messages from {args.sender}")
        return
    targets = ids if args.all else ids[-1:]

    for mid in targets:
        typ, raw = M.fetch(mid, "(RFC822)")
        msg = email.message_from_bytes(raw[0][1])
        print("=" * 72)
        print("id      :", mid.decode())
        print("from    :", dec(msg.get("From")))
        print("to      :", dec(msg.get("To")))
        print("cc      :", dec(msg.get("Cc")))
        print("date    :", msg.get("Date"))
        print("subject :", dec(msg.get("Subject")))
        print("-" * 72)

        body = ""
        files = []
        for part in msg.walk():
            ctype = part.get_content_type()
            disp = str(part.get("Content-Disposition") or "")
            fname = part.get_filename()
            if "attachment" in disp or (fname and ctype not in ("text/plain", "text/html")):
                fname = safe(dec(fname) if fname else "attachment")
                path = os.path.join(args.save, fname)
                base, ext = os.path.splitext(path)
                n = 2
                while os.path.exists(path):
                    path = f"{base}-{n}{ext}"
                    n += 1
                with open(path, "wb") as f:
                    f.write(part.get_payload(decode=True))
                files.append((path, os.path.getsize(path)))
            elif ctype == "text/plain":
                body += part.get_payload(decode=True).decode(
                    part.get_content_charset() or "utf-8", errors="replace")

        print(body.strip()[:2500] if body.strip() else "(no plain-text body)")
        print("-" * 72)
        for p, size in files:
            print(f"SAVED: {p}  ({size} bytes)")
        if not files:
            print("no attachments found")

    M.logout()


main()
