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

CONFIG_PATH = os.path.expanduser('~/.topless')

DEFAULT_CONFIG = {
    'text_color': 'black',
    'bar_color': 'gray',
    'low_value': 0,
    'low_color': 'gray',
    'medium_value': 25,
    'medium_color': 'yellow',
    'medium_high_value': 50,
    'medium_high_color': 'orange',
    'high_value': 75,
    'high_color': 'red',
}

ANSI_COLORS = {
    'black': "\033[30m",
    'red': "\033[91m",
    'green': "\033[92m",
    'yellow': "\033[93m",
    'blue': "\033[94m",
    'magenta': "\033[95m",
    'cyan': "\033[96m",
    'white': "\033[97m",
    'gray': "\033[90m",
    'orange': "\033[38;5;214m",
}

ANSI_BG_COLORS = {
    'black': "\033[40m",
    'red': "\033[41m",
    'green': "\033[42m",
    'yellow': "\033[43m",
    'blue': "\033[44m",
    'magenta': "\033[45m",
    'cyan': "\033[46m",
    'white': "\033[47m",
    'gray': "\033[100m",
    'orange': "\033[48;5;214m",
}

def load_or_create_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'w') as f:
            for k, v in DEFAULT_CONFIG.items():
                f.write(f"{k}={v}\n")

    config = DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or '=' not in line or line.startswith('#'):
                    continue
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip()
                if key in config:
                    if key.endswith('_value'):
                        try:
                            config[key] = float(val)
                        except ValueError:
                            pass
                    else:
                        config[key] = val.lower()
    except Exception:
        pass
    return config

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

def colorize(cpu, mem, name, user, config, use_color=True, line_number=None, width=0):
    if not use_color:
        return f"{str(line_number).rjust(width)}  {cpu:5.1f}    {mem:5.1f}    {name:35}  {user:15}" if line_number else f"{cpu:5.1f}    {mem:5.1f}    {name:35}  {user:15}"

    if cpu >= config['high_value']:
        color = ANSI_COLORS.get(config['high_color'], "\033[91m")
    elif cpu >= config['medium_high_value']:
        color = ANSI_COLORS.get(config['medium_high_color'], "\033[38;5;214m")
    elif cpu >= config['medium_value']:
        color = ANSI_COLORS.get(config['medium_color'], "\033[93m")
    elif cpu >= config['low_value']:
        color = ANSI_COLORS.get(config['low_color'], "\033[90m")
    else:
        color = ANSI_COLORS.get(config['text_color'], "\033[30m")

    RESET = "\033[0m"
    line = f"{cpu:5.1f}    {mem:5.1f}    {name:35}  {user:15}"
    if line_number is not None:
        return f"{color}{str(line_number).rjust(width)}  {line}{RESET}"
    return f"{color}{line}{RESET}"

def print_processes(limit, sort_key='cpu', reverse=True, show_quit_hint=True, use_color=True, show_line_numbers=False, config=None):
    if config is None:
        config = DEFAULT_CONFIG

    clear_screen()
    top_processes = get_top_processes(limit, sort_key=sort_key, reverse=reverse)

    BG_GRAY = ANSI_BG_COLORS.get(config['bar_color'], "\033[100m") if use_color else ""
    BLACK_TEXT = ANSI_COLORS.get(config['text_color'], "\033[30m") if use_color else ""
    ARROW_UP = "↑"
    ARROW_DOWN = "↓"
    arrow = ARROW_DOWN if reverse else ARROW_UP

    def col_label(col_key, label, width):
        return f"{arrow if sort_key == col_key else ' '} {label}".ljust(width)

    cpu_col = col_label('cpu', "CPU", 6)
    mem_col = col_label('mem', "MEM", 6)
    name_col = col_label('name', "PROC", 35)
    user_col = col_label('user', "USER", 15)
    line_prefix = "Ln  " if show_line_numbers else ""
    header = f"{line_prefix}{cpu_col}  {mem_col}  {name_col}  {user_col}"

    term_width = get_terminal_size().columns
    block_width = len(header)
    padding = max((term_width - block_width) // 2, 0)
    pad = ' ' * padding

    print(f"{pad}{BG_GRAY}{BLACK_TEXT}{header}\033[0m")

    width = len(str(limit))
    line_number_fmt = f"{{:0{width}d}}"

    for i, proc in enumerate(top_processes, start=1):
        cpu = proc['cpu']
        mem = proc['mem']
        name = proc['name']
        user = proc['user']
        if show_line_numbers:
            formatted_line_number = line_number_fmt.format(i)
            line = colorize(cpu, mem, name, user, config, use_color, line_number=formatted_line_number, width=width)
        else:
            line = colorize(cpu, mem, name, user, config, use_color)
        print(f"{pad}{line}")

    bottom_bar = "PRESS [C]PU [M]EM [P]ROC [U]SER TO SORT OR [Q]UIT."
    footer = bottom_bar if show_quit_hint else ' '
    centered_footer = footer.center(block_width)
    print(f"{pad}{BG_GRAY}{BLACK_TEXT}{centered_footer}\033[0m")

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
    parser.add_argument('-l', '--lines', action='store_true', help="Show line numbers")
    args = parser.parse_args()

    config = load_or_create_config()
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
        print_processes(limit, sort_key, reverse, show_quit, use_color, show_line_numbers, config=config)

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

