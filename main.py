"""Email Triage Assistant."""
import argparse
import json
import mailbox
import re
from pathlib import Path

import llm

VIPS = {"ceo@acme.ng", "mrs.ade@brightschools.ng"}
CATEGORIES = {
    "invoice": ["invoice", "payment", "receipt", "bill"],
    "meeting": ["meeting", "call", "schedule", "calendar", "zoom", "available"],
    "newsletter": ["unsubscribe", "newsletter", "weekly digest", "webinar"],
    "client": ["proposal", "contract", "project", "quote", "deliverable"],
}
URGENT = ["urgent", "asap", "today", "by eod", "deadline", "immediately", "overdue"]
PHISH = ["verify your account", "password expires", "click here to avoid", "gift card"]


def classify(e: dict) -> dict:
    text = f"{e['subject']} {e['body']}".lower()
    sender = e["from"].lower()
    domain = sender.split("@")[-1]
    if any(p in text for p in PHISH) or re.search(r"(paypa1|g00gle|micros0ft)", domain):
        return {**e, "category": "phishing", "priority": 0, "bucket": "Ignore / report"}
    cat = next((c for c, w in CATEGORIES.items() if any(x in text for x in w)), "other")
    p = 2
    p += 3 if sender in VIPS else 0
    p += 2 if any(u in text for u in URGENT) else 0
    p += 1 if "?" in e["body"] else 0
    p -= 3 if cat == "newsletter" or "no-reply" in sender or "noreply" in sender else 0
    bucket = ("Act now" if p >= 6 else "Reply today" if p >= 3 else
              "Read later" if p >= 0 else "Ignore / report")
    return {**e, "category": cat, "priority": p, "bucket": bucket}


def draft(e: dict) -> str:
    name = e["from"].split("@")[0].split(".")[0].title()
    base = {
        "meeting": f"Hi {name}, thanks. Tuesday or Wednesday after 2pm works for me. Which suits you?",
        "invoice": f"Hi {name}, thanks for this. I've forwarded it to finance and will confirm payment timing shortly.",
        "client": f"Hi {name}, thanks for the update. I'll review and come back to you by end of day.",
    }.get(e["category"], f"Hi {name}, thanks for your email. I'll get back to you shortly.")
    better = llm.complete(f"Draft a brief reply (under 60 words) to this email.\nSubject: "
                          f"{e['subject']}\n{e['body']}")
    return (better or base).strip()


def load(args):
    if args.mbox:
        out = []
        for m in mailbox.mbox(args.mbox):
            body = m.get_payload(decode=True) if not m.is_multipart() else \
                m.get_payload(0).get_payload(decode=True)
            out.append({"from": re.sub(r".*<|>.*", "", m["from"] or ""),
                        "subject": m["subject"] or "", "body": (body or b"").decode(errors="ignore")})
        return out
    return json.loads(Path(args.input).read_text())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", default="sample_emails.json")
    ap.add_argument("--mbox")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    emails = [classify(e) for e in load(a)]
    order = ["Act now", "Reply today", "Read later", "Ignore / report"]
    lines = ["# Inbox triage", ""]
    for b in order:
        group = [e for e in emails if e["bucket"] == b]
        print(f"== {b} ({len(group)}) ==")
        lines += [f"## {b}", ""]
        for e in sorted(group, key=lambda x: -x["priority"]):
            print(f"  [{e['category']:<10}] {e['from']:<30} {e['subject']}")
            lines.append(f"- **{e['subject']}** from {e['from']} ({e['category']})")
            if b in ("Act now", "Reply today"):
                d = draft(e)
                print(f"      draft: {d}")
                lines.append(f"  - Draft: {d}")
        lines.append("")
    Path("output").mkdir(exist_ok=True)
    Path("output/triage.md").write_text("\n".join(lines))
    print("\nSaved output/triage.md")


if __name__ == "__main__":
    main()
