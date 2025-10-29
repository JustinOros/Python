#!/usr/bin/python3
# Description: A command-line interface to https://stats.distributed.net 
# Usage: python3 dnet-user-stats.py -p <project> -u <username>
# Author: Justin Oros
# Source: https://github.com/JustinOros
# Dependencies: pip install requests argparse beautifulsoup4 lxml

from bs4 import BeautifulSoup
import requests, argparse, sys

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

# Normalize valid project names for case-insensitive lookup
normalizedProjects = {k.lower(): v for k, v in validProjects.items()}

# Parse command-line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description='Fetch Distributed.net stats for user and project.')
    parser.add_argument('-u', '--user', type=str, required=True, help='Username of the participant.')
    parser.add_argument('-p', '--project', type=str, required=True, help='Project name (case-insensitive).')
    return parser.parse_args()

# Main execution function
def main():
    # Parse the command-line arguments
    args = parse_arguments()

    # Retrieve user and project from parsed arguments
    user = args.user
    project_input = args.project.strip().lower()

    # Validate project name (case-insensitive)
    if project_input not in normalizedProjects:
        print(f"\nError: Invalid project '{args.project}'. Valid options are:")
        for p in validProjects.keys():
            print(f"  - {p}")
        sys.exit(1)

    # Get project ID
    projectId = normalizedProjects[project_input]
    project = [k for k, v in validProjects.items() if v == projectId][0]  # Get the canonical name

    # Prepare data for the request
    data = {'project_id': projectId, 'st': user}

    # Perform a POST request to fetch the response
    response = requests.post(searchUrl, data=data)

    if response:
        soup = BeautifulSoup(response.text, 'lxml')

        summary = soup.find('td', class_='htitle').text.lstrip()

        if 'Summary' in summary:
            print(f'\nUser: {user}')
            summary = ' '.join(summary.split())
            summary = summary.split('/')
            project_name = summary[0]
            print(f'Project: {project_name}')
        else:
            print(f'\nError: {user} not found for project {project}.\n')
            sys.exit()

        line = 0
        for match in soup.find_all('td', align='right'):
            line += 1
            if line == 1:
                overallRank = match.text.lstrip()
                if overallRank[0] != 'T' and overallRank[0] != '0':
                    overallRank = overallRank.split('(')[0]
            if line == 2:
                currentRank = match.text.lstrip()
                if currentRank[0] != '0':
                    currentRank = currentRank.split('(')[0]
            if line == 3:
                currentRank = f'{int(currentRank):,}'
                print(f'Rank: {currentRank}')
                overallRank = f'{int(overallRank):,}'
                print(f'Overall: {overallRank}')
                break

        lastUpdate = soup.find('td', class_='lastupdate').text.split()
        lastUpdate = lastUpdate[8].lstrip()

        Year = lastUpdate[7:12]
        Month = lastUpdate[3:6]
        Day = lastUpdate[0:2]

        formattedDate = f'{Month} {Day}, {Year}'
        print(f'Updated: {formattedDate}\n')

    else:
        print('An error has occurred while fetching data.')

if __name__ == '__main__':
    main()
