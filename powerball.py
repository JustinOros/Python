#!/usr/bin/python3
# Description: CLI to https://powerball.com (prints winning powerball results)
# Usage: python3 powerball.py [-List|-L]
# Author: Justin Oros
# Source: https://github.com/JustinOros

import requests
from bs4 import BeautifulSoup as BS
import sys

# ANSI escape codes for text formatting
RED = '\033[31m'
RESET = '\033[0m'

# Perform an HTTP GET request to the Powerball website
powerballUrl = 'https://www.powerball.com/previous-results?gc=powerball'
r = requests.get(powerballUrl, verify=True)

# Parse out our HTML using BeautifulSoup
soup = BS(r.text, 'html.parser')

# Parse Drawing Dates
drawingDates = soup.find_all('h5', class_='card-title')

# Parse White Balls
whiteballs = soup.find_all('div', class_='form-control col white-balls item-powerball')

# Parse Power Balls
powerballs = soup.find_all('div', class_='form-control col powerball item-powerball')

# Initalize and Set starting positions
whiteballPos = powerballPos = 0

# Check for arguments to decide if we should print all or just the first line
if len(sys.argv) > 1 and sys.argv[1].lower() in ['-list', '-l']:
    # If -List or -L is present, print all lines
    print_all = True
else:
    # If no arguments or other arguments, print only the first line
    print_all = False

# Function to print a single line of results
def print_line(date, whiteballPos, powerballPos):
    print(date.text.strip() + ":", end=" ")

    # Print 5 White Balls
    for i in range(0, 5):
        print(whiteballs[whiteballPos].text.strip() + ",", end=" ")
        whiteballPos += 1

    # Print 1 Power Ball in red
    print(RED + powerballs[powerballPos].text.strip() + RESET)
    powerballPos += 1

    return whiteballPos, powerballPos

# Loop through previous Drawing Dates and print results
if print_all:
    # Print all lines if -List or -L is present
    for date in drawingDates:
        whiteballPos, powerballPos = print_line(date, whiteballPos, powerballPos)
else:
    # Print only the first line
    if drawingDates:
        print_line(drawingDates[0], whiteballPos, powerballPos)
