#!/usr/bin/python3
# Description: A command-line interface to https://chat.openai.com/chat 
# Usage: python3 chatgpt.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import openai
import os
import sys
from pathlib import Path

def get_api_key():
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        return api_key

    # Prompt user for input
    print("OpenAI API key not found.")
    print("Please paste your OpenAI API key below.")
    print("If you don't have one, you can create it here: https://platform.openai.com/account/api-keys")
    api_key = input("Enter your API key: ").strip()

    # Save the key to shell config for next time
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

def chat_with_gpt():
    current_model = "gpt-3.5-turbo"
    available_models = ["gpt-3.5-turbo", "gpt-4"]
    last_response = ""

    print(f"ChatGPT: Hello. You are currently using the '{current_model}' model.")
    print("Type 'help' for a list of internal commands.")

    conversation_history = []

    while True:
        user_input = input("User: ")

        if user_input.lower() == "help":
            show_help()
            continue

        if user_input.lower() == "new":
            print("ChatGPT: Starting a new conversation...")
            conversation_history = []
            last_response = ""
            print(f"ChatGPT: Hello. You are using the '{current_model}' model. How can I help you today?")
            continue

        if user_input.lower() in ["exit", "quit", "bye"]:
            print("ChatGPT: Goodbye!")
            break

        if user_input.lower().startswith("model="):
            model_name = user_input.split("=", 1)[1].strip()
            if model_name in available_models:
                current_model = model_name
                print(f"ChatGPT: Switched to the '{current_model}' model.")
            else:
                print(f"ChatGPT: '{model_name}' is not a valid model. Available models are: {', '.join(available_models)}.")
            continue

        if user_input.lower() == "model":
            print(f"ChatGPT: You are currently using the '{current_model}' model.")
            print(f"Available models: {', '.join(available_models)}.")
            continue

        if user_input.lower().startswith("output"):
            if not last_response:
                print("ChatGPT: No response available to save.")
                continue

            # Determine extension based on code block
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

            # Parse optional filename
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
                    # Extract only the content within the triple backticks
                    content = content.split("```")[1]
                    if "\n" in content:
                        content = "\n".join(content.split("\n")[1:])
                    content = content.strip("`").strip()

                with open(filename, "w") as f:
                    f.write(content)
                print(f"ChatGPT: Output saved to '{filename}'")
            except Exception as e:
                print(f"ChatGPT: Failed to save output: {e}")
            continue

        conversation_history.append({"role": "user", "content": user_input})

        try:
            response = openai.ChatCompletion.create(
                model=current_model,
                messages=conversation_history,
                max_tokens=150
            )
            chatgpt_reply = response['choices'][0]['message']['content']
            print(f"ChatGPT: {chatgpt_reply}")
            last_response = chatgpt_reply
            conversation_history.append({"role": "assistant", "content": chatgpt_reply})
        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    openai.api_key = get_api_key()
    chat_with_gpt()

