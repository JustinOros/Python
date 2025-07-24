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
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from datetime import datetime
from bs4 import BeautifulSoup, Comment

# List of known tracking parameters to strip
TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'fbclid', 'gclid', 'mc_cid', 'mc_eid', 'ref', 'ref_src'
}

def normalize_url(url):
    if not urlparse(url).scheme:
        url = 'https://' + url
    return strip_tracking_params(url)

def strip_tracking_params(url):
    parsed = urlparse(url)
    clean_query = [(k, v) for k, v in parse_qsl(parsed.query) if k not in TRACKING_PARAMS]
    new_query = urlencode(clean_query)
    return urlunparse(parsed._replace(query=new_query))

def fetch_content(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text

def clean_content(html):
    soup = BeautifulSoup(html, 'html.parser')

    # Remove dynamic or non-content elements
    for tag in soup(['script', 'style', 'noscript', 'meta']):
        tag.decompose()

    # Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove tracking params from all anchor links
    for a in soup.find_all('a', href=True):
        a['href'] = strip_tracking_params(a['href'])

    # Get visible text, normalize whitespace
    text = soup.get_text(separator=' ', strip=True)
    return ' '.join(text.split())

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

def timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_message(message, log_file, quiet=False):
    if not quiet:
        print(message)
    with open(log_file, 'a') as f:
        f.write(message + '\n')

def monitor_website(url, interval, log_file_override=None, max_checks=None, quiet=False):
    url = normalize_url(url)
    domain = urlparse(url).netloc
    log_file = get_log_filename(url, log_file_override)
    cache_file = get_cache_filename(url)

    log_message(f"[{timestamp()}] Monitoring {domain}", log_file, quiet)

    checks_done = 0

    while True:
        try:
            raw_html = fetch_content(url)
            cleaned_text = clean_content(raw_html)
            current_hash = get_hash(cleaned_text)
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
        else:
            log_message(f"[{timestamp()}] First-time check for {url}: storing baseline.", log_file, quiet)

        with open(cache_file, 'w') as f:
            f.write(current_hash)

        checks_done += 1
        if max_checks is not None and checks_done >= max_checks:
            log_message(f"[{timestamp()}] Reached max checks ({max_checks}). Stopping.", log_file, quiet)
            break

        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor a website for changes.")
    parser.add_argument("url", help="The website URL or domain to monitor.")
    parser.add_argument("-t", "--time", type=int, default=60,
                        help="Time interval between checks in seconds (default: 60).")
    parser.add_argument("-l", "--log", type=str,
                        help="Optional log file name (default: domain.tld.log)")
    parser.add_argument("-c", "--count", type=int,
                        help="Optional number of times to check before stopping.")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Quiet mode: suppress console output")

    args = parser.parse_args()
    try:
        monitor_website(args.url, args.time, args.log, args.count, args.quiet)
    except KeyboardInterrupt:
        log_file = get_log_filename(args.url, args.log)
        log_message(f"[{timestamp()}] Monitoring stopped by user (KeyboardInterrupt).", log_file, args.quiet)

