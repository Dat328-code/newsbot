#!/usr/bin/env python3
import time
import os
import requests
import feedparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import traceback

# === CONFIG ===
EMAIL_USER   = os.getenv("EMAIL_USER")
EMAIL_PASS   = os.getenv("EMAIL_PASSWORD")
EMAIL_TO     = os.getenv("EMAIL_TO") or EMAIL_USER

SEC_FEED_URL = (
    "https://www.sec.gov/cgi-bin/browse-edgar?"
    "action=getcurrent&type=8-K&owner=exclude&count=100&output=atom"
)
HEADERS      = {
    "User-Agent": "MyBot/1.0 (your_email@example.com)"
}
PERSIST_FILE = "seen_accessions.json"
INTERVAL     = 60  # seconds between polls

# === Email helper ===
def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From']    = EMAIL_USER
    msg['To']      = EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
            print(f"Sent email: {subject}")
    except Exception:
        print(f"Failed to send email: {subject}")
        traceback.print_exc()

# === Seen‐cache persistence ===
def load_seen():
    if os.path.exists(PERSIST_FILE):
        with open(PERSIST_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(PERSIST_FILE, 'w') as f:
        json.dump(list(seen), f)

# === Main monitoring loop ===
def monitor():
    seen = load_seen()
    print(f"Monitoring SEC 8-K feed every {INTERVAL} seconds...")
    while True:
        try:
            # Fetch with requests + headers to avoid SEC blocking
            resp = requests.get(SEC_FEED_URL, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)

            for entry in feed.entries:
                # Unique key per filing
                accnum = entry.id.split('/')[-1] if hasattr(entry, 'id') else entry.link
                if accnum not in seen:
                    seen.add(accnum)
                    title = entry.title
                    link  = entry.link
                    subject = f"[SEC 8-K] {title}"
                    body    = f"New 8-K filing detected:\n{title}\nLink: {link}"
                    send_email(subject, body)

            # Persist updated seen list
            save_seen(seen)

        except Exception as e:
            print("Error during monitoring:", e)
            traceback.print_exc()

        time.sleep(INTERVAL)

if __name__ == '__main__':
    if not EMAIL_USER or not EMAIL_PASS:
        print("ERROR: EMAIL_USER and EMAIL_PASSWORD must be set in environment.")
        exit(1)
    monitor()
