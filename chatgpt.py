#!/usr/bin/python3
# Description: A command-line interface to https://chat.openai.com/chat 
# Usage: python3 chatgpt.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import openai
import os
import sys
import shutil
import textwrap
from pathlib import Path
import colorama

colorama.init()

def get_api_key():
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        return api_key

    print("OpenAI API key not found.")
    print("Please paste your OpenAI API key below.")
    print("If you don't have one, you can create it here: https://platform.openai.com/account/api-keys")
    api_key = input("Enter your API key: ").strip()

    shell = os.getenv("SHELL", "")
    shell_config = None

    if "zsh" in shell:
        shell_config = Path.home() / ".zshrc"
    elif "bash" in shell:
        shell_config = Path.home() / ".bashrc"
    else:
        print("Unknown shell; please manually add the following to your shell config:")
        print(f'export OPENAI_API_KEY="{api_key}"')
        return api_key

    export_line = f'\nexport OPENAI_API_KEY="{api_key}"\n'

    try:
        with open(shell_config, "a") as f:
            f.write(export_line)
        print(f"✅ API key saved to {shell_config}. It will be available next time you launch the terminal.")
    except Exception as e:
        print(f"⚠️ Failed to save API key to {shell_config}: {e}")
        print("You can set it manually by adding:")
        print(f'export OPENAI_API_KEY="{api_key}"')

    return api_key

def show_help():
    help_text = """
    Available Commands:
    
    - 'new'       : Start a new conversation (clear the chat history).
    - 'exit', 'quit', 'bye' : End the conversation and exit the script.
    - 'help'      : Show this help message with a list of commands.
    - 'model'     : Show the current model or available models.
    - 'model=<model_name>' : Switch to the specified model (e.g., 'model=gpt-4').
    - 'output'    : Save the last ChatGPT response to a file (auto-named).
    - 'output=<filename>' : Save the last ChatGPT response to the given filename.
    """
    print(help_text)

def print_imessage(sender, text, is_user=False):
    cols = shutil.get_terminal_size().columns
    max_bubble_width = min(60, cols - 10)
    indent = cols - max_bubble_width - 6 if is_user else 2
    wrapper = textwrap.TextWrapper(width=max_bubble_width)
    lines = wrapper.wrap(text.strip())

    # Bubble color
    color = "\033[44m" if is_user else "\033[100m"  # Blue or Gray
    reset = "\033[0m"

    # Top and bottom border
    top = f"{color}╭{'─' * (max_bubble_width + 2)}╮{reset}"
    bottom = f"{color}╰{'─' * (max_bubble_width + 2)}╯{reset}"

    print(" " * indent + f"{sender}:")
    print(" " * indent + top)

    for line in lines:
        pad = " " * (max_bubble_width - len(line))
        print(" " * indent + f"{color}│ {line}{pad} │{reset}")

    print(" " * indent + bottom + "\n")

def chat_with_gpt():
    current_model = "gpt-3.5-turbo"
    available_models = ["gpt-3.5-turbo", "gpt-4"]
    last_response = ""

    print_imessage("ChatGPT", f"Hello. You are currently using the '{current_model}' model.\nType 'help' for a list of internal commands.", is_user=False)

    conversation_history = []

    while True:
        user_input = input("You: ").strip()
        print_imessage("You", user_input, is_user=True)

        if user_input.lower() == "help":
            show_help()
            continue

        if user_input.lower() == "new":
            print_imessage("ChatGPT", f"Starting a new conversation...\nHello. You are using the '{current_model}' model. How can I help you today?", is_user=False)
            conversation_history = []
            last_response = ""
            continue

        if user_input.lower() in ["exit", "quit", "bye"]:
            print_imessage("ChatGPT", "Goodbye!", is_user=False)
            break

        if user_input.lower().startswith("model="):
            model_name = user_input.split("=", 1)[1].strip()
            if model_name in available_models:
                current_model = model_name
                print_imessage("ChatGPT", f"Switched to the '{current_model}' model.", is_user=False)
            else:
                print_imessage("ChatGPT", f"'{model_name}' is not a valid model. Available models: {', '.join(available_models)}.", is_user=False)
            continue

        if user_input.lower() == "model":
            print_imessage("ChatGPT", f"You are currently using the '{current_model}' model.\nAvailable models: {', '.join(available_models)}.", is_user=False)
            continue

        if user_input.lower().startswith("output"):
            if not last_response:
                print_imessage("ChatGPT", "No response available to save.", is_user=False)
                continue

            def get_extension(content):
                if "```python" in content:
                    return "py"
                elif "```html" in content:
                    return "html"
                elif "```json" in content:
                    return "json"
                elif "```bash" in content:
                    return "sh"
                else:
                    return "txt"

            if "=" in user_input:
                filename = user_input.split("=", 1)[1].strip()
                if "." not in filename:
                    ext = get_extension(last_response)
                    filename = f"{filename}.{ext}"
            else:
                ext = get_extension(last_response)
                filename = f"chatgpt-output.{ext}"

            try:
                content = last_response
                if "```" in content:
                    content = content.split("```")[1]
                    if "\n" in content:
                        content = "\n".join(content.split("\n")[1:])
                    content = content.strip("`").strip()

                with open(filename, "w") as f:
                    f.write(content)
                print_imessage("ChatGPT", f"Output saved to '{filename}'", is_user=False)
            except Exception as e:
                print_imessage("ChatGPT", f"Failed to save output: {e}", is_user=False)
            continue

        conversation_history.append({"role": "user", "content": user_input})

        try:
            response = openai.ChatCompletion.create(
                model=current_model,
                messages=conversation_history,
                max_tokens=150
            )
            chatgpt_reply = response['choices'][0]['message']['content']
            print_imessage("ChatGPT", chatgpt_reply, is_user=False)
            last_response = chatgpt_reply
            conversation_history.append({"role": "assistant", "content": chatgpt_reply})
        except Exception as e:
            print_imessage("ChatGPT", f"Error: {e}", is_user=False)
            break

if __name__ == "__main__":
    openai.api_key = get_api_key()
    chat_with_gpt()

