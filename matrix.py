#!/usr/bin/python3
# Description: The Matrix Screensaver.
# Usage: python3 matrix.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import curses
import random
import time
import argparse

# Main function that runs the Matrix screensaver
def matrix_rain(stdscr, color_pair):
    # Hide the cursor
    curses.curs_set(0)
    # Start color support and use default colors
    curses.start_color()
    curses.use_default_colors()

    # Initialize color pair for the text (foreground) color
    curses.init_pair(1, color_pair, -1)  # Text color, background color (default black)

    # String of characters to simulate the "Matrix" rain effect
    chars = (
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890@#$%^&*()[]{}|;:,.<>?/~!_`'\"\\±§€£¥∑πΩΔ∫ƒ"
        "αβγδεζηθικλμνξοπρστυφχψω«»≠∞≡∧∨⊕∈∩∪≈αβγπ"
        "ϲπΔΘΩ≺⊂⊆≿⊤⊥⊢∝⇔⇒⇑⇓↔↕⊗⊙⊢⊣"
        "αβγδεζηθικλμνξοπρστυφχψω«»≠∞≡∧∨⊕∈∩∪≈αβγπ"
        "ϲπΔΘΩ≺⊂⊆≿⊤⊥⊢∝⇔⇒⇑⇓↔↕⊗⊙⊢⊣"
    )

    # List to store the current position of each falling character column
    columns = []

    # Infinite loop to keep the screensaver running
    while True:
        # Get the current screen size (height and width)
        sh, sw = stdscr.getmaxyx()

        # If the terminal size changes, update the columns list
        if len(columns) != sw:
            columns = [random.randint(0, sh - 1) for _ in range(sw)]

        # Clear the screen before drawing the next frame
        stdscr.erase()

        # Loop over each column in the terminal window
        for i in range(sw):
            # Create a string of 30 random characters for the falling text
            char_string = ''.join(random.choice(chars) for _ in range(30))
            x = i  # X position for the current column
            y = columns[i]  # Y position for the current column

            # Loop through each character in the string and apply fade effect
            for j in range(0, 30):  # Limit to 30 layers of fade
                fade_y = (y - j) % sh  # Loop the y position within screen bounds
                if fade_y < 0: continue  # Skip if outside the screen

                # Brightness effect: top characters are bright, others fade out
                brightness = max(0, 30 - j)
                smooth_brightness = int(30 * (1 - (j / 30)))  # Linear fade

                # Only draw characters that are within the screen bounds
                if 0 <= fade_y < sh and 0 <= x < sw:
                    try:
                        # Add the character at position (fade_y, x) with a fade effect
                        stdscr.addstr(fade_y, x, char_string[j], curses.color_pair(1) | curses.A_DIM * smooth_brightness)
                    except curses.error:
                        pass  # If the drawing position is out of bounds, just skip it

            # Update the position for the next frame (loop back to the top after reaching the bottom)
            columns[i] = (columns[i] + 1) % sh

        # Refresh the screen to show the changes
        stdscr.refresh()
        # Control the frame rate (how fast the text falls)
        time.sleep(0.05)

# Map color name to curses color code
def get_color_pair(color_name):
    color_map = {
        'black': curses.COLOR_BLACK,
        'red': curses.COLOR_RED,
        'green': curses.COLOR_GREEN,
        'yellow': curses.COLOR_YELLOW,
        'blue': curses.COLOR_BLUE,
        'purple': curses.COLOR_MAGENTA,  # Map "purple" to magenta
        'cyan': curses.COLOR_CYAN,
        'white': curses.COLOR_WHITE,
    }

    # Return the mapped color, default to green if invalid
    return color_map.get(color_name.lower(), curses.COLOR_GREEN)

# Command-line argument parsing and running the screensaver
def main():
    # Create a parser for command-line arguments
    parser = argparse.ArgumentParser(description="Matrix Screensaver")
    # Add an argument for choosing the color of the falling text
    parser.add_argument('-color', type=str, default='green', help="Choose the color of the falling text")
    args = parser.parse_args()

    # Initialize curses and pass the chosen color to the screensaver function
    curses.wrapper(lambda stdscr: matrix_rain(stdscr, get_color_pair(args.color)))

# Run the script if executed directly
if __name__ == "__main__":
    main()

