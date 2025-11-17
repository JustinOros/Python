#!/usr/bin/python3
# Description: Searches for participant or team statistics from stats.distributed.net
# Usage: python3 stats-distributed-net.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import requests
from bs4 import BeautifulSoup
import sys
import json
import os
from datetime import datetime
from pathlib import Path


def get_history_file():
    """Return path to history file in user's home directory."""
    home = Path.home()
    return home / ".stats_distributed_net_history.json"


def load_last_search():
    """Load the last search term from history file."""
    history_file = get_history_file()
    if history_file.exists():
        try:
            with open(history_file, 'r') as f:
                data = json.load(f)
                return data.get('last_search', '')
        except Exception:
            return ''
    return ''


def save_last_search(search_term):
    """Save the search term to history file."""
    history_file = get_history_file()
    try:
        with open(history_file, 'w') as f:
            json.dump({'last_search': search_term}, f)
    except Exception as e:
        print(f"Warning: Could not save search history: {e}")


def get_projects():
    """Fetch available projects dynamically from stats.distributed.net and return {project_id: project_name}."""
    url = "https://stats.distributed.net/"

    # Known stable mapping used only if parsing misses anything
    KNOWN = {
        "3":  "RC5-56",
        "5":  "RC5-64",
        "8":  "RC5-72",
        "24": "OGR-24",
        "25": "OGR-25",
        "26": "OGR-26",
        "27": "OGR-27",
        "28": "OGR-28",
        "205": "RC5-64 (all)",
    }

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Error fetching projects: {e}")
        return KNOWN.copy()  # fallback to known values

    soup = BeautifulSoup(response.text, 'html.parser')
    projects = {}

    # Scrape any link with project_id= in the href
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)

        if "project_id=" in href:
            try:
                pid = href.split("project_id=")[1].split("&")[0]
                if pid:
                    # Prefer readable project text if meaningful
                    if text and any(text.startswith(prefix) for prefix in ("RC5", "OGR", "DES")):
                        projects[pid] = text
                    else:
                        projects[pid] = KNOWN.get(pid, text or f"Project {pid}")

            except Exception:
                continue

    # Ensure all known are included (fallback)
    for pid, name in KNOWN.items():
        if pid not in projects:
            projects[pid] = name

    # Notify if new project IDs appear so user can track future additions
    for pid, name in projects.items():
        if pid not in KNOWN:
            print(f"⚠️ New project detected on stats.distributed.net: ID={pid}, Name='{name}'")

    return dict(sorted(projects.items(), key=lambda x: int(x[0])))


def search_participant(project_id, search_term, debug=False):
    url = "https://stats.distributed.net/participant/psearch.php"
    params = {'project_id': project_id, 'st': search_term}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        if debug:
            with open('debug_participant.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("DEBUG: Saved response to debug_participant.html")

        return parse_results(response.text, 'participant')
    except Exception as e:
        print(f"Error searching participant: {e}")
        return None


def search_team(project_id, search_term, debug=False):
    url = "https://stats.distributed.net/team/tsearch.php"
    params = {'project_id': project_id, 'st': search_term}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()

        if debug:
            with open('debug_team.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("DEBUG: Saved response to debug_team.html")

        return parse_results(response.text, 'team')
    except Exception as e:
        print(f"Error searching team: {e}")
        return None


def parse_results(html, search_type):
    soup = BeautifulSoup(html, 'html.parser')
    results = []

    if 'psummary.php' in html or 'tsummary.php' in html:
        result = parse_stats_page(soup, search_type)
        if result:
            return [result]

    tables = soup.find_all('table')

    for table in tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 3:
                continue

            data = [cell.get_text(strip=True) for cell in cells]
            if not any(data):
                continue

            rank_text = data[0].replace(',', '').replace('(', '').replace(')', '').strip()
            if not rank_text.isdigit():
                continue

            name = data[1]
            days = data[2]
            overall = data[3] if len(data) > 3 else 'N/A'

            results.append({
                "name": name,
                "current_rank": rank_text,
                "overall_rank": rank_text,
                "updated": f"{days} days active" if days != 'N/A' else 'N/A',
                "overall_work": overall
            })

    return results or None


def parse_stats_page(soup, search_type):
    result = {}
    h1_tag = soup.find('h1', class_='phead')
    if h1_tag:
        text = h1_tag.get_text(strip=True)
        if "'s stats" in text:
            text = text.replace("'s stats", "").strip()
        result['name'] = text

    title_tag = soup.find('title')
    if 'name' not in result and title_tag:
        title_text = title_tag.get_text(strip=True)
        if ' for ' in title_text:
            result['name'] = title_text.split(' for ')[-1].strip()

    tables = soup.find_all('table', border='0')
    for table in tables:
        for row in table.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                if label == 'rank:':
                    overall = cells[1].get_text(strip=True)
                    result['overall_rank'] = overall
                    if len(cells) >= 3:
                        current = cells[2].get_text(strip=True).split('(')[0].strip()
                        result['current_rank'] = current
                    else:
                        result['current_rank'] = overall
                elif label == 'time working:':
                    result['time_working'] = cells[1].get_text(strip=True)

    last_update = soup.find('td', class_='lastupdate')
    if last_update:
        text = last_update.get_text(strip=True)
        if 'as of' in text:
            date_text = text.split('as of')[1].split('at')[0].strip()
            result['updated'] = date_text

    result.setdefault('name', 'Unknown')
    result.setdefault('overall_rank', 'N/A')
    result.setdefault('current_rank', result['overall_rank'])
    result.setdefault('updated', 'N/A')

    return result if result['name'] != 'Unknown' else None


def get_input_with_default(prompt, default_value):
    """Display a prompt with a default value that can be edited."""
    if default_value:
        prompt_text = f"{prompt} [{default_value}]: "
    else:
        prompt_text = f"{prompt}: "
    
    user_input = input(prompt_text).strip()
    
    # If user just presses Enter and there's a default, use it
    if not user_input and default_value:
        return default_value
    
    return user_input


def main():
    print("=" * 60)
    print("Distributed.net Statistics Search Tool")
    print("=" * 60)
    print("\nFetching project list from stats.distributed.net ...")

    projects = get_projects()

    print("\nAvailable Projects:")
    project_items = list(projects.items())
    for i, (pid, name) in enumerate(project_items, 1):
        print(f"{i}. {name} (ID: {pid})")

    while True:
        choice = input("\nSelect project number (press Enter for RC5-72): ").strip()
        if choice == "":
            project_id = "8"
            break
        if choice.isdigit() and 1 <= int(choice) <= len(project_items):
            project_id = project_items[int(choice)-1][0]
            break
        print(f"Enter a number between 1 and {len(project_items)}")

    print("\n1. Participant (User)")
    print("2. Team")
    while True:
        search_type = input("\nSelect search type (1 or 2): ").strip()
        if search_type in ("1", "2"):
            break
        print("Invalid choice")

    # Load last search and offer it as default
    last_search = load_last_search()
    search_term = get_input_with_default("\nEnter search term", last_search)
    
    if not search_term:
        print("Search term cannot be empty.")
        return

    # Save this search for next time
    save_last_search(search_term)

    debug = '--debug' in sys.argv

    print(f"\nSearching '{search_term}'...\nPlease wait...")

    results = search_participant(project_id, search_term, debug) if search_type == "1" else search_team(project_id, search_term, debug)

    print("\n" + "=" * 60)
    print("SEARCH RESULTS")
    print("=" * 60)

    if not results:
        print("\nNo results found.")
    else:
        for result in results:
            print(f"\nName: {result['name']}")
            print(f"Current Rank: {result['current_rank']}")
            print(f"Overall Rank: {result['overall_rank']}")
            print(f"Updated: {result['updated']}")
            if "time_working" in result:
                print(f"Time Working: {result['time_working']}")
            if "overall_work" in result:
                print(f"Total Work Units: {result['overall_work']}")
            print("-" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
