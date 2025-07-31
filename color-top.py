#!/usr/bin/env python3
# Description: Displays top system processes with color.
# Usage: python3 color-top.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import os
import time
import psutil
import sys
import select
import socket
import argparse

GREEN = "\033[32m"
YELLOW = "\033[33m"
ORANGE = "\033[38;5;214m"
RED = "\033[31m"
RESET = "\033[0m"

def get_top_processes(limit):
    processes = []
    for proc in psutil.process_iter(['cpu_percent', 'name', 'username']):
        try:
            cpu = proc.info['cpu_percent']
            if cpu is not None:
                processes.append((cpu, proc.info['name'], proc.info['username']))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    processes.sort(reverse=True, key=lambda p: p[0])
    return processes[:limit]

def colorize(cpu, name, user):
    color = GREEN if cpu <= 25 else YELLOW if cpu <= 50 else ORANGE if cpu <= 75 else RED
    cpu_str = f"{cpu:.2f}%"  # Displaying CPU usage with 2 decimal places
    return f"{color}{cpu_str}, {name}, {user}{RESET}"

def print_processes(limit):
    os.system('clear')
    top_processes = get_top_processes(limit)
    hostname = socket.gethostname()

    header = f"Top {limit} Running Processes ({hostname}):"
    print(header)
    print("-" * len(header))
    
    for idx, (cpu, name, user) in enumerate(top_processes, start=1):
        print(colorize(cpu, name, user))

def main():
    parser = argparse.ArgumentParser(description="Monitor system processes by CPU usage.")
    parser.add_argument("-n", "--number", type=int, default=10, help="Number of processes to monitor (default is 10).")
    
    args = parser.parse_args()
    limit = args.number
    
    try:
        while True:
            print_processes(limit)
            time.sleep(1)

            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                input_char = sys.stdin.read(1)
                if input_char.lower() == 'q':
                    print("Exiting...")
                    break
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")

if __name__ == "__main__":
    main()

