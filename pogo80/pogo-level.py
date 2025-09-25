#!/usr/bin/env python3
# Description: Calculate Pokémon GO trainer level from total XP
# Usage: python3 pogo-level.py
# Author: Justin Oros
# Source: https://github.com/JustinOros

import sys

# XP thresholds for levels 1–80 (cumulative XP)
xp_thresholds = [
    0, 1000, 3000, 6000, 10000, 15000, 21000, 28000, 36000, 45000,          # 1–10
    55000, 65000, 75000, 85000, 100000, 120000, 140000, 160000, 185000, 210000,  # 11–20
    260000, 335000, 435000, 560000, 710000, 900000, 1100000, 1350000, 1650000, 2000000,  # 21–30
    2500000, 3000000, 3750000, 4750000, 6000000, 7500000, 9500000, 12000000, 15000000, 20000000,  # 31–40
    26000000, 33500000, 42500000, 43500000, 66500000, 82000000, 100000000, 121000000, 146000000, 176000000,  # 41–50
    206000000, 236000000, 266000000, 296000000, 326000000, 356000000, 386000000, 416000000, 446000000, 476000000,  # 51–60
    506000000, 536000000, 566000000, 596000000, 626000000, 656000000, 686000000, 716000000, 746000000, 776000000,  # 61–70
    806000000, 836000000, 866000000, 896000000, 926000000, 956000000, 986000000, 1016000000, 1046000000, 1076000000,  # 71–80
]

def main():
    try:
        xp_input = input("Enter your total XP: ").replace(',', '').strip()
        xp = int(xp_input)
    except ValueError:
        print("Please enter a valid number for XP.")
        sys.exit(1)

    level = 1
    for i, threshold in enumerate(xp_thresholds):
        if xp >= threshold:
            level = i + 1
        else:
            break

    print(f"Current Level: {level}")

    if level < 80:
        xp_to_next_level = xp_thresholds[level] - xp
        xp_to_level_80 = xp_thresholds[79] - xp
        print(f"XP to next level: {xp_to_next_level:,}")
        print(f"XP to Level 80: {xp_to_level_80:,}")
    else:
        print("You have reached the maximum level (Level 80)!")

if __name__ == "__main__":
    main()
