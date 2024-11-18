#!/usr/bin/python3
# Description: A command-line interface to https://stats.distributed.net 
# Usage: python3 dnet-stats.py -p <project> -u <username>
# Author: Justin Oros
# Source: https://github.com/JustinOros
# Dependencies: pip install requests argparse beautifulsoup4 lxml

from bs4 import BeautifulSoup
import requests
import argparse
import sys

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

# Parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description='Fetch Distributed.net stats for user and project.')
    parser.add_argument('-u', '--user', type=str, required=True, help='Username of the participant.')
    parser.add_argument('-p', '--project', type=str, required=True, choices=validProjects.keys())
    args = parser.parse_args()

    return parser.parse_args()

# Main execution function
def main():
    # Parse the command-line arguments
    args = parse_arguments()

    # Retrieve user and project from parsed arguments
    user = args.user
    project = args.project

    # Get project ID
    projectId = validProjects[project]

    # Prepare data for the request
    data = {'project_id': projectId, 'st': user}

    # Perform a POST request to fetch the response
    response = requests.post(searchUrl, data=data)

    if response:  # Proceed if we received a response
        soup = BeautifulSoup(response.text, 'lxml')  # Load the response into BeautifulSoup

        summary = soup.find('td', class_='htitle').text.lstrip()  # Find summary

        if "Summary" in summary:
            print(f'\nUser: {user}')  # Print user
            summary = " ".join(summary.split())  # Remove extra spaces from summary
            summary = summary.split('/')  # Split summary and project into 2 strings
            project_name = summary[0]  # Store the project name from the summary into a variable
            print(f'Project: {project_name}')  # Print project
        else:
            print(f"\nError: {user} not found for project {project}.\n")  # Notify if user not found
            sys.exit()

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
                print(f'Rank: {currentRank}')
                print(f'Overall: {overallRank}')
                break

        # Get last update date
        lastUpdate = soup.find('td', class_="lastupdate").text.split()
        lastUpdate = lastUpdate[8].lstrip()
        print(f'Updated: {lastUpdate}\n')

    else:
        print('An error has occurred while fetching data.')

if __name__ == '__main__':
    main()
