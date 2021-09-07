from bs4 import BeautifulSoup
import requests
import sys

# check to see if we have input
if len(sys.argv) <= 1:
    print()
    print('Usage: python distributednet-stats.py <user@domain.tld>')
    print()
    sys.exit()

# distributed.net project search form
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

dnet_search_text = str(sys.argv[1]) # store the user argument into a variable
data = {'project_id':dnet_project_id,'st':dnet_search_text} # along with the project id
response = requests.post(dnet_url,data=data) # perfom a form post and get the response

if response: # if we received a response
    soup = BeautifulSoup(response.text, 'lxml') # load the response into BeautifulSoup

    print()
    summary = soup.find('td',class_='htitle').text.lstrip() # find summary

    if "Summary" in summary:
        print('User: ' + dnet_search_text) # print user
        summary = " ".join(summary.split()) # remove extra spaces from summary
        summary = summary.split('/') # split summary and project into 2 strings
        project = summary[0] # store the project name from the summary into a variable
        print('Project: ' + project) # print project
    else: 
        print(dnet_search_text + ' not found.') # notify if user not found
        print()

    line = 0
    for match in soup.find_all('td',align='right'): # search soup for table data
        line +=1
        if line == 1: # print overall rank
            overall_rank = match.text.lstrip()
            if overall_rank[0] != "T" and overall_rank[0] != "0":
                overall_rank = overall_rank.split('(')
                overall_rank = overall_rank[0]
                print ("Overall Rank: " + overall_rank)
        if line == 2: # print current rank
            current_rank = match.text.lstrip()
            if current_rank[0] != "0":
                current_rank = current_rank.split('(')
                current_rank = current_rank[0]
                print ("Current Rank: " + current_rank)
        if line == 3: # stop searching soup
            print()
            break
else:
    print('An error has occured.')
