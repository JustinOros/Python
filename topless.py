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
import shutil

first_run = True
current_sort_key = 'cpu'
reverse_sort = True

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
    global first_run
    if first_run:
        os.system('cls' if os.name == 'nt' else 'clear')
        first_run = False
    else:
        print("\033[H", end='')

def get_top_processes(limit, sort_key='cpu', reverse=True):
    for proc in psutil.process_iter(['pid']):
        try:
            proc.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    time.sleep(0.1)

    processes = []
    for proc in psutil.process_iter(['cpu_percent', 'memory_percent', 'name', 'username']):
        try:
            cpu = proc.info['cpu_percent']
            mem = proc.info['memory_percent']
            name = proc.info['name']
            user = proc.info['username']
            processes.append({'cpu': cpu, 'mem': mem, 'name': name, 'user': user})
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    processes = [
        p for p in processes
        if p['cpu'] is not None and
           p['mem'] is not None and
           p['name'] is not None and
           p['user'] is not None
    ]

    processes.sort(key=lambda p: p[sort_key], reverse=reverse)
    return processes[:limit]

def colorize(cpu, mem, name, user, use_color, line_number=None, width=0):
    name_limit = 35
    if len(name) > name_limit:
        display_name = name[:name_limit - 3] + "..."
    else:
        display_name = name

    if not use_color:
        prefix = f"{line_number:0{width}d}: " if line_number is not None else ""
        return f"{prefix}{cpu:6.2f}%  {mem:6.2f}%  {display_name:<35}  {user[:15]:<15}"

    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_ORANGE = "\033[48;5;214m"
    BG_RED = "\033[41m"
    BLACK_TEXT = "\033[30m"
    RESET = "\033[0m"

    if cpu <= 25:
        bg_color = BG_GREEN
    elif cpu <= 50:
        bg_color = BG_YELLOW
    elif cpu <= 75:
        bg_color = BG_ORANGE
    else:
        bg_color = BG_RED

    prefix = f"{line_number:0{width}d}: " if line_number is not None else ""
    line = f"{bg_color}{BLACK_TEXT}{prefix}{cpu:6.2f}%  {mem:6.2f}%  {display_name:<35}  {user[:15]:<15}{RESET}"
    return line

def print_processes(limit, sort_key='cpu', reverse=True, show_quit_hint=True, use_color=True, show_line_numbers=False):
    clear_screen()
    top_processes = get_top_processes(limit, sort_key=sort_key, reverse=reverse)

    GREEN = "\033[32m" if use_color else ""
    RESET = "\033[0m" if use_color else ""
    UNDERLINE = "\033[4m" if use_color else ""
    RESET_UNDERLINE = "\033[24m" if use_color else ""
    ARROW_UP = "↑"
    ARROW_DOWN = "↓"

    arrow = ARROW_DOWN if reverse else ARROW_UP

    def col_label(col_key, label, width):
        if sort_key == col_key:
            return f"{arrow} {label}".ljust(width)
        else:
            return f"  {label}".ljust(width)

    cpu_col = col_label('cpu', "CPU", 7)
    mem_col = col_label('mem', "MEM", 6)
    name_col = col_label('name', "Process", 35)
    user_col = col_label('user', "User", 15)

    line_prefix = "Ln  " if show_line_numbers else ""
    header = f"{line_prefix}{cpu_col}  {mem_col}  {name_col}  {user_col}"
    separator = '-' * (len(header) + 1)
    term_width = shutil.get_terminal_size((80, 20)).columns

    print(f"{GREEN}{header.ljust(term_width)}{RESET}")
    print(f"{GREEN}{separator.ljust(term_width)}{RESET}")

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
        print(line.ljust(term_width))

    print(f"{GREEN}{separator.ljust(term_width)}{RESET}")
    if show_quit_hint:
        print((
            f"\n{GREEN}Sort: "
            f"[{UNDERLINE}C{RESET_UNDERLINE}]PU "
            f"[{UNDERLINE}M{RESET_UNDERLINE}]EM "
            f"[{UNDERLINE}P{RESET_UNDERLINE}]rocess "
            f"[{UNDERLINE}U{RESET_UNDERLINE}]ser or "
            f"[{UNDERLINE}Q{RESET_UNDERLINE}]uit."
        ).ljust(term_width))

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

class SortedHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    def add_arguments(self, actions):
        actions = sorted(actions, key=lambda a: a.option_strings)
        super().add_arguments(actions)

def main():
    global current_sort_key, reverse_sort

    parser = argparse.ArgumentParser(
        description="Monitor system processes by CPU and memory usage.",
        formatter_class=SortedHelpFormatter
    )
    parser.add_argument("-i", "--interval", type=int, default=1, help="Refresh interval in seconds.")
    parser.add_argument("-l", "--line", action="store_true", help="Show line numbers.")
    parser.add_argument("-n", "--number", type=int, default=10, help="Number of processes to monitor.")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output.")
    args = parser.parse_args()

    limit = args.number
    interval = max(1, args.interval)

    use_color = not args.no_color and supports_color()
    show_lines = args.line

    refresh_count = 0
    start_time = time.time()

    try:
        while True:
            refresh_count += 1
            elapsed = time.time() - start_time
            show_quit = refresh_count < 3 and elapsed < 3
            print_processes(
                limit,
                sort_key=current_sort_key,
                reverse=reverse_sort,
                show_quit_hint=show_quit,
                use_color=use_color,
                show_line_numbers=show_lines
            )

            key = wait_for_keypress(timeout=interval)
            if key:
                key = key.lower()
                if key == 'q':
                    break
                elif key in ['c', 'm', 'p', 'u']:
                    key_map = {'c': 'cpu', 'm': 'mem', 'p': 'name', 'u': 'user'}
                    chosen_sort = key_map[key]
                    if current_sort_key == chosen_sort:
                        reverse_sort = not reverse_sort
                    else:
                        current_sort_key = chosen_sort
                        reverse_sort = True
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting...")

if __name__ == "__main__":
    main()

