#!/usr/bin/env python3
# Description: Monitor a website for changes.
# Usage: python3 diff-web.py --domain example.com
# Author: Justin Oros
# Source: https://github.com/JustinOros

import argparse
import hashlib
import os
import re
import sys
import time
from datetime import datetime
from getpass import getpass
from urllib.parse import urlparse

import requests
from requests.exceptions import ConnectionError, HTTPError, Timeout, RequestException
from bs4 import BeautifulSoup

def clean_text(text):
    junk_phrases = [
        r'\bMenu\b', r'\bClose\b', r'\bSign ?In\b', r'\bSign ?Out\b',
        r'\bLogin\b', r'\bLogout\b', r'\bBack\b', r'\bNext\b', r'\bMore\b',
        r'\bSearch\b', r'\bCart\b', r'\bSettings\b', r'\bHelp\b',
        r'\bContact\b', r'\bLanguage\b', r'\bProfile\b', r'\bAccount\b',
        r'\bSupport\b', r'\bUS\b', r'\bEN\b', r'\bFR\b', r'\bDE\b',
        r'\bJP\b', r'\bES\b', r'\bIT\b', r'\bCN\b', r'\b≡\b', r'\b×\b'
    ]

    text = re.sub(r'\b(?:US|EN|FR|DE|JP|ES|IT|CN)\b(\s*chevron_right\s*)+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'(chevron_right\s*){2,}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\bchevron_right\b', '', text, flags=re.IGNORECASE)

    for pattern in junk_phrases:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)

    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fetch_content_with_fallback(domain):
    """
    Try HTTPS first, if fails, fall back to HTTP.
    Return tuple (url_used, content)
    """
    parsed = urlparse(domain)
    netloc = parsed.netloc if parsed.netloc else parsed.path  # handles domain or full url input

    https_url = f"https://{netloc}"
    http_url = f"http://{netloc}"

    for url in [https_url, http_url]:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove unwanted tags
            for tag in soup(["script", "style", "noscript", "iframe", "svg", "canvas", "header", "footer", "nav", "form", "button"]):
                tag.decompose()

            keep_tags = ['h1', 'h2', 'h3', 'h4', 'p', 'li', 'article', 'section', 'span', 'div']
            for tag in soup.find_all(True):
                if tag.name not in keep_tags:
                    tag.decompose()

            raw_text = soup.get_text(separator=' ', strip=True)
            cleaned = clean_text(raw_text)
            return url, cleaned

        except (ConnectionError, HTTPError, Timeout, RequestException) as e:
            print(f"[!] Failed to fetch {url}: {e}")
            # Try next url in fallback loop
            continue

    raise Exception(f"Could not fetch content from HTTPS or HTTP for domain: {domain}")

def hash_content(content):
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def save_log(domain, content):
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d.%H%M%S")
    domain_name = domain.replace("https://", "").replace("http://", "").split("/")[0]
    filename = f"{domain_name}.{timestamp}.log"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] Change detected. Log saved to: {os.path.abspath(filename)}")

def prompt_credentials(args):
    try:
        # Prompt email if -e passed without value or empty string
        if args.email is not None and not args.email.strip():
            args.email = input("Enter your email: ").strip()

        # Prompt password only if email is set and password not provided
        if args.email and not args.password:
            args.password = getpass("Enter your password: ")

    except KeyboardInterrupt:
        print("\n[!] Input canceled by user. Exiting.")
        sys.exit(0)
    return args

def main():
    parser = argparse.ArgumentParser(description="Monitor a webpage for changes.")
    parser.add_argument("-d", "--domain", type=str, required=True, help="Domain to monitor (e.g., example.com)")
    parser.add_argument("--time", type=int, default=60, help="Polling interval in seconds (default: 60)")
    parser.add_argument("-e", "--email", nargs="?", const="", help="Your email address (optional prompt)")
    parser.add_argument("-p", "--password", nargs="?", const="", help="Your password (optional; will prompt if not provided)")

    args = parser.parse_args()
    args = prompt_credentials(args)

    domain = args.domain
    print(f"[+] Monitoring: {domain} every {args.time} seconds")
    if args.email:
        print(f"[+] Email: {args.email}")

    previous_hash = None
    current_url = None  # to remember actual URL used (https/http)

    while True:
        try:
            url_used, content = fetch_content_with_fallback(domain)
            current_url = url_used
            current_hash = hash_content(content)

            if previous_hash and current_hash != previous_hash:
                save_log(current_url, content)
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] No change.")

            previous_hash = current_hash

        except Exception as e:
            print(f"[!] Error: {e}")

        try:
            time.sleep(args.time)
        except KeyboardInterrupt:
            print("\n[!] Monitoring stopped by user. Goodbye!")
            sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Monitoring stopped by user. Goodbye!")
        sys.exit(0)

