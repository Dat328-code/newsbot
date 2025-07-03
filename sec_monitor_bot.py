import time
import os
import feedparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import traceback
from datetime import datetime, timedelta

# === CONFIG ===
EMAIL_USER       = os.getenv("EMAIL_USER")
EMAIL_PASS       = os.getenv("EMAIL_PASSWORD")
EMAIL_TO         = os.getenv("EMAIL_TO") or EMAIL_USER

SEC_FEED         = (
    "https://www.sec.gov/cgi-bin/browse-edgar?"
    "action=getcurrent&type=8-K&owner=exclude&count=100&output=atom"
)
PERSIST_FILE     = "seen_accessions.json"
POLL_INTERVAL    = 60          # seconds between feed polls
HEARTBEAT_HOURS  = 3           # hours between heartbeat emails

# === Email utility ===
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

# === Persistence ===
def load_seen():
    if os.path.exists(PERSIST_FILE):
        with open(PERSIST_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(PERSIST_FILE, 'w') as f:
        json.dump(list(seen), f)

# === Monitor loop ===
def monitor():
    seen = load_seen()

    # Send startup notification
    now = datetime.now()
    send_email("[SEC Monitor] Bot Deployed",
               f"SEC Monitor Bot deployed at {now.isoformat()}.")
    last_heartbeat = now
    print(f"Monitoring SEC 8-K feed every {POLL_INTERVAL} seconds...")

    while True:
        try:
            feed = feedparser.parse(SEC_FEED)
            for entry in feed.entries:
                accnum = entry.id.split('/')[-1] if hasattr(entry, 'id') else entry.link
                if accnum not in seen:
                    seen.add(accnum)
                    title = entry.title
                    link  = entry.link
                    subj  = f"[SEC 8-K] {title}"
                    body  = f"New 8-K filing detected:\n{title}\nLink: {link}"
                    send_email(subj, body)
            save_seen(seen)

            # Heartbeat
            now = datetime.now()
            if (now - last_heartbeat) >= timedelta(hours=HEARTBEAT_HOURS):
                send_email("[SEC Monitor] Bot Heartbeat",
                           f"Bot is still running at {now.isoformat()}.")
                last_heartbeat = now

        except Exception as e:
            print("Error during monitoring:", e)
            traceback.print_exc()
        time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    if not EMAIL_USER or not EMAIL_PASS:
        print("ERROR: EMAIL_USER and EMAIL_PASSWORD must be set in environment.")
        exit(1)
    monitor()
