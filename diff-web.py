#!/usr/bin/env python3
# Description: Monitor a website for changes.
# Usage: python3 diff-web.py https://example.com --time 300 --email user@example.com --hook https://example.com/webhook
# Author: Justin Oros
# Source: https://github.com/JustinOros

import requests
import hashlib
import os
import time
import sys
import argparse
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from datetime import datetime
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
import getpass  # For secure SNMP password input

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = os.getenv("EMAIL_USER")
SMTP_PASSWORD = os.getenv("EMAIL_PASS")
EMAIL_FROM = SMTP_USERNAME

sys.argv = [arg if not arg.startswith('/') else '-' + arg[1:] for arg in sys.argv]

parser = argparse.ArgumentParser(description="Monitor a website for changes.", add_help=False)
parser.add_argument("--help", action="help", help="Show this help message and exit")
parser.add_argument("url", nargs='?', help="The website URL or domain to monitor.")
parser.add_argument("-d", "--domain", help="Domain to monitor.")
parser.add_argument("-t", "--time", type=int, default=60,
                    help="Time interval between checks in seconds (default: 60).")
parser.add_argument("-l", "--log", type=str,
                    help="Optional log file name (default: domain.tld.log)")
parser.add_argument("-q", "--quiet", action="store_true",
                    help="Suppress console output.")
parser.add_argument("-e", "--email", nargs='+',
                    help="Email address(es) to notify on changes.")
parser.add_argument("-h", "--hook", type=str,
                    help="Webhook URL to POST to on changes.")

args = parser.parse_args()

# Prompt for SNMP password securely
SNMP_PASSWORD = getpass.getpass("Enter SNMP password: ")

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
    if not domain:
        domain = url.replace("://", "_").replace("/", "_")
        if not domain:
            domain = "monitor"
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

def send_webhook(url, payload):
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send webhook to {url}: {e}")

def monitor_website(url, interval, log_file, quiet=False, recipients=None, webhook_url=None):
    url = normalize_url(url)
    domain = urlparse(url).netloc
    cache_file = get_cache_filename(url)
    if not os.path.exists(log_file):
        with open(log_file, 'w') as f:
            pass
    initial_message = f"[{timestamp()}] Monitoring {domain}"
    if not quiet:
        print(initial_message)
    with open(log_file, 'a') as f:
        f.write(initial_message + '\n')
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
                if webhook_url:
                    payload = {
                        "url": url,
                        "domain": domain,
                        "timestamp": timestamp(),
                        "message": "Change detected on monitored website."
                    }
                    send_webhook(webhook_url, payload)
        else:
            log_message(f"[{timestamp()}] First-time check for {url}: storing baseline.", log_file, quiet)
        with open(cache_file, 'w') as f:
            f.write(current_hash)
        time.sleep(interval)

target = args.domain if args.domain else args.url
if not target:
    parser.error("You must specify a URL/domain to monitor either as positional argument or with -d/--domain.")
if not urlparse(target).scheme:
    target = "https://" + target
log_file = get_log_filename(target, args.log)
if not os.path.exists(log_file):
    print(f"Log file created at {os.path.abspath(log_file)}")
try:
    monitor_website(target, args.time, log_file, args.quiet, args.email, args.hook)
except KeyboardInterrupt:
    message = f"[{timestamp()}] Monitoring halted by user (^C)."
    if not args.quiet:
        print(message)
    with open(log_file, 'a') as f:
        f.write(message + '\n')

