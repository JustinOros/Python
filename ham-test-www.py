#!/usr/bin/env python3
# Description: A Python script that generates a HAM Operator Test in a web browser.
# Usage: python3 ham-test-www.py
# Author: Justin Oros

import json
import os
import requests
import logging
import webbrowser
from datetime import datetime

logging.basicConfig(level=logging.WARNING, format='[%(levelname)s] %(message)s')

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
            dt = datetime.strptime(r.headers['Last-Modified'], '%a, %d %b %Y %H:%M:%S %Z')
            return dt.timestamp()
    except Exception as e:
        logging.warning(f"Could not fetch Last-Modified for {url}: {e}")
    return None

def download_file(url, local_path):
    print(f"Downloading {url} ...")
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    with open(local_path, 'w', encoding='utf-8') as f:
        f.write(r.text)
    print(f"Saved to {local_path}")

def sync_files():
    for name, url in URLS.items():
        local = LOCAL_FILES[name]
        remote_ts = get_remote_last_modified(url)
        if remote_ts is None:
            if not os.path.exists(local):
                download_file(url, local)
            else:
                print(f"Skipping update for {name} (no remote timestamp)")
        elif not os.path.exists(local) or os.path.getmtime(local) < remote_ts:
            download_file(url, local)
        else:
            print(f"{local} is up to date.")

def load_all_questions():
    all_questions = {}
    for name, path in LOCAL_FILES.items():
        with open(path, 'r', encoding='utf-8') as f:
            all_questions[name] = json.load(f)
    return all_questions

def generate_html(questions):
    options_html = "\n".join(f'<option value="{name}">{name}</option>' for name in questions)
    data_json = json.dumps(questions)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>HAM Radio Test</title>
  <style>
    body {{
      font-family: sans-serif;
      background-color: #ffffff;
      color: #000000;
      margin: 20px;
      transition: background-color 0.3s, color 0.3s;
    }}
    .dark-mode {{
      background-color: #121212;
      color: #ffffff;
    }}
    .question-box {{
      background: #fff;
      padding: 1rem;
      border-radius: 8px;
      box-shadow: 0 0 10px rgba(0,0,0,0.1);
      margin-bottom: 2rem;
    }}
    .dark-mode .question-box {{
      background: #1e1e1e;
      box-shadow: 0 0 10px rgba(255,255,255,0.05);
    }}
    .answers label {{
      display: block;
      margin: 0.5rem 0;
    }}
    .nav-buttons {{
      margin-top: 1rem;
    }}
    .nav-buttons button {{
      margin-right: 0.5rem;
    }}
    .correct {{ color: limegreen; }}
    .incorrect {{ color: tomato; }}
    #result {{ font-weight: bold; }}
    .settings {{
      position: fixed;
      top: 10px;
      right: 10px;
      z-index: 100;
    }}
    .gear-icon {{
      font-size: 24px;
      cursor: pointer;
    }}
    .settings-menu {{
      display: none;
      position: absolute;
      top: 30px;
      right: 0;
      background: #f0f0f0;
      border: 1px solid #ccc;
      padding: 10px;
      border-radius: 8px;
      font-size: 14px;
      width: 100px;
      white-space: nowrap;
    }}
    .settings-menu.dark {{
      background: #2a2a2a;
      color: white;
      border-color: #555;
    }}
    .settings:hover .settings-menu {{
      display: block;
    }}
    .settings-menu input {{
      margin-right: 6px;
    }}
  </style>
</head>
<body>
  <div class="settings">
    <span class="gear-icon">&#9881;</span>
    <div class="settings-menu" id="settingsMenu">
      <label><input type="radio" name="theme" value="light" checked> Light Mode</label><br>
      <label><input type="radio" name="theme" value="dark"> Dark Mode</label>
    </div>
  </div>

  <h1>HAM Radio Test</h1>
  <p>Select a test pool:</p>
  <select id="testSelect">
    {options_html}
  </select>
  <button onclick="startTest()">Start</button>

  <div id="quiz" style="display:none;"></div>

  <script>
    const data = {data_json};
    let current = 0, score = 0, selectedTest = '', shuffled = [];
    let quitRequested = false;

    function startTest() {{
      selectedTest = document.getElementById("testSelect").value;
      shuffled = [...data[selectedTest]].sort(() => 0.5 - Math.random());
      current = 0;
      score = 0;
      quitRequested = false;
      document.getElementById("quiz").style.display = "block";
      showQuestion();
    }}

    function showQuestion() {{
      if (current >= shuffled.length) {{
        document.getElementById("quiz").innerHTML = `<h2>Finished!</h2><p id="result">Score: ${{score}} / ${{shuffled.length}} (${{((score / shuffled.length) * 100).toFixed(2)}}%)</p>`;
        return;
      }}

      const q = shuffled[current];
      const options = q.answers.map((a, i) => {{
        return `<label><input type="radio" name="ans" value="${{i}}"> ${{a}}</label>`;
      }}).join("");

      document.getElementById("quiz").innerHTML = `
        <div class="question-box">
          <h2>Question ${{current + 1}} of ${{shuffled.length}}</h2>
          <p>${{q.question}}</p>
          <div class="answers">${{options}}</div>
          <div class="nav-buttons">
            <button onclick="quitTest()">Quit</button>
            <button id="submitBtn" onclick="submitAnswer(${{q.correct}})">Submit</button>
          </div>
        </div>`;
    }}

    function submitAnswer(correct) {{
      const radios = document.getElementsByName("ans");
      let selected = -1;
      for (let i = 0; i < radios.length; i++) {{
        if (radios[i].checked) {{
          selected = parseInt(radios[i].value);
        }}
        radios[i].disabled = true;
      }}

      if (selected === -1) {{
        alert("Please select an answer.");
        return;
      }}

      const submitBtn = document.getElementById("submitBtn");
      if (submitBtn) submitBtn.disabled = true;

      const isCorrect = selected === correct;
      if (isCorrect) score++;

      const feedback = isCorrect
        ? '<p class="correct">Correct!</p>'
        : `<p class="incorrect">Incorrect. Correct answer was: ${{shuffled[current].answers[correct]}}</p>`;

      document.querySelector(".question-box").innerHTML += feedback;

      setTimeout(() => {{
        if (!quitRequested) {{
          current++;
          showQuestion();
        }}
      }}, isCorrect ? 1000 : 2500);
    }}

    function quitTest() {{
      quitRequested = true;
      const answered = current;
      const percent = answered > 0 ? ((score / answered) * 100).toFixed(0) : 0;
      document.getElementById("quiz").innerHTML = `
        <h1>Test Score</h1>
        <p>You answered ${{score}} questions correctly out of ${{answered}} questions answered. (${{percent}}%)</p>
      `;
    }}

    const body = document.body;
    const settingsMenu = document.getElementById('settingsMenu');
    const radios = settingsMenu.querySelectorAll('input[name="theme"]');

    radios.forEach(radio => {{
      radio.addEventListener('change', () => {{
        if (radio.value === 'dark') {{
          body.classList.add('dark-mode');
          settingsMenu.classList.add('dark');
        }} else {{
          body.classList.remove('dark-mode');
          settingsMenu.classList.remove('dark');
        }}
      }});
    }});
  </script>
</body>
</html>
"""
    return html

def write_html_file(content, filename="ham-test.html"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"HTML quiz written to: {filename}")
    webbrowser.open(f"file://{os.path.abspath(filename)}")

def main():
    print("Syncing questions...")
    sync_files()
    print("Loading questions...")
    questions = load_all_questions()
    html = generate_html(questions)
    write_html_file(html)

if __name__ == "__main__":
    main()

