#!/usr/bin/python3
# Description: A Python GUI interface for the HAM Operator Test.
# Usage: python3 ham-test-gui.py
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

# Setup logging
logging.basicConfig(level=logging.WARNING, format='[%(levelname)s] %(message)s')

# URLs and Local file paths
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

class HamTestGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("HAM Radio Test")
        self.center_window(800, 300)
        self.master.resizable(False, False)

        self.questions = []
        self.score = 0
        self.total = 0
        self.current_index = -1
        self.correct_answer = None
        self.correct_answer_text = ""
        self.next_pending = False

        self.history = []
        self.in_review_mode = False

        self.content_frame = tk.Frame(self.master)
        self.content_frame.pack(fill="both", expand=True)

        self.show_test_selection()

    def center_window(self, width=800, height=600):
        self.master.update_idletasks()
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.master.geometry(f"{width}x{height}+{x}+{y}")

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def show_test_selection(self):
        self.clear_content()
        label = tk.Label(self.content_frame, text="Select the test you want to take:", font=("Arial", 14))
        label.pack(padx=10, pady=10)

        for test_name in URLS.keys():
            btn = tk.Button(self.content_frame, text=test_name, width=20, font=("Arial", 12),
                            command=lambda tn=test_name: self.start_test(tn))
            btn.pack(pady=5)

    def start_test(self, test_name):
        print(f"Selected test: {test_name}")
        print("Syncing question files...")
        sync_files()

        questions = load_questions(test_name)
        if not questions:
            messagebox.showerror("Error", f"No questions found for {test_name}.")
            return

        self.questions = questions
        random.shuffle(self.questions)
        self.score = 0
        self.total = 0
        self.current_index = -1
        self.history = []
        self.in_review_mode = False
        self.show_question()

    def show_question(self):
        self.clear_content()
        if not self.in_review_mode:
            self.current_index += 1

        if self.current_index >= len(self.questions):
            pct = (self.score / self.total) * 100 if self.total > 0 else 0
            messagebox.showinfo("Quiz Finished", f"Score: {self.score}/{self.total} ({pct:.2f}%)")
            self.master.destroy()
            return

        q = self.questions[self.current_index]
        question_text = q.get("question")
        answers = q.get("answers", [])
        correct_index = q.get("correct")

        self.feedback_label = tk.Label(self.content_frame, text="", font=("Arial", 14), wraplength=780, justify="left")
        self.feedback_label.pack(pady=5)

        self.question_label = tk.Label(self.content_frame, text=question_text, wraplength=780, justify="left", font=("Arial", 12))
        self.question_label.pack(padx=10, pady=10)

        self.selected_answer = tk.StringVar()
        self.answers_frame = tk.Frame(self.content_frame)
        self.answers_frame.pack(pady=5)

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
                wraplength=760,
                justify="left",
                anchor="w",
                padx=10,
                font=("Arial", 11)
            )
            rb.pack(anchor="w", pady=2)
            if orig_index == correct_index:
                self.correct_answer = ans_text
                self.correct_answer_text = ans_text

        nav_frame = tk.Frame(self.content_frame)
        nav_frame.pack(pady=10)

        self.back_button = tk.Button(nav_frame, text="←", command=self.go_back, font=("Arial", 14))
        self.back_button.pack(side=tk.LEFT, padx=5)
        if self.current_index == 0:
            self.back_button.config(state="disabled")

        self.quit_button = tk.Button(nav_frame, text="Quit", command=self.quit_quiz)
        self.quit_button.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(nav_frame, text="→", command=self.check_answer, font=("Arial", 14))
        self.next_button.pack(side=tk.LEFT, padx=5)

        self.next_pending = False

        if self.in_review_mode:
            self.next_button.config(text="→", command=self.exit_review_mode, state="normal")
            selected = None
            was_correct = False
            for h in self.history:
                if h["index"] == self.current_index:
                    selected = h["selected"]
                    was_correct = h["correct"]
                    break
            self.selected_answer.set(selected)
            for child in self.answers_frame.winfo_children():
                child.config(state="disabled")
            if was_correct:
                self.feedback_label.config(text="Correct (Previously answered)", fg="green")
            else:
                self.feedback_label.config(
                    text=f"Incorrect. The correct answer was: {self.correct_answer_text}", fg="red"
                )

    def check_answer(self):
        if self.next_pending:
            return

        selected = self.selected_answer.get()
        if not selected:
            messagebox.showwarning("No Answer", "Please select an answer before proceeding.")
            return

        self.total += 1
        is_correct = selected == self.correct_answer
        if is_correct:
            self.score += 1
            self.feedback_label.config(text="Correct!", fg="green")
            delay = 1500
        else:
            self.feedback_label.config(text=f"Incorrect! The correct answer was: {self.correct_answer_text}", fg="red")
            delay = 3500

        self.history.append({
            "index": self.current_index,
            "selected": selected,
            "correct": is_correct
        })

        self.next_pending = True
        self.master.after(delay, self.show_question)

    def go_back(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.in_review_mode = True
            self.show_question()

    def exit_review_mode(self):
        self.in_review_mode = False
        self.show_question()

    def quit_quiz(self):
        pct = (self.score / self.total) * 100 if self.total > 0 else 0
        messagebox.showinfo("Quit Quiz", f"Questions answered: {self.total}\nCorrect: {self.score}\nPercentage: {int(pct)}%")
        self.master.destroy()

def main():
    root = tk.Tk()
    app = HamTestGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()

