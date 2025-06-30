#!/usr/bin/python3
# Description: A Python-GUI interface for the HAM Operator Test. 
# Usage: python3 ham-test-cli.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import json
import os
import random
import requests
import logging
from datetime import datetime
import tkinter as tk
from tkinter import messagebox

# --- Setup logging ---
logging.basicConfig(level=logging.WARNING, format='[%(levelname)s] %(message)s')

# --- URLs and Local file paths ---
URLS = {
    "Technician": "https://raw.githubusercontent.com/russolsen/ham_radio_question_pool/master/technician-2022-2026/technician.json",
    "General": "https://raw.githubusercontent.com/russolsen/ham_radio_question_pool/master/general-2023-2027/general.json",
    "Extra": "https://raw.githubusercontent.com/russolsen/ham_radio_question_pool/master/extra-2024-2028/extra.json"
}

LOCAL_FILES = {
    "Technician": "technician.json",
    "General": "general.json",
    "Extra": "extra.json"
}

# --- Helper functions to sync question files ---

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

def download_file(url, local_path):
    print(f"Downloading latest questions from {url} ...")
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    with open(local_path, "w", encoding='utf-8') as f:
        f.write(r.text)
    print(f"Saved to {local_path}")

def is_local_file_up_to_date(local_path, remote_timestamp):
    if not os.path.exists(local_path):
        return False
    local_mtime = os.path.getmtime(local_path)
    return local_mtime >= remote_timestamp

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

def load_questions(test_name):
    local_path = LOCAL_FILES[test_name]
    if not os.path.exists(local_path):
        print(f"Error: Local file {local_path} not found.")
        return []
    with open(local_path, "r", encoding='utf-8') as f:
        return json.load(f)

# --- GUI Classes ---

class QuizGUI:
    def __init__(self, master, questions):
        self.master = master
        self.master.title("HAM Radio Quiz")
        self.questions = questions
        random.shuffle(self.questions)

        self.score = 0
        self.total = 0
        self.current_index = -1
        self.correct_answer = None
        self.next_pending = False
        self.correct_answer_text = ""

        self.feedback_label = tk.Label(master, text="", font=("Arial", 14), wraplength=800, justify="left")
        self.feedback_label.pack(pady=5)

        self.question_label = tk.Label(master, text="", wraplength=600, justify="left", font=("Arial", 12))
        self.question_label.pack(padx=10, pady=10)

        self.selected_answer = tk.StringVar()
        self.answers_frame = tk.Frame(master)
        self.answers_frame.pack(pady=5)

        nav_frame = tk.Frame(master)
        nav_frame.pack(pady=10)

        self.next_button = tk.Button(nav_frame, text="Next", command=self.check_answer)
        self.next_button.pack(side=tk.LEFT, padx=5)

        self.quit_button = tk.Button(nav_frame, text="Quit", command=self.quit_quiz)
        self.quit_button.pack(side=tk.LEFT, padx=5)

        self.load_next_question()

    def resize_to_fit_text(self, text):
        avg_char_width = 7
        padding = 60
        max_width = 1000
        min_width = 400
        estimated_width = min(max(len(text) * avg_char_width + padding, min_width), max_width)
        self.master.geometry(f"{estimated_width}x400")

    def load_next_question(self):
        self.current_index += 1

        if self.current_index >= len(self.questions):
            pct = (self.score / self.total) * 100 if self.total > 0 else 0
            messagebox.showinfo("Quiz Finished", f"Score: {self.score}/{self.total} ({pct:.2f}%)")
            self.master.destroy()
            return

        self.feedback_label.config(text="")
        self.selected_answer.set(None)

        for widget in self.answers_frame.winfo_children():
            widget.destroy()

        q = self.questions[self.current_index]
        question_text = q.get("question")
        answers = q.get("answers", [])
        correct_index = q.get("correct")

        width = min(max(400, len(question_text) * 7), 800)
        self.master.geometry(f"{width}x400")
        self.question_label.config(text=question_text)

        options = list(enumerate(answers))
        random.shuffle(options)

        self.correct_answer = None
        self.correct_answer_text = ""
        for idx, (orig_index, ans_text) in enumerate(options):
            rb = tk.Radiobutton(
                self.answers_frame,
                text=ans_text,
                variable=self.selected_answer,
                value=ans_text,
                wraplength=width - 50,
                justify="left",
                anchor="w",
                padx=10,
                font=("Arial", 11)
            )
            rb.pack(anchor="w", pady=2)
            if orig_index == correct_index:
                self.correct_answer = ans_text
                self.correct_answer_text = ans_text

        self.next_pending = False

    def check_answer(self):
        if self.next_pending:
            return

        selected = self.selected_answer.get()
        if not selected:
            messagebox.showwarning("No Answer", "Please select an answer before proceeding.")
            return

        self.total += 1
        if selected == self.correct_answer:
            self.score += 1
            self.feedback_label.config(text="Correct!", fg="green")
            delay = 1500  # 1.5 sec
        else:
            feedback_text = f"Incorrect! The correct answer was: {self.correct_answer_text}"
            self.feedback_label.config(text=feedback_text, fg="red")
            self.resize_to_fit_text(feedback_text)
            delay = 3500  # 3.5 sec

        self.next_pending = True
        self.master.after(delay, self.load_next_question)

    def quit_quiz(self):
        pct = (self.score / self.total) * 100 if self.total > 0 else 0
        messagebox.showinfo("Quit Quiz", f"Questions answered: {self.total}\nCorrect: {self.score}\nPercentage: {pct:.2f}%")
        self.master.destroy()


class TestSelectGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("Select Test")
        self.selected_test = None

        label = tk.Label(master, text="Select the test you want to take:", font=("Arial", 14))
        label.pack(padx=10, pady=10)

        for test_name in URLS.keys():
            btn = tk.Button(master, text=test_name, width=20, command=lambda tn=test_name: self.select_test(tn))
            btn.pack(pady=5)

    def select_test(self, test_name):
        self.selected_test = test_name
        self.master.destroy()


def main():
    root = tk.Tk()
    select_gui = TestSelectGUI(root)
    root.mainloop()

    test_name = select_gui.selected_test
    if test_name is None:
        print("No test selected. Exiting.")
        return

    print(f"Selected test: {test_name}")
    print("Syncing question files...")
    sync_files()

    questions = load_questions(test_name)
    if not questions:
        print("No questions found.")
        return

    root = tk.Tk()
    app = QuizGUI(root, questions)
    root.mainloop()


if __name__ == "__main__":
    main()

