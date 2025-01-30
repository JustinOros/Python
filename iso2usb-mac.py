#!/usr/bin/env python3
# Description: An easy CLI interface for writing ISOs to USB sticks on macOS.
# Usage: python3 iso2usb-mac.py
# Author: Justin Oros
# Source: https://github.com/JustinOros
# Dependencies: dd, diskutil (standard utils on macOS)

import os
import subprocess
import sys

def list_files(extension):
    # List files in the current directory with the ISO extension.
    return [f for f in os.listdir() if f.endswith(extension)]

def list_external_disks():
    # List external disks (USB drives) currently mounted on macOS.
    result = subprocess.run(['diskutil', 'list'], capture_output=True, text=True)
    disks = []
    for line in result.stdout.splitlines():
        if "/dev/disk" in line and "external" in line:
            parts = line.split()
            disks.append(parts[0])
    return disks

def prompt_choice(options, prompt):
    # Prompt user to select an option from a list.
    while True:
        for idx, option in enumerate(options, 1):
            print(f"{idx}. {option}")
        try:
            choice = int(input(f"{prompt} (Enter the number): "))
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                print(f"Please enter a number between 1 and {len(options)}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def prompt_speed_choice():
    # Prompt the user to select the write speed.
    print("\nSelect the write speed:")
    print("1) Slow (1M)")
    print("2) Regular (4M) [default]")
    print("3) Fast (8M)")

    while True:
        choice = input("Enter the number (or press RETURN for default): ").strip()

        if choice == "":
            return "4M"  # Default to regular speed (4M)
        elif choice == "1":
            return "1M"  # Slow speed
        elif choice == "2":
            return "4M"  # Regular speed
        elif choice == "3":
            return "8M"  # Fast speed
        else:
            print("Invalid input. Please enter 1, 2, or 3, or press RETURN for default.")

def confirm(prompt):
    # Prompt user to confirm an action.
    while True:
        confirm = input(f"{prompt} (y/n): ").strip().lower()
        if confirm in ['y', 'n']:
            return confirm == 'y'
        print("Please enter 'y' or 'n'.")

def main():
    # List ISOs in the current directory
    iso_files = list_files('.iso')
    if not iso_files:
        print("No ISO files found in the current directory.")
        sys.exit(1)

    # List available external disks
    disks = list_external_disks()
    if not disks:
        print("No external disks found.")
        sys.exit(1)

    # Prompt user to select ISO
    selected_iso = prompt_choice(iso_files, "Select an ISO file")
    
    # Prompt user to select disk
    selected_disk = prompt_choice(disks, "Select a disk")

    # Prompt user to select write speed
    selected_speed = prompt_speed_choice()

    # Overview of selected ISO, disk, and write speed
    print(f"\nYou selected:")
    print(f"ISO: {selected_iso}")
    print(f"Disk: {selected_disk}")
    print(f"Write speed: {selected_speed}")

    # Confirm before proceeding
    if confirm("Are you sure you want to proceed? This will overwrite the disk"):
        print("Writing ISO to disk...")
        
        # Execute dd command to write the ISO to the selected disk with the selected block size
        try:
            # WARNING: dd command will overwrite the disk, be sure!
            subprocess.run(['sudo', 'dd', f'if={selected_iso}', f'of={selected_disk}', 'bs=' + selected_speed, 'status=progress', 'oflag=sync'], check=True)
            
            # After writing the ISO, eject the disk to make it ready for use
            subprocess.run(['sudo', 'diskutil', 'eject', selected_disk], check=True)
            
            print("ISO successfully written to disk.")
        except subprocess.CalledProcessError as e:
            print(f"Error while writing to disk: {e}")
    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    main()
