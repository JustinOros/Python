#!/usr/bin/python3
# Description: A command-line interface for the HAM Operator Test. 
# Usage: python3 ham-test.py
# Author: Justin Oros
# Source: https://github.com/JustinOros
# Dependencies: pip install requests

import json
import os
import random
import requests
from datetime import datetime

# URLs to download the latest official HAM exam question pools from GitHub
URLS = {
    "Technician": "https://raw.githubusercontent.com/russolsen/ham_radio_question_pool/master/technician-2022-2026/technician.json",
    "General": "https://raw.githubusercontent.com/russolsen/ham_radio_question_pool/master/general-2023-2027/general.json",
    "Extra": "https://raw.githubusercontent.com/russolsen/ham_radio_question_pool/master/extra-2024-2028/extra.json"
}

# Corresponding local filenames for each question pool
LOCAL_FILES = {
    "Technician": "technician.json",
    "General": "general.json",
    "Extra": "extra.json"
}

# Get the Last-Modified timestamp of a remote file, used to detect updates
def get_remote_last_modified(url):
    try:
        r = requests.head(url, timeout=10)
        if r.status_code == 200 and 'Last-Modified' in r.headers:
            lm = r.headers['Last-Modified']
            dt = datetime.strptime(lm, '%a, %d %b %Y %H:%M:%S %Z')
            return dt.timestamp()
    except Exception as e:
        print(f"Warning: Could not get Last-Modified for {url}: {e}")
    return None

# Download the file from GitHub and save it locally
def download_file(url, local_path):
    print(f"Downloading latest questions from {url} ...")
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    with open(local_path, "w", encoding='utf-8') as f:
        f.write(r.text)
    print(f"Saved to {local_path}")

# Determine whether the local file is newer than the remote version
def is_local_file_up_to_date(local_path, remote_timestamp):
    if not os.path.exists(local_path):
        return False
    local_mtime = os.path.getmtime(local_path)
    return local_mtime >= remote_timestamp

# Sync all 3 test pools with the GitHub repo (if newer versions exist)
def sync_files():
    for test_name, url in URLS.items():
        local_path = LOCAL_FILES[test_name]
        remote_ts = get_remote_last_modified(url)
        if remote_ts is None:
            if not os.path.exists(local_path):
                print(f"No local file for {test_name} and unable to get remote timestamp. Downloading anyway.")
                download_file(url, local_path)
            else:
                print(f"Skipping update for {test_name} (no remote timestamp).")
        else:
            if not is_local_file_up_to_date(local_path, remote_ts):
                download_file(url, local_path)
            else:
                print(f"{local_path} is up to date.")

# Load questions from the locally stored JSON file
def load_questions(test_name):
    local_path = LOCAL_FILES[test_name]
    if not os.path.exists(local_path):
        print(f"Error: Local file {local_path} not found.")
        return []
    with open(local_path, "r", encoding='utf-8') as f:
        return json.load(f)

# Prompt the user to select one of the 3 test pools
def select_test():
    print("Select the test you want to take:")
    for idx, name in enumerate(URLS.keys(), start=1):
        print(f"{idx}. {name} Class")
    choice = input("Enter number: ").strip()
    try:
        return list(URLS.keys())[int(choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice. Try again.\n")
        return select_test()

# Core quiz loop: presents questions, checks answers, tracks score
def run_quiz(questions):
    score = 0
    total = 0
    random.shuffle(questions)  # Randomize question order each session
    print("\nPress 'Q' at any time to quit.\n")

    for q in questions:
        question_text = q.get("question")
        answers = q.get("answers", [])
        correct_index = q.get("correct")

        # Skip if the structure is invalid
        if not question_text or not answers or correct_index is None:
            continue

        # Assign A, B, C, D... letters to each answer option
        letter_map = {chr(65 + i): ans for i, ans in enumerate(answers)}

        print(f"\n{question_text}")
        for letter, ans in letter_map.items():
            print(f"  {letter}. {ans}")

        # Get the user's answer
        while True:
            user_input = input("Your answer (A/B/C/D or Q to quit): ").strip().upper()
            if user_input == 'Q':
                print("Exiting test.")
                print(f"Final score: {score}/{total}")
                return
            if user_input in letter_map:
                selected_index = ord(user_input) - 65
                break
            else:
                print("Invalid input. Please enter A, B, C, D or Q.")

        # Score the answer
        total += 1
        if selected_index == correct_index:
            print("✅ Correct!\n")
            score += 1
        else:
            correct_letter = chr(65 + correct_index)
            correct_answer = answers[correct_index]
            print(f"❌ Incorrect. The correct answer is {correct_letter}. {correct_answer}\n")

    print(f"Test completed. Score: {score}/{total} ({(score/total)*100:.1f}%)")

# Main program flow
def main():
    print("Syncing question files...")
    sync_files()
    test_name = select_test()
    questions = load_questions(test_name)
    if not questions:
        print("No questions found.")
        return
    run_quiz(questions)

if __name__ == "__main__":
    main()

