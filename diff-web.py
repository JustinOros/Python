#!/usr/bin/env python3
# Description: Monitor a website for changes.
# Usage: python3 diff-web.py https://example.com --email user@example.com
# Author: Justin Oros
# Source: https://github.com/JustinOros

import requests
import hashlib
import os
import time
import argparse
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from datetime import datetime
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv("EMAIL_USER")
SMTP_PASSWORD = os.getenv("EMAIL_PASS")
EMAIL_FROM = SMTP_USERNAME

def normalize_url(url):
    parsed = urlparse(url)
    if not parsed.scheme:
        url = 'https://' + url
        parsed = urlparse(url)

    query = parse_qs(parsed.query)
    stripped_query = {k: v for k, v in query.items() if not k.startswith(('utm_', 'fbclid', 'gclid'))}
    new_query = urlencode(stripped_query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

def fetch_content(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    for tag in soup(["script", "style", "noscript", "iframe", "svg", "canvas"]):
        tag.decompose()
    return soup.get_text(separator=' ', strip=True)

def get_hash(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def get_log_filename(url, override=None):
    if override:
        return override
    domain = urlparse(url).netloc
    return f"{domain}.log"

def get_cache_filename(url):
    domain = urlparse(url).netloc
    return f".{domain}.cache"

def log_message(message, log_file, quiet=False):
    if not quiet:
        print(message)
    with open(log_file, 'a') as f:
        f.write(message + '\n')

def timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def send_email(subject, body, recipients):
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("Email credentials not configured in environment.")
        return
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = ", ".join(recipients)
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(EMAIL_FROM, recipients, msg.as_string())
    except Exception as e:
        print(f"Failed to send email: {e}")

def monitor_website(url, interval, log_file_override=None, quiet=False, recipients=None):
    url = normalize_url(url)
    domain = urlparse(url).netloc
    log_file = get_log_filename(url, log_file_override)
    cache_file = get_cache_filename(url)

    log_message(f"[{timestamp()}] Monitoring {domain}", log_file, quiet)

    while True:
        try:
            current_content = fetch_content(url)
            current_hash = get_hash(current_content)
        except Exception as e:
            log_message(f"[{timestamp()}] [ERROR] Failed to fetch {url}: {e}", log_file, quiet)
            time.sleep(interval)
            continue

        is_changed = True
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                old_hash = f.read().strip()
            is_changed = current_hash != old_hash
            if is_changed:
                log_message(f"[{timestamp()}] Change detected on {url}", log_file, quiet)
                if recipients:
                    subject = f"Website Change Detected: {domain}"
                    body = f"A change was detected on {url} at {timestamp()}."
                    send_email(subject, body, recipients)
        else:
            log_message(f"[{timestamp()}] First-time check for {url}: storing baseline.", log_file, quiet)

        with open(cache_file, 'w') as f:
            f.write(current_hash)

        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor a website for changes.")
    parser.add_argument("url", help="The website URL or domain to monitor.")
    parser.add_argument("-t", "--time", type=int, default=60,
                        help="Time interval between checks in seconds (default: 60).")
    parser.add_argument("-l", "--log", type=str,
                        help="Optional log file name (default: domain.tld.log)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress console output.")
    parser.add_argument("-e", "--email", nargs='+',
                        help="Email address(es) to notify on changes.")

    args = parser.parse_args()
    log_file = get_log_filename(args.url, args.log)
    try:
        monitor_website(args.url, args.time, args.log, args.quiet, args.email)
    except KeyboardInterrupt:
        message = f"[{timestamp()}] Monitoring halted by user (^C)."
        if not args.quiet:
            print(message)
        with open(log_file, 'a') as f:
            f.write(message + '\n')

