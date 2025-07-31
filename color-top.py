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
import tty
import termios

GREEN = "\033[32m"
YELLOW = "\033[33m"
ORANGE = "\033[38;5;214m"
RED = "\033[31m"
RESET = "\033[0m"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_top_processes(limit):
    # Prime cpu_percent readings
    for proc in psutil.process_iter(['pid']):
        try:
            proc.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    time.sleep(0.1)

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
    cpu_str = f"{cpu:6.2f}%"
    return f"{color}{cpu_str}  {name[:25]:<25}  {user[:15]:<15}{RESET}"

def print_processes(limit):
    clear_screen()
    top_processes = get_top_processes(limit)

    print(" CPU%    Process                    User")
    print("----------------------------------------------")
    
    for (cpu, name, user) in top_processes:
        print(colorize(cpu, name, user))

    print("\nPress 'q' to quit.")

def wait_for_keypress(timeout=1.0):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        if select.select([sys.stdin], [], [], timeout)[0]:
            return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return None

def main():
    parser = argparse.ArgumentParser(description="Monitor system processes by CPU usage.")
    parser.add_argument("-n", "--number", type=int, default=10, help="Number of processes to monitor (default is 10).")
    parser.add_argument("-i", "--interval", type=int, default=1, help="Refresh interval in seconds (default is 1).")
    args = parser.parse_args()
    limit = args.number
    interval = max(1, args.interval)

    try:
        while True:
            print_processes(limit)
            key = wait_for_keypress(timeout=interval)
            if key and key.lower() == 'q':
                print("Exiting...")
                break
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")

if __name__ == "__main__":
    main()

