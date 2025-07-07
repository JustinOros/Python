#!/usr/bin/python3
# Description: A command-line interface to https://chat.openai.com/chat 
# Usage: python3 chatgpt.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import openai
import os

# Function to get the OpenAI API key
def get_api_key():
    # Check if API key is set in environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        # If API key is not in environment variables, prompt the user to enter it
        print("OpenAI API key not found.")
        print("Please paste your OpenAI API key below.")
        print("If you don't have one, you can create it here: https://platform.openai.com/account/api-keys")
        api_key = input("Enter your API key: ").strip()

    # Set the OpenAI API key
    openai.api_key = api_key

def show_help():
    help_text = """
    Available Commands:
    
    - 'new'       : Start a new conversation (clear the chat history).
    - 'exit'      : End the conversation and exit the script.
    - 'quit'      : Same as 'exit', ends the conversation.
    - 'bye'       : Same as 'exit', ends the conversation.
    - 'help'      : Show this help message with a list of commands.
    - 'model'     : Show the current model or available models.
    - 'model=<model_name>' : Switch to the specified model (e.g., 'model=gpt-4').
    """
    print(help_text)

def chat_with_gpt():
    # Default model
    current_model = "gpt-3.5-turbo"
    
    print(f"ChatGPT: Hello. You are currently using the '{current_model}' model.")
    print("Type 'help' for a list of internal commands.")

    # A basic conversation loop
    conversation_history = []  # Store conversation to maintain context

    while True:
        # Get input from the user
        user_input = input("User: ")

        # Show help message
        if user_input.lower() == "help":
            show_help()
            continue

        # Check if the user wants to start a new conversation
        if user_input.lower() == "new":
            print("ChatGPT: Starting a new conversation...")
            conversation_history = []  # Reset the conversation history
            print(f"ChatGPT: Hello. You are using the '{current_model}' model. How can I help you today?")
            continue

        # Check if the user wants to exit the conversation
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("ChatGPT: Goodbye!")
            break

        # Check if the user wants to change the model
        if user_input.lower().startswith("model="):
            model_name = user_input.split("=")[1].strip()

            if model_name in available_models:
                current_model = model_name
                print(f"ChatGPT: Switched to the '{current_model}' model.")
            else:
                print(f"ChatGPT: '{model_name}' is not a valid model. Available models are: {', '.join(available_models)}.")
            continue

        # Check if the user wants to see the current model or available models
        if user_input.lower() == "model":
            print(f"ChatGPT: You are currently using the '{current_model}' model.")
            print(f"Available models: {', '.join(available_models)}.")
            continue

        # Add user input to conversation history
        conversation_history.append({"role": "user", "content": user_input})

        try:
            # Call OpenAI's GPT model
            response = openai.ChatCompletion.create(
                model=current_model,  # Use the current model
                messages=conversation_history,
                max_tokens=150
            )

            # Extract and print the response
            chatgpt_reply = response['choices'][0]['message']['content']
            print(f"ChatGPT: {chatgpt_reply}")

            # Add ChatGPT's reply to the conversation history
            conversation_history.append({"role": "assistant", "content": chatgpt_reply})

        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    # First, ensure the OpenAI API key is available
    get_api_key()
    # Start the chat
    chat_with_gpt()

