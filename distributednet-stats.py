from bs4 import BeautifulSoup
import requests
import sys

dnet_url = 'https://stats.distributed.net/participant/psearch.php'

#dnet_project_id = 24 # OGR-24 Optimal Golomb Rulers 
#dnet_project_id = 25 # OGR-25 Optimal Golomb Rulers 
#dnet_project_id = 26 # OGR-26 Optimal Golomb Rulers 
#dnet_project_id = 27 # OGR-27 Optimal Golomb Rulers 
#dnet_project_id = 28 # OGR-28 Optimal Golomb Rulers 
#dnet_project_id = 3 # RSA Labs' 56bit RC5 Encryption Challenge
#dnet_project_id = 5 # RSA Labs' 64bit RC5 Encryption Challenge
dnet_project_id = 8 # RSA Labs' 72bit RC5 Encryption Challenge

if len(sys.argv) <= 1:
    print()
    print('Usage: python distributednet-stats.py <user@domain.tld>')
    print()
    sys.exit()

dnet_search_text = str(sys.argv[1])
data = {'project_id':dnet_project_id,'st':dnet_search_text}
response = requests.post(dnet_url,data=data)

if response: 
    soup = BeautifulSoup(response.text, 'lxml')

    print()
    summary = soup.find('td',class_='htitle').text.lstrip()

    if "Summary" in summary:
        print('User: ' + dnet_search_text) 
        summary = " ".join(summary.split()) # remove extra spaces
        summary = summary.split('/')
        project = summary[0]
        print('Project: ' + project)
    else: 
        print(dnet_search_text + ' not found.')
        print()

    line = 0
    for match in soup.find_all('td',align='right'):
        line +=1
        if line == 1:
            overall_rank = match.text.lstrip()
            if overall_rank[0] != "T" and overall_rank[0] != "0":
                print ("Overall Rank: " + overall_rank)
        if line == 2:
            current_rank = match.text.lstrip()
            if current_rank[0] != "0":
                print ("Current Rank: " + current_rank)
        if line == 3:
            print()
            break
else:
    print('An error has occurred.')


