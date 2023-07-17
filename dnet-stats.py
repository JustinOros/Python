#!/usr/bin/python3
# Description: A command-line interface to stats.distributed.net 
# Usage: python3 dnet-stats.py <user> <project> 
# Author: Justin Oros
# Source: https://github.com/JustinOros

from bs4 import BeautifulSoup
import requests, sys

# Distributed.net Participant Search Form
searchUrl = 'https://stats.distributed.net/participant/psearch.php'

# Distributed.net Projects (and associated IDs)
validProjects = {
    'RC5-56' : 3,
    'RC5-64' : 5,
    'RC5-72' : 8,
    'OGR-24' : 24,
    'OGR-25' : 25,
    'OGR-26' : 26,
    'OGR-27' : 27,
    'OGR-28' : 28,
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
        Text.Reset + Text.Green + 'dnet-stats.py <username> <project>\n' +
        Text.Bold + Text.Green + '\nProjects: ' + 
        Text.Reset + Text.Green + 'RC5-56, RC5-64, RC5-72, OGR-24, OGR-25, OGR-26, OGR-27, OGR-28\n' +
        Text.Bold + Text.Green + '\nExample: ' + 
        Text.Reset + Text.Green + 'dnet-stats.py bluecat9@penguinized.net RC5-72\n' + Text.Reset
        )
    exit()

# If no arguments are given, display Help Menu hint
if len(sys.argv) <= 2:
    helpHint()

# get username from user input
myUser = sys.argv[1]

# get project from user input
myProject = sys.argv[2].upper()

# if we have all arguments needed, proceed...
if len(sys.argv) == 3:
    # ensure the project argument is a valid project
    if sys.argv[2].upper() in ['RC5-56','RC5-64','RC5-72','OGR-24','OGR-25','OGR-26','OGR-27','OGR-28']: 
        # if it is valid, store the Project ID into a variable
        projectId = validProjects[sys.argv[2].upper()]
    else:
        # otherwise, let the user know their project was not valid
        print(Text.Bold + Text.Red + '\nError: ' + sys.argv[2].upper() + ' is not a valid project.\n' + Text.Reset)
        exit()

data = {'project_id':projectId,'st':myUser} # along with the project id

response = requests.post(searchUrl,data=data) # perfom a form post and get the response

if response: # if we received a response
    soup = BeautifulSoup(response.text, 'lxml') # load the response into BeautifulSoup

    summary = soup.find('td',class_='htitle').text.lstrip() # find summary

    if "Summary" in summary:
        print(Text.Bold + Color.Theme1 + '\nUser: ' + myUser + Text.Reset) # print user
        summary = " ".join(summary.split()) # remove extra spaces from summary
        summary = summary.split('/') # split summary and project into 2 strings
        project = summary[0] # store the project name from the summary into a variable
        print(Text.Bold + Color.Theme2 + 'Project: ' + project) # print project
    else: 
        print('\n' + Text.Bold + Text.Red + 'Error: ' + myUser + ' not found for project ' + myProject + '.\n' + Text.Reset) # notify if user not found
        exit()

    line = 0
    for match in soup.find_all('td',align='right'): # search soup for table data
        line +=1
        if line == 1: # get overall rank
            overallRank = match.text.lstrip()
            if overallRank[0] != "T" and overallRank[0] != "0":
                overallRank = overallRank.split('(')
                overallRank = overallRank[0]
        if line == 2: # get current rank
            currentRank = match.text.lstrip()
            if currentRank[0] != "0":
                currentRank = currentRank.split('(')
                currentRank = currentRank[0]
        if line == 3: # print current and overall rank
            print (Text.Bold + Color.Theme3 + 'Rank: ' + Text.Underline + currentRank + Text.Reset)
            print (Text.Bold + Color.Theme4 + 'Overall: ' + overallRank + Text.Reset)
            break

    # get last update date
    lastUpdate = soup.find('td',class_="lastupdate").text.split()
    lastUpdate = lastUpdate[8].lstrip()
    print(Text.Bold + Color.Theme5 + 'Updated: ' + lastUpdate + Text.Reset + '\n')

else:
    print(Text.Bold + Text.Red + 'An error has occuRed.' + Text.Reset)
