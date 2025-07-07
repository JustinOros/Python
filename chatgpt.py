import openai
import os
import sys
import shutil
import textwrap
from pathlib import Path
import colorama
import readline

colorama.init()

def get_api_key():
    # Check if API key is already set in the current environment
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    # If the key isn't found, check if it's in the .zshrc or .bashrc file
    shell = os.getenv("SHELL", "")
    shell_config = None

    if "zsh" in shell:
        shell_config = Path.home() / ".zshrc"
    elif "bash" in shell:
        shell_config = Path.home() / ".bashrc"
    else:
        print("Unknown shell; please manually add the following to your shell config:")
        print(f'export OPENAI_API_KEY="your-api-key"')
        return None

    if shell_config.exists():
        content = shell_config.read_text()
        if "OPENAI_API_KEY" in content:
            print(f"API key found in {shell_config}, but it may not be loaded into your current session.")
            print("Please restart your terminal session or manually run `source ~/.zshrc` or `source ~/.bashrc`.")
            return None

    # If not found, prompt the user for an API key
    print("OpenAI API key not found.")
    print("Please paste your OpenAI API key below.")
    print("If you don't have one, you can create it here: https://platform.openai.com/account/api-keys")
    api_key = input("Enter your API key: ").strip()

    export_line = f'\nexport OPENAI_API_KEY="{api_key}"\n'
    try:
        if shell_config.exists():
            content = shell_config.read_text()
            if api_key in content:
                print(f"API key already present in {shell_config}.")
                return api_key
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
- 'bye'       : End the conversation and exit the script.
- 'help'      : Show this help message with a list of commands.
- 'model'     : Show the current model or available models.
- 'model=<model_name>' : Switch to the specified model (e.g., 'model=gpt-4').
- 'output'    : Save the last ChatGPT response to a file (auto-named).
- 'output=<filename>' : Save the last ChatGPT response to the given filename.
- 'attach=<filename>' : Attach a local file's contents and send it as part of the conversation.
"""
    print(help_text)

def print_imessage(sender, text, is_user=False):
    cols = shutil.get_terminal_size().columns
    max_bubble_width = min(60, cols - 10)
    indent = cols - max_bubble_width - 6 if is_user else 2
    wrapper = textwrap.TextWrapper(width=max_bubble_width)
    lines = wrapper.wrap(text.strip())

    color = "\033[44m" if is_user else "\033[100m"
    reset = "\033[0m"
    top = f"{color}╭{'─' * (max_bubble_width + 2)}╮{reset}"
    bottom = f"{color}╰{'─' * (max_bubble_width + 2)}╯{reset}"

    print(" " * indent + top)
    for line in lines:
        pad = " " * (max_bubble_width - len(line))
        print(" " * indent + f"{color}│ {line}{pad} │{reset}")
    print(" " * indent + bottom + "\n")

def read_input_silently(prompt="You: "):
    try:
        print(prompt, end="", flush=True)
        user_input = input()
        sys.stdout.write("\033[F\033[K")  # Move cursor up and clear line
        return user_input.strip()
    except EOFError:
        return ""

def chat_with_gpt():
    current_model = "gpt-3.5-turbo"
    available_models = ["gpt-3.5-turbo", "gpt-4"]
    last_response = ""

    print_imessage("ChatGPT", f"Hello. You are currently using the '{current_model}' model.\nType 'help' for a list of internal commands.", is_user=False)

    conversation_history = []

    while True:
        user_input = read_input_silently()
        if not user_input:
            continue

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
                    parts = content.split("```")
                    if len(parts) >= 3:
                        content = parts[2].strip()
                    else:
                        content = content.strip("`").strip()

                with open(filename, "w") as f:
                    f.write(content)
                print_imessage("ChatGPT", f"Output saved to '{filename}'", is_user=False)
            except Exception as e:
                print_imessage("ChatGPT", f"Failed to save output: {e}", is_user=False)
            continue

        if user_input.lower().startswith("attach="):
            filepath = user_input.split("=", 1)[1].strip()
            if not os.path.isfile(filepath):
                print_imessage("ChatGPT", f"File not found: {filepath}", is_user=False)
                continue
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    file_content = f.read()
                file_message = f"[Attached file: {os.path.basename(filepath)}]\n```\n{file_content}\n```"
                conversation_history.append({"role": "user", "content": file_message})
                print_imessage("ChatGPT", f"File '{os.path.basename(filepath)}' attached and sent.", is_user=False)
            except Exception as e:
                print_imessage("ChatGPT", f"Failed to read file '{filepath}': {e}", is_user=False)
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
    if openai.api_key:
        chat_with_gpt()

