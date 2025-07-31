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

def supports_color():
    if not sys.stdout.isatty():
        return False
    term = os.environ.get('TERM', '')
    if 'color' in term.lower():
        return True
    if os.name == 'nt':
        return True
    return False

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_top_processes(limit):
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

def colorize(cpu, name, user, use_color):
    limit = 35
    if len(name) > limit:
        display_name = name[:limit - 3] + "..."
    else:
        display_name = name

    if cpu <= 25 or not use_color:
        return f"{cpu:6.2f}%  {display_name:<35}  {user[:15]:<15}"
    else:
        YELLOW = "\033[33m"
        ORANGE = "\033[38;5;214m"
        RED = "\033[31m"
        RESET_TO_GREEN = "\033[32m"
        color = YELLOW if cpu <= 50 else ORANGE if cpu <= 75 else RED
        cpu_str = f"{cpu:6.2f}%"
        return f"{color}{cpu_str}  {display_name:<35}  {user[:15]:<15}{RESET_TO_GREEN}"

def print_processes(limit, show_quit_hint=True, use_color=True):
    clear_screen()
    top_processes = get_top_processes(limit)

    GREEN = "\033[32m" if use_color else ""

    if use_color:
        print(GREEN, end='')

    print(" CPU     Process                               User")
    print("----------------------------------------------------------")
    
    for (cpu, name, user) in top_processes:
        print(colorize(cpu, name, user, use_color))

    if show_quit_hint:
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
    parser.add_argument("--no-color", action="store_true", help="Disable colored output.")
    args = parser.parse_args()
    limit = args.number
    interval = max(1, args.interval)

    use_color = not args.no_color and supports_color()

    refresh_count = 0
    start_time = time.time()

    try:
        while True:
            refresh_count += 1
            elapsed = time.time() - start_time
            show_quit = refresh_count < 3 and elapsed < 3
            print_processes(limit, show_quit_hint=show_quit, use_color=use_color)
            key = wait_for_keypress(timeout=interval)
            if key and key.lower() == 'q':
                print("Exiting...")
                break
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")

if __name__ == "__main__":
    main()

