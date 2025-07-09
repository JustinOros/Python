#!/usr/bin/python3
# Description: The Matrix Screensaver.
# Usage: python3 matrix.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import curses
import random
import time
import argparse
import sys

# Available colors (excluding black and white for regular text)
COLOR_NAMES = ['red', 'green', 'yellow', 'blue', 'purple', 'cyan']
COLOR_OPTIONS = COLOR_NAMES + ['rgb']  # 'rgb' cycles through colors every 5 seconds

# Mapping from color names to curses color constants
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
    # Initialize curses settings
    curses.curs_set(0)  # Hide the cursor
    curses.start_color()  # Enable color functionality
    curses.use_default_colors()  # Use default terminal background

    # Initialize color pairs for each available color
    for i, name in enumerate(COLOR_NAMES):
        curses.init_pair(i + 1, COLOR_MAP[name], -1)  # Foreground color, default background

    # Initialize variables for color cycling (for 'rgb' mode)
    color_index = 0
    current_color = COLOR_NAMES[color_index]
    next_color = current_color
    last_color_change = time.time()

    # Characters used in the Matrix rain effect (mix of ascii and Greek symbols)
    chars = (
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        "@#$%^&*()[]{}|;:,.<>?/~!_`'\"\\"
        "αβγδεζηθικλμνξοπρστυφχψω∑πΩΔ∫ƒ∞≡∧∨⊕⊗⊙"
    )

    # Signature string that appears as an easter egg every 30 seconds
    signature = "Justin Oros"
    signature_columns = {}  # Tracks column and starting Y-position of signature
    signature_visible = False
    signature_visible_until = 0
    last_signature_time = time.time()

    start_time = time.time()
    columns = []  # Y positions of falling characters for each column
    column_speeds = []  # Speed at which each column falls (some variation)
    column_colors = []  # Color of each column (for 'rgb' cycling)

    try:
        while True:
            now = time.time()
            if timeout and (now - start_time) > timeout:
                break  # Exit if timeout reached

            sh, sw = stdscr.getmaxyx()  # Get screen height and width

            # Initialize columns if screen width changes
            if len(columns) != sw:
                columns = [random.randint(0, sh - 1) for _ in range(sw)]
                column_speeds = [random.choice([1, 1, 2]) for _ in range(sw)]  # Mostly speed 1, sometimes 2
                column_colors = [current_color] * sw

            # Handle color cycling for 'rgb' mode every 5 seconds
            if color_mode == 'rgb' and (now - last_color_change >= 5):
                color_index = (color_index + 1) % len(COLOR_NAMES)
                next_color = COLOR_NAMES[color_index]
                last_color_change = now

            # Gradually switch column colors in 'rgb' mode with some randomness
            if color_mode == 'rgb':
                for i in range(sw):
                    if column_colors[i] != next_color and random.random() < 0.03:
                        column_colors[i] = next_color
            elif color_mode in COLOR_NAMES:
                column_colors = [color_mode] * sw

            # Show signature every 30 seconds for 5 seconds
            if not signature_visible and (now - last_signature_time >= 30):
                signature_columns.clear()
                col = random.randint(0, sw - len(signature))  # Random horizontal position
                y_start = random.randint(5, max(6, sh - len(signature)))  # Random vertical position within bounds
                signature_columns[col] = y_start
                signature_visible = True
                signature_visible_until = now + 5  # Display duration of 5 seconds
                last_signature_time = now

            # Hide signature after display time ends
            if signature_visible and now > signature_visible_until:
                signature_visible = False
                signature_columns.clear()

            stdscr.erase()  # Clear screen before drawing new frame

            for i in range(sw):
                x = i
                y = columns[i]
                speed = column_speeds[i]
                color_name = column_colors[i]
                color_id = COLOR_NAMES.index(color_name) + 1

                # Draw signature if visible in this column
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
                    # Draw normal falling characters with fade effect
                    char_string = ''.join(random.choice(chars) for _ in range(30))
                    for j in range(30):
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

                columns[i] = (columns[i] + speed) % sh  # Move column down for next frame

            stdscr.refresh()  # Update screen with changes
            time.sleep(0.05)  # Frame rate control (~20 FPS)

    except KeyboardInterrupt:
        pass  # Graceful exit on Ctrl+C

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

