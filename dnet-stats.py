#!/usr/bin/python3
# Description: A command-line interface to stats.distributed.net 
# Usage: python3 dnet-stats.py -User <username> -Project <project> 
# Author: Justin Oros
# Source: https://github.com/JustinOros
# Dependencies: pip install requests beautifulsoup4

from bs4 import BeautifulSoup
import requests, sys

# Distributed.net Participant Search Form
searchUrl = 'https://stats.distributed.net/participant/psearch.php'

# Distributed.net Projects (and associated IDs)
validProjects = {
    'RC5-56': 3,
    'RC5-64': 5,
    'RC5-72': 8,
    'OGR-24': 24,
    'OGR-25': 25,
    'OGR-26': 26,
    'OGR-27': 27,
    'OGR-28': 28,
}

# Text Colors & Formatting
class Text:
    Pink = '\033[95m'
    Black = '\u001b[30m'
    Red = '\u001b[31m'
    Green = '\u001b[32m'
    Yellow = '\u001b[33m'
    Blue = '\u001b[34m'
    Magenta = '\u001b[35m'
    Cyan = '\u001b[36m'
    White = '\u001b[37m'
    Bold = '\033[1m'
    Italics = '\x1B[3m'
    Underline = '\033[4m'
    Reset = '\u001b[0m'

# Text Color Theme
class Color:
    Theme1 = '\u001b[38;5;165m'
    Theme2 = '\u001b[38;5;164m'
    Theme3 = '\u001b[38;5;163m'
    Theme4 = '\u001b[38;5;162m'
    Theme5 = '\u001b[38;5;161m'
    
# Help Menu (Hint)
def helpHint():
    if len(sys.argv) > 1:
        if sys.argv[1].lower() == 'help':
            helpMenu()
    print(Text.Green + '\nType ' + Text.Bold + Text.Italics + 'dnet-stats.py help' + Text.Reset + Text.Green + ' for the help menu.\n' + Text.Reset)
    exit()

# Help Menu (Main)
def helpMenu():
    print(
        Text.Bold + Text.Green + '\nHelp Menu:\n' + 
        Text.Bold + Text.Green + '\nUsage: ' + 
        Text.Reset + Text.Green + 'dnet-stats.py -User <username> -Project <project>\n' +
        Text.Bold + Text.Green + '\nProjects: ' + 
        Text.Reset + Text.Green + 'RC5-56, RC5-64, RC5-72, OGR-24, OGR-25, OGR-26, OGR-27, OGR-28\n' +
        Text.Bold + Text.Green + '\nExample: ' + 
        Text.Reset + Text.Green + 'python3 dnet-stats.py -User bluecat9@penguinized.net -Project RC5-72\n' + Text.Reset
    )
    exit()

# Parse command-line arguments
user = None
project = None

# Check if the arguments are provided and valid
for i in range(1, len(sys.argv)):
    if sys.argv[i] == "-User" and i + 1 < len(sys.argv):
        user = sys.argv[i + 1]
    if sys.argv[i] == "-Project" and i + 1 < len(sys.argv):
        project = sys.argv[i + 1].upper()

# Check if both user and project are provided
if not user or not project:
    print(Text.Bold + Text.Red + "Error: Missing required arguments. Use -User and -Project." + Text.Reset)
    helpMenu()

# Ensure the project argument is a valid project
if project not in validProjects:
    print(Text.Bold + Text.Red + f"Error: {project} is not a valid project.\n" + Text.Reset)
    helpMenu()

# Get project ID
projectId = validProjects[project]

# Prepare data for the request
data = {'project_id': projectId, 'st': user}

# Perform a POST request to fetch the response
response = requests.post(searchUrl, data=data)

if response:  # If we received a response
    soup = BeautifulSoup(response.text, 'lxml')  # Load the response into BeautifulSoup

    summary = soup.find('td', class_='htitle').text.lstrip()  # Find summary

    if "Summary" in summary:
        print(Text.Bold + Color.Theme1 + '\nUser: ' + user + Text.Reset)  # Print user
        summary = " ".join(summary.split())  # Remove extra spaces from summary
        summary = summary.split('/')  # Split summary and project into 2 strings
        project_name = summary[0]  # Store the project name from the summary into a variable
        print(Text.Bold + Color.Theme2 + 'Project: ' + project_name)  # Print project
    else:
        print('\n' + Text.Bold + Text.Red + 'Error: ' + user + ' not found for project ' + project + '.\n' + Text.Reset)  # Notify if user not found
        exit()

    line = 0
    for match in soup.find_all('td', align='right'):  # Search soup for table data
        line += 1
        if line == 1:  # Get overall rank
            overallRank = match.text.lstrip()
            if overallRank[0] != "T" and overallRank[0] != "0":
                overallRank = overallRank.split('(')
                overallRank = overallRank[0]
        if line == 2:  # Get current rank
            currentRank = match.text.lstrip()
            if currentRank[0] != "0":
                currentRank = currentRank.split('(')
                currentRank = currentRank[0]
        if line == 3:  # Print current and overall rank
            print(Text.Bold + Color.Theme3 + 'Rank: ' + Text.Underline + currentRank + Text.Reset)
            print(Text.Bold + Color.Theme4 + 'Overall: ' + overallRank + Text.Reset)
            break

    # Get last update date
    lastUpdate = soup.find('td', class_="lastupdate").text.split()
    lastUpdate = lastUpdate[8].lstrip()
    print(Text.Bold + Color.Theme5 + 'Updated: ' + lastUpdate + Text.Reset + '\n')

else:
    print(Text.Bold + Text.Red + 'An error has occurred while fetching data.' + Text.Reset)
