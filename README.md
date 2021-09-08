# distributednet-stats.py

    Summary: A cli interface to https://stats.distributed.net written in python
    
    Usage: dnet-stats.py [user] [project]

    Optional: [project], must be specified using a project id number.

    =====Distributed.net Projects=====
    3 = RSA-56 RC5 Encryption Challenge
    5 = RSA-64 RC5 Encryption Challenge
    8 = RSA-72 RC5 Encryption Challenge
    24 = OGR-24 Optimal Golomb Rulers
    25 = OGR-25 Optimal Golomb Rulers
    26 = OGR-26 Optimal Golomb Rulers
    27 = OGR-27 Optimal Golomb Rulers
    28 = OGR-28 Optimal Golomb Rulers
    ==================================

## Example Output: 
    User: user@domain.tld
    Project: RC5-72 
    Overall Rank: 809
    Current Rank: 166

## Linux / macOS / Windows Pre-reqs
    pip3 install bs4 lxml requests
