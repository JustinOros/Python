#!/usr/bin/python3
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

# Format Output
class FORMAT:
    PINK = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    REGULAR = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ITALICS = '\x1B[3m'

# Help Menu (Hint)
def helpHint():
    if len(sys.argv) > 1:
        if sys.argv[1].lower() == 'help':
            helpMenu()
    print(FORMAT.GREEN + '\nType ' + FORMAT.BOLD + FORMAT.ITALICS + 'dnet-stats.py help' + FORMAT.REGULAR + FORMAT.GREEN + ' for the help menu.\n')
    exit()

# Help Menu (Main)
def helpMenu():
    print(
        FORMAT.BOLD + FORMAT.GREEN + '\nHelp Menu:\n' + 
        FORMAT.BOLD + FORMAT.GREEN + '\nUsage: ' + 
        FORMAT.REGULAR + FORMAT.GREEN + 'dnet-stats.py <username> <project>\n' +
        FORMAT.BOLD + FORMAT.GREEN + '\nProjects: ' + 
        FORMAT.REGULAR + FORMAT.GREEN + 'RC5-56, RC5-64, RC5-72, OGR-24, OGR-25, OGR-26, OGR-27, OGR-28\n' +
        FORMAT.BOLD + FORMAT.GREEN + '\nExample: ' + 
        FORMAT.REGULAR + FORMAT.GREEN + 'dnet-stats.py bluecat9@penguinized.net RC5-72\n'
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
        print(FORMAT.BOLD + FORMAT.RED + '\nError: ' + sys.argv[2].upper() + ' is not a valid project.\n')
        exit()

data = {'project_id':projectId,'st':myUser} # along with the project id

response = requests.post(searchUrl,data=data) # perfom a form post and get the response

if response: # if we received a response
    soup = BeautifulSoup(response.text, 'lxml') # load the response into BeautifulSoup

    summary = soup.find('td',class_='htitle').text.lstrip() # find summary

    if "Summary" in summary:
        print(FORMAT.BOLD + FORMAT.YELLOW + '\nUser: ' + FORMAT.RED + myUser + FORMAT.REGULAR) # print user
        summary = " ".join(summary.split()) # remove extra spaces from summary
        summary = summary.split('/') # split summary and project into 2 strings
        project = summary[0] # store the project name from the summary into a variable
        print(FORMAT.BOLD + FORMAT.YELLOW + 'Project: ' + FORMAT.REGULAR + FORMAT.CYAN + project) # print project
    else: 
        print('\n' + FORMAT.BOLD + FORMAT.RED + 'Error: ' + myUser + ' not found for project ' + myProject + '.\n') # notify if user not found
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
            print (FORMAT.BOLD + FORMAT.YELLOW + 'Current Rank: ' + FORMAT.YELLOW + FORMAT.GREEN + FORMAT.UNDERLINE + currentRank + FORMAT.REGULAR)
            print (FORMAT.BOLD + FORMAT.YELLOW + 'Overall Rank: ' + FORMAT.YELLOW + FORMAT.PINK + overallRank + FORMAT.REGULAR + '\n')
            break
else:
    print(FORMAT.BOLD + FORMAT.RED + 'An error has occured.')
