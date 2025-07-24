#!/usr/bin/env python3
# Description: Monitor a website for changes. 
# Usage: python3 diff-web.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import requests
import hashlib
import os
import time
import argparse
from urllib.parse import urlparse
from datetime import datetime

def normalize_url(url):
    if not urlparse(url).scheme:
        url = 'https://' + url
    return url

def fetch_content(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text

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

def log_message(message, log_file):
    print(message)
    with open(log_file, 'a') as f:
        f.write(message + '\n')

def monitor_website(url, interval, log_file_override=None):
    url = normalize_url(url)
    domain = urlparse(url).netloc
    log_file = get_log_filename(url, log_file_override)
    cache_file = get_cache_filename(url)

    log_message(f"[{datetime.now()}] Monitoring {domain}", log_file)

    while True:
        try:
            current_content = fetch_content(url)
            current_hash = get_hash(current_content)
        except Exception as e:
            log_message(f"[{datetime.now()}] [ERROR] Failed to fetch {url}: {e}", log_file)
            time.sleep(interval)
            continue

        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                old_hash = f.read().strip()
            if current_hash != old_hash:
                msg = f"[{datetime.now()}] Change detected on {url}"
                log_message(msg, log_file)
                with open(cache_file, 'w') as f:
                    f.write(current_hash)
        else:
            msg = f"[{datetime.now()}] First-time check for {url}: storing baseline."
            log_message(msg, log_file)
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

    args = parser.parse_args()
    monitor_website(args.url, args.time, args.log)

