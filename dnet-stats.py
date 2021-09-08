#!/usr/bin/python3

from bs4 import BeautifulSoup
import requests, sys

if len(sys.argv) <= 1: # check to see if we have at least 1 argument
    print( # and if not, print a help menu
        '\nUsage: dnet-stats.py [user] [project]\n' +
        '\nOptional: [project], must be specified using a project id number.\n' +
        '\n=====Distributed.net Projects=====' +
        '\n3 = RSA-56 RC5 Encryption Challenge' +
        '\n5 = RSA-64 RC5 Encryption Challenge' +
        '\n8 = RSA-72 RC5 Encryption Challenge' +
        '\n24 = OGR-24 Optimal Golomb Rulers' + 
        '\n25 = OGR-25 Optimal Golomb Rulers' +
        '\n26 = OGR-26 Optimal Golomb Rulers' +
        '\n27 = OGR-27 Optimal Golomb Rulers' +
        '\n28 = OGR-28 Optimal Golomb Rulers' +
        '\n===================================\n'
        )
    exit()

# distributed.net participant search form
dnet_url = 'https://stats.distributed.net/participant/psearch.php'

### distributed.net projects ### 
#dnet_project_id = 24 # OGR-24 Optimal Golomb Rulers 
#dnet_project_id = 25 # OGR-25 Optimal Golomb Rulers 
#dnet_project_id = 26 # OGR-26 Optimal Golomb Rulers 
#dnet_project_id = 27 # OGR-27 Optimal Golomb Rulers 
#dnet_project_id = 28 # OGR-28 Optimal Golomb Rulers 
#dnet_project_id = 3 # RSA Labs' 56bit RC5 Encryption Challenge
#dnet_project_id = 5 # RSA Labs' 64bit RC5 Encryption Challenge
dnet_project_id = 8 # RSA Labs' 72bit RC5 Encryption Challenge

if len(sys.argv) == 2:
    print('\nNo project id specified so defaulting to ' + str(dnet_project_id) + '.')
    
valid_projects = ['3', '5', '8', '24', '25', '26', '27', '28', '205']

if len(sys.argv) == 3:
    x = sys.argv[2]
    if x in valid_projects:
        dnet_project_id = sys.argv[2]
    else:
        print('\n' + sys.argv[2] + ' is not a valid project id.\n')
        exit()

dnet_search_text = sys.argv[1] # store the user argument into a variable

data = {'project_id':dnet_project_id,'st':dnet_search_text} # along with the project id
response = requests.post(dnet_url,data=data) # perfom a form post and get the response

if response: # if we received a response
    soup = BeautifulSoup(response.text, 'lxml') # load the response into BeautifulSoup

    summary = soup.find('td',class_='htitle').text.lstrip() # find summary

    if "Summary" in summary:
        print('\nUser: ' + dnet_search_text) # print user
        summary = " ".join(summary.split()) # remove extra spaces from summary
        summary = summary.split('/') # split summary and project into 2 strings
        project = summary[0] # store the project name from the summary into a variable
        print('Project: ' + project) # print project
    else: 
        print(
            '\nSearching project id ' + dnet_project_id + '...\n'
            '\n' + dnet_search_text + ' not found.\n') # notify if user not found
        exit()

    line = 0
    for match in soup.find_all('td',align='right'): # search soup for table data
        line +=1
        if line == 1: # print overall rank
            overall_rank = match.text.lstrip()
            if overall_rank[0] != "T" and overall_rank[0] != "0":
                overall_rank = overall_rank.split('(')
                overall_rank = overall_rank[0]
        if line == 2: # print current rank
            current_rank = match.text.lstrip()
            if current_rank[0] != "0":
                current_rank = current_rank.split('(')
                current_rank = current_rank[0]
        if line == 3: # stop searching soup
            print ('Current Rank: ' + current_rank)
            print ('Overall Rank: ' + overall_rank + '\n')
            break
else:
    print('An error has occured.')
