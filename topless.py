#!/usr/bin/env python3
# Description: Display top system processes with less mess and more color.
# Usage: python3 topless.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import os
import time
import psutil
import sys
import select
import argparse
import tty
import termios
from shutil import get_terminal_size

def clear_screen():
    print("\033[H\033[J", end='')

def get_top_processes(limit=10, sort_key='cpu', reverse=True):
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username']):
        try:
            pinfo = proc.info
            processes.append({
                'cpu': pinfo['cpu_percent'] or 0.0,
                'mem': pinfo['memory_percent'] or 0.0,
                'name': pinfo['name'][:30] if pinfo['name'] else '',
                'user': pinfo['username'][:14] if pinfo['username'] else ''
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return sorted(processes, key=lambda x: x[sort_key], reverse=reverse)[:limit]

def colorize(cpu, mem, name, user, use_color=True, line_number=None, width=0):
    if not use_color:
        return f"{str(line_number).rjust(width)}  {cpu:5.1f}    {mem:5.1f}    {name:35}  {user:15}" if line_number else f"{cpu:5.1f}    {mem:5.1f}    {name:35}  {user:15}"

    if cpu >= 50:
        color = "\033[91m"  # red
    elif cpu >= 20:
        color = "\033[93m"  # yellow
    elif cpu >= 10:
        color = "\033[92m"  # green
    else:
        color = "\033[90m"  # gray

    RESET = "\033[0m"
    line = f"{cpu:5.1f}    {mem:5.1f}    {name:35}  {user:15}"
    if line_number is not None:
        return f"{color}{str(line_number).rjust(width)}  {line}{RESET}"
    return f"{color}{line}{RESET}"

def print_processes(limit, sort_key='cpu', reverse=True, show_quit_hint=True, use_color=True, show_line_numbers=False):
    clear_screen()
    top_processes = get_top_processes(limit, sort_key=sort_key, reverse=reverse)

    GREEN = "\033[32m" if use_color else ""
    RESET = "\033[0m" if use_color else ""
    UNDERLINE = "\033[4m" if use_color else ""
    RESET_UNDERLINE = "\033[24m" if use_color else ""
    ARROW_UP = "↑"
    ARROW_DOWN = "↓"

    BG_GRAY = "\033[100m" if use_color else ""
    BLACK_TEXT = "\033[30m" if use_color else ""

    arrow = ARROW_DOWN if reverse else ARROW_UP

    def col_label(col_key, label, width):
        if sort_key == col_key:
            return f"{arrow} {label}".ljust(width)
        else:
            return f"  {label}".ljust(width)

    cpu_col = col_label('cpu', "CPU", 7)
    mem_col = col_label('mem', "MEM", 5)
    name_col = col_label('name', "Process", 35)
    user_col = col_label('user', "User", 15)

    line_prefix = "Ln  " if show_line_numbers else ""
    header = f"{line_prefix}{cpu_col}  {mem_col}  {name_col}  {user_col}"

    print(f"{BG_GRAY}{BLACK_TEXT}{header.ljust(len(header))}{RESET}")

    width = len(str(limit))
    for i, proc in enumerate(top_processes, start=1):
        cpu = proc['cpu']
        mem = proc['mem']
        name = proc['name']
        user = proc['user']
        if show_line_numbers:
            line = colorize(cpu, mem, name, user, use_color, line_number=i, width=width)
        else:
            line = colorize(cpu, mem, name, user, use_color)
        print(line.ljust(len(header)))

    bottom_bar = "Sort: [C]PU [M]EM [P]rocess [U]ser or [Q]uit."
    if show_quit_hint:
        print(f"{BG_GRAY}{BLACK_TEXT}{bottom_bar.ljust(len(header))}{RESET}")
    else:
        print(f"{BG_GRAY}{' '.ljust(len(header))}{RESET}")

def timed_input(timeout=0.1):
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        rlist, _, _ = select.select([fd], [], [], timeout)
        if rlist:
            return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', type=int, help="Number of processes to display")
    parser.add_argument('--no-color', action='store_true', help="Disable color output")
    parser.add_argument('--lines', action='store_true', help="Show line numbers")
    args = parser.parse_args()

    use_color = not args.no_color
    show_line_numbers = args.lines

    term_height = get_terminal_size().lines
    limit = args.n if args.n else max(5, term_height - 10)

    sort_key = 'cpu'
    reverse = True
    refresh_count = 0
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        show_quit = True

        print_processes(limit, sort_key, reverse, show_quit, use_color, show_line_numbers)

        key = timed_input(1)
        refresh_count += 1

        if key:
            key = key.lower()
            if key == 'q':
                break
            elif key == 'c':
                reverse = not reverse if sort_key == 'cpu' else True
                sort_key = 'cpu'
            elif key == 'm':
                reverse = not reverse if sort_key == 'mem' else True
                sort_key = 'mem'
            elif key == 'p':
                reverse = not reverse if sort_key == 'name' else True
                sort_key = 'name'
            elif key == 'u':
                reverse = not reverse if sort_key == 'user' else True
                sort_key = 'user'
            elif key == 'r':
                reverse = not reverse

if __name__ == "__main__":
    main()

