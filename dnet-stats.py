#!/usr/bin/python3
from bs4 import BeautifulSoup
import requests, sys

# Distributed.net participant search form
searchUrl = 'https://stats.distributed.net/participant/psearch.php'

# Valid Distributed.net Projects (and associated ID)
validProjects = {
    'RSA-56' : 3,
    'RSA-64' : 5,
    'RSA-72' : 8,
    'OGR-24' : 24,
    'OGR-25' : 25,
    'OGR-26' : 26,
    'OGR-27' : 27,
    'OGR-28' : 28,
}

# Help menu
def printHelp():
    print(
        '\nUsage: dnet-stats.py [user] [project]\n' +
        '\nPROJECTs' +
        '\n========' +
        '\n RSA-56 ' +
        '\n RSA-64 ' +
        '\n RSA-72 ' +
        '\n OGR-24 ' + 
        '\n OGR-25 ' +
        '\n OGR-26 ' +
        '\n OGR-27 ' +
        '\n OGR-28 ' +
        '\n========\n'
        )
    exit()

# If no arguments are given, display Help Menu
if len(sys.argv) <= 2:
    print('\nError: Please specify user and project.')
    printHelp()

# get username from user input
myUser = sys.argv[1]

# get project from user input
myProject = sys.argv[2].upper()

# if we have all arguments needed, proceed...
if len(sys.argv) == 3:
    # ensure the project argument is a valid project
    if sys.argv[2].upper() in ['RSA-56','RSA-64','RSA-72','OGR-24','OGR-25','OGR-26','OGR-27','OGR-28']: 
        # if it is valid, store the Project ID into a variable
        projectId = validProjects[sys.argv[2].upper()]
    else:
        # otherwise, let the user know their project was not valid
        print('\nError: ' + sys.argv[2].upper() + ' is not a valid project.')
        printHelp()
        exit()

data = {'project_id':projectId,'st':myUser} # along with the project id
response = requests.post(searchUrl,data=data) # perfom a form post and get the response

if response: # if we received a response
    soup = BeautifulSoup(response.text, 'lxml') # load the response into BeautifulSoup

    summary = soup.find('td',class_='htitle').text.lstrip() # find summary

    if "Summary" in summary:
        print('\nUser: ' + myUser) # print user
        summary = " ".join(summary.split()) # remove extra spaces from summary
        summary = summary.split('/') # split summary and project into 2 strings
        project = summary[0] # store the project name from the summary into a variable
        print('Project: ' + project) # print project
    else: 
        print('\n' + myUser + ' not found for project ' + myProject + '.\n') # notify if user not found
        exit()

    line = 0
    for match in soup.find_all('td',align='right'): # search soup for table data
        line +=1
        if line == 1: # print overall rank
            overallRank = match.text.lstrip()
            if overallRank[0] != "T" and overallRank[0] != "0":
                overallRank = overallRank.split('(')
                overallRank = overallRank[0]
        if line == 2: # print current rank
            currentRank = match.text.lstrip()
            if currentRank[0] != "0":
                currentRank = currentRank.split('(')
                currentRank = currentRank[0]
        if line == 3: # stop searching soup
            print ('Current Rank: ' + currentRank)
            print ('Overall Rank: ' + overallRank + '\n')
            break
else:
    print('An error has occured.')
