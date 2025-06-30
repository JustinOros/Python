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
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.WARNING, format='[%(levelname)s] %(message)s')

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
        logging.warning(f"Could not get Last-Modified for {url}: {e}")
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
                print(f"{local_path} is outdated, updating it.")
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
def select_test(attempts=3):
    # Prompt user to select an exam type
    print("Select the test you want to take:")
    for idx, name in enumerate(URLS.keys(), start=1):
        print(f"{idx}. {name} Class")
    
    while attempts > 0:
        choice = input("Enter number: ").strip()
        try:
            return list(URLS.keys())[int(choice) - 1]
        except (ValueError, IndexError):
            attempts -= 1
            print(f"Invalid choice. You have {attempts} attempts left.\n")
    
    print("Too many invalid attempts. Exiting.")
    exit(1)

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
        if correct_index < 0 or correct_index >= len(answers):
            logging.warning(f"Skipping question with invalid correct index: {question_text}")
            continue

        # Pair each answer with whether it is correct
        answer_options = [(i, ans, i == correct_index) for i, ans in enumerate(answers)]
        random.shuffle(answer_options)  # Shuffle answer order

        # Create a letter map from shuffled options
        letter_map = {}
        correct_letter = None
        for idx, (orig_index, ans_text, is_correct) in enumerate(answer_options):
            letter = chr(65 + idx)
            letter_map[letter] = (orig_index, ans_text)
            if is_correct:
                correct_letter = letter
                correct_answer = ans_text

        print(f"\n{question_text}")
        for letter in sorted(letter_map.keys()):
            print(f"  {letter}. {letter_map[letter][1]}")

        # Get the user's answer
        while True:
            user_input = input("Your answer (A/B/C/D or Q to quit): ").strip().upper()
            if user_input == 'Q':
                print("Exiting test.")
                print(f"Final score: {score}/{total}")
                return
            if user_input in letter_map:
                break
            else:
                print("Invalid input. Please enter A, B, C, D or Q.")

        # Score the answer
        total += 1
        selected_index = letter_map[user_input][0]
        if selected_index == correct_index:
            print("✅ Correct!\n")
            score += 1
        else:
            print(f"❌ Incorrect. The correct answer is {correct_letter}. {correct_answer}\n")

    percentage = (score / total) * 100 if total > 0 else 0
    print(f"Test completed. Score: {score}/{total} ({percentage:.2f}%)")

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
