#!/usr/bin/env python3
# Description: The Matrix Screensaver.
# Usage: python3 matrix.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import curses
import random
import time
import argparse
import sys

COLOR_NAMES = ['red', 'green', 'yellow', 'blue', 'purple', 'cyan']
COLOR_OPTIONS = COLOR_NAMES + ['random', 'cycle']

COLOR_MAP = {
    'black': curses.COLOR_BLACK,
    'red': curses.COLOR_RED,
    'green': curses.COLOR_GREEN,
    'yellow': curses.COLOR_YELLOW,
    'blue': curses.COLOR_BLUE,
    'purple': curses.COLOR_MAGENTA,
    'cyan': curses.COLOR_CYAN,
    'white': curses.COLOR_WHITE,
}

def matrix_rain(stdscr, color_mode, timeout=None):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()
    stdscr.nodelay(True)
    stdscr.keypad(True)

    for i, name in enumerate(COLOR_NAMES):
        curses.init_pair(i + 1, COLOR_MAP[name], -1)

    if color_mode in COLOR_NAMES:
        color_index = COLOR_NAMES.index(color_mode)
    else:
        color_index = COLOR_NAMES.index('green')

    current_color = COLOR_NAMES[color_index]
    next_color = current_color
    last_color_change = time.time()
    manual_color_control = False

    chars = (
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        "@#$%^&*()[]{}|;:,.<>?/~!_`'\"\\"
        "αβγδεζηθικλμνξοπρστυφχψω∑πΩΔ∫ƒ∞≡∧∨⊕⊗⊙"
    )

    signature = "Justin Oros"
    signature_columns = {}
    signature_visible = False
    signature_visible_until = 0
    last_signature_time = time.time()

    start_time = time.time()
    columns = []
    column_speeds = []
    column_colors = []

    try:
        while True:
            now = time.time()
            if timeout and (now - start_time) > timeout:
                break

            key = stdscr.getch()
            if key == curses.KEY_RIGHT:
                manual_color_control = True
                color_index = (color_index + 1) % len(COLOR_NAMES)
                current_color = COLOR_NAMES[color_index]
                next_color = current_color
                column_colors = [current_color] * len(column_colors)
            elif key == curses.KEY_LEFT:
                manual_color_control = True
                color_index = (color_index - 1) % len(COLOR_NAMES)
                current_color = COLOR_NAMES[color_index]
                next_color = current_color
                column_colors = [current_color] * len(column_colors)
            elif key == 3:
                break

            sh, sw = stdscr.getmaxyx()

            if len(columns) != sw:
                columns = [random.randint(0, sh - 1) for _ in range(sw)]
                column_speeds = [random.choice([1, 1, 2]) for _ in range(sw)]
                column_colors = [current_color] * sw

            if color_mode == 'random' and not manual_color_control and (now - last_color_change >= 5):
                color_index = (color_index + 1) % len(COLOR_NAMES)
                next_color = COLOR_NAMES[color_index]
                last_color_change = now

            if color_mode == 'cycle' and not manual_color_control and (now - last_color_change >= 0.1):
                color_index = (color_index + 1) % len(COLOR_NAMES)
                current_color = COLOR_NAMES[color_index]
                column_colors = [current_color] * sw
                last_color_change = now

            if color_mode == 'random' and not manual_color_control:
                for i in range(sw):
                    if column_colors[i] != next_color and random.random() < 0.03:
                        column_colors[i] = next_color
            elif color_mode != 'cycle':
                column_colors = [current_color] * sw

            if not signature_visible and (now - last_signature_time >= 30):
                signature_columns.clear()
                col = random.randint(0, sw - len(signature))
                y_start = random.randint(5, max(6, sh - len(signature)))
                signature_columns[col] = y_start
                signature_visible = True
                signature_visible_until = now + 5
                last_signature_time = now

            if signature_visible and now > signature_visible_until:
                signature_visible = False
                signature_columns.clear()

            stdscr.erase()

            for i in range(sw):
                x = i
                y = columns[i]
                speed = column_speeds[i]
                color_name = column_colors[i]
                color_id = COLOR_NAMES.index(color_name) + 1

                rain_length = 30

                if signature_visible and i in signature_columns:
                    y_start = signature_columns[i]
                    for j, ch in enumerate(signature):
                        pos_y = (y_start + j) % sh
                        try:
                            attr = curses.color_pair(color_id) | curses.A_BOLD
                            stdscr.addstr(pos_y, i, ch, attr)
                        except curses.error:
                            pass
                else:
                    char_string = ''.join(random.choice(chars) for _ in range(rain_length))
                    for j in range(rain_length):
                        fade_y = (y - j) % sh
                        if 0 <= fade_y < sh:
                            try:
                                if j == 0:
                                    attr = curses.color_pair(color_id) | curses.A_BOLD
                                elif j < 10:
                                    attr = curses.color_pair(color_id)
                                else:
                                    attr = curses.color_pair(color_id) | curses.A_DIM
                                stdscr.addstr(fade_y, x, char_string[j], attr)
                            except curses.error:
                                pass

                columns[i] = (columns[i] + speed) % sh

            stdscr.refresh()
            time.sleep(0.05)

    except KeyboardInterrupt:
        pass

def main():
    parser = argparse.ArgumentParser(
        description="Matrix Screensaver - Simulate falling code in the terminal",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('-c', '--color', type=str, default='green',
                        help="Set the falling text color (use -l to list options)")
    parser.add_argument('-t', '--timeout', type=int, default=None,
                        help="Exit after N seconds (optional)")
    parser.add_argument('-l', '--list-colors', action='store_true',
                        help="List available color options and exit")
    args = parser.parse_args()

    if args.list_colors:
        print("Available colors:")
        for color in COLOR_OPTIONS:
            print(f"  - {color}")
        sys.exit(0)

    chosen_color = args.color.lower()
    if chosen_color not in COLOR_OPTIONS:
        print(f"Error: Invalid color '{chosen_color}'. Use -l to list available options.")
        sys.exit(1)

    curses.wrapper(lambda stdscr: matrix_rain(stdscr, chosen_color, args.timeout))

if __name__ == "__main__":
    main()

