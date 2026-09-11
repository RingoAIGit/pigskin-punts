"""Sign in to here.now so the Pig Skin Punts site stops expiring.

Free tier is permanent and costs nothing (10 GB, 500 sites). This uses the Ringo mailbox for
the one-time sign-in code, so nothing lands in Neil's inbox and no step is needed from him.

Then it tries to claim the existing anonymous site, which would keep the current URL --
worth trying because that URL is already written into the Google OAuth consent screen as
both the app home page and the privacy policy. If the claim token has rotated, it says so
rather than pretending.
"""
import json
import os
import re
import ssl
import sys
import time
import imaplib
import urllib.error
import urllib.request

API = "https://here.now"
EMAIL = "emailringoai@gmail.com"
PW_FILE = os.path.expanduser("~/.hermes/.gmail_password")
CREDS = os.path.expanduser("~/.herenow/credentials")
SITE_DIR = os.path.expanduser("~/Documents/pigskin-punts")
STATE = os.path.join(SITE_DIR, ".herenow", "state.json")
KEY_NAME = "hermes-ringo"


def post(path, body, key=None):
    data = json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, method="POST",
                                headers={"content-type": "application/json"})
    if key:
        req.add_header("Authorization", "Bearer " + key)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        try:
            body = json.loads(body)
        except Exception:
            pass
        return e.code, body
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"


def gmail():
    pw = open(PW_FILE).read().strip()
    M = imaplib.IMAP4_SSL("imap.gmail.com", timeout=60)
    M.login(EMAIL, pw)
    return M


def find_code(M, timeout_s=150):
    """Poll the inbox for the here.now sign-in code. Returns (code, snippet)."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        M.select("INBOX")
        typ, ids = M.search(None, 'FROM "here.now"')
        ids = ids[0].split()
        for i in reversed(ids[-4:]):
            typ, d = M.fetch(i, "(BODY[])")
            raw = b"".join(part[1] for part in d if isinstance(part, tuple))
            text = raw.decode("utf-8", "replace")
            text = re.sub(r"=\r?\n", "", text)                     # undo quoted-printable wraps
            m = (re.search(r"\b[A-Z0-9]{4}-[A-Z0-9]{4}\b", text)
                 or re.search(r"\b\d{6}\b", text)
                 or re.search(r"\b[A-Z0-9]{8}\b", text))
            if m:
                snippet = " ".join(text.split())[:400]
                return m.group(0), snippet
        print(f"  no code yet, waiting... ({(deadline - time.time()):.0f}s left)")
        time.sleep(10)
    return None, None


def state_entry():
    if not os.path.exists(STATE):
        return None, None
    st = json.load(open(STATE))
    for slug, info in (st.get("publishes") or {}).items():
        if info.get("claimToken"):
            return slug, info
    return None, None


def main():
    key = None
    if os.path.exists(CREDS):
        key = open(CREDS).read().strip()
        if key:
            print(f"already have an API key at {CREDS} (…{key[-4:]}) - reusing it.")

    if not key:
        print("1. requesting a sign-in code for", EMAIL)
        st, res = post("/api/auth/agent/request-code", {"email": EMAIL})
        print(f"   {st} {res}")
        if st != 200:
            return 1
        print("2. reading the code out of the Ringo inbox")
        M = gmail()
        try:
            code, snippet = find_code(M)
        finally:
            try:
                M.logout()
            except Exception:
                pass
        if not code:
            print("   no code arrived within the window.")
            print("   Last here.now mail seen:")
            print("   ", snippet)
            return 1
        print(f"   code found: {code}")
        print("3. verifying it")
        st, res = post("/api/auth/agent/verify-code",
                       {"email": EMAIL, "code": code, "keyName": KEY_NAME})
        print(f"   {st} {res}")
        if st != 200 or not isinstance(res, dict) or not res.get("apiKey"):
            return 1
        key = res["apiKey"]
        os.makedirs(os.path.dirname(CREDS), exist_ok=True)
        with open(CREDS, "w") as f:
            f.write(key)
        os.chmod(CREDS, 0o600)
        print(f"   key saved to {CREDS} (0600), account "
              f"{'created' if res.get('isNewUser') else 'existing'}")

    # Try to keep the current URL: it is already written into the Google OAuth consent screen.
    slug, info = state_entry()
    if slug:
        print(f"4. claiming the existing site '{slug}' to keep the current URL")
        st, res = post(f"/api/v1/publish/{slug}/claim",
                       {"claimToken": info["claimToken"]}, key=key)
        print(f"   {st} {res}")
        if st == 200:
            print(f"   CLAIMED. expiresAt={res.get('expiresAt')} "
                  f"(null means permanent)")
            print(f"   siteUrl {res.get('siteUrl')}")
        else:
            print("   claim did not succeed - the token has probably rotated. The site will")
            print("   still expire; a fresh publish under the account gives a new URL, and the")
            print("   two links in the Google OAuth branding page would need updating.")
    else:
        print("4. no claim token on disk for an anonymous site - nothing to claim.")

    print("5. what the account holds now")
    req = urllib.request.Request(API + "/api/v1/publishes",
                                 headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read().decode())
        sites = body.get("publishes") or body.get("sites") or []
        if not sites:
            print("   no sites on the account yet (expected if the claim failed)")
        for s in sites:
            print(f"   {s.get('slug')}  expiresAt={s.get('expiresAt')}  "
                  f"url={s.get('siteUrl')}")
    except Exception as e:
        print(f"   could not list sites: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
