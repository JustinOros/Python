#!/usr/bin/python3
# Description: A command-line interface to https://openpayrolls.com for University of Arizona payroll data.
# Usage: python3 ua-pay.py -fn <first_name> -ln <last_name>
# Author: Justin Oros
# Source: https://github.com/JustinOros
# Dependencies: pip install requests selenium beautifulsoup4

import argparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Setup argparse to allow command-line input for first and last name
parser = argparse.ArgumentParser(description="Scrape data for a given employee from OpenPayrolls.")
parser.add_argument('-fn', '--firstname', required=True, help="First name of the employee")
parser.add_argument('-ln', '--lastname', required=True, help="Last name of the employee")

# Parse command-line arguments
args = parser.parse_args()

# Construct URL using provided first and last name (converted to lowercase)
url = f'https://openpayrolls.com/employee/{args.firstname.lower()}-{args.lastname.lower()}-4329'

# Set up Selenium WebDriver (Chrome in headless mode)
options = Options()
options.headless = True  # Ensure headless mode is enabled
options.add_argument("--no-sandbox")  # Sometimes needed for headless mode to work in certain environments
options.add_argument("--disable-dev-shm-usage")  # Prevents issues in some systems

# Specify the path to the ChromeDriver if it's not in the system PATH
driver = webdriver.Chrome(options=options)

# Open the target URL
driver.get(url)

# Wait for the page to fully load (use a fixed time delay or more advanced methods if necessary)
driver.implicitly_wait(10)  # wait up to 10 seconds for the page to load

# Get the page source after JavaScript has been rendered
page_source = driver.page_source

# Use BeautifulSoup to parse the page content
soup = BeautifulSoup(page_source, 'html.parser')

# Extract all text from the page
page_text = soup.get_text(strip=True)

# Find portion of the text starting with "University of Arizona (UA) records show" and ending with "employees."
start_marker = "University of Arizona (UA) records show"
end_marker = "employees."

# Find the start and end positions in the text
start_index = page_text.find(start_marker)
end_index = page_text.find(end_marker, start_index) + len(end_marker)

# Extract the relevant portion of the text (if both markers are found)
if start_index != -1 and end_index != -1:
    relevant_text = page_text[start_index:end_index]
    print(relevant_text)
else:
    print("The specified text could not be found on the page.")

# Close the browser after scraping
driver.quit()
