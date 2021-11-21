#!/usr/bin/python3

# Import BeautifulSoup
from bs4 import BeautifulSoup
import requests

# Arizona Powerball API URL
myUrl = 'https://powerball.com/api/v1/numbers/powerball/recent10?_format=xml'

try: 
    # Get winning Arizona Powerball numbers from powerball.com
    response = requests.get(myUrl)

    # If we receive a response, proceed...
    if response:

        # Store the response from the server into a bowl of soup
        soup = BeautifulSoup(response.text, 'lxml') # load the response into BeautifulSoup
    
        # parse out the winning numbers
        winningNumbers = soup.find('field_winning_numbers').contents
    
        # parse out the drawing date
        drawingDate = soup.find('field_draw_date').contents

        # print out the winning numbers and drawing date
        print(*winningNumbers,*drawingDate)

# Notify user if we fail to get a response from server...
except Exception as e:
    print('No response from powerball.com.')