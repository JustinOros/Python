#!/usr/bin/env python3
# Description: Monero (XMR) Mining Script - Optimized for CPU mining with support for solo and pool mining
# Usage: python3 miner-monero.py
# Author: Justin Oros
# Source: https://github.com/JustinOros 

import json
import subprocess
import sys
import os
import time
import signal
import platform
import urllib.request
import urllib.error
import tarfile
import zipfile
import re
import threading
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime

class MoneroMiner:
    def __init__(self, config_file: str = "miner-monero.json"):
        self.config_file = config_file
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config = None
        self.process: Optional[subprocess.Popen] = None
        self.gpu_process: Optional[subprocess.Popen] = None
        self.stats_thread = None
        self.stop_stats = False
        self.has_nvidia_gpu = False
        
        # Known mining pools (with minimum payout amounts)
        self.known_pools = [
            {"name": "MoneroOcean", "address": "gulf.moneroocean.stream:10128", "tls": False, "coin": None, "min_payout": "0.003 XMR"},
            {"name": "SupportXMR", "address": "pool.supportxmr.com:443", "tls": True, "coin": "XMR", "min_payout": "0.1 XMR"},
            {"name": "NanoPool", "address": "xmr-eu1.nanopool.org:14433", "tls": True, "coin": "XMR", "min_payout": "0.1 XMR"},
            {"name": "HashVault", "address": "pool.hashvault.pro:443", "tls": True, "coin": "XMR", "min_payout": "0.1 XMR"},
            {"name": "HeroMiners", "address": "monero.herominers.com:1111", "tls": False, "coin": "XMR", "min_payout": "0.1 XMR"},
            {"name": "C3Pool", "address": "mine.c3pool.com:13333", "tls": False, "coin": None, "min_payout": "0.001 XMR", "no_api": True},
        ]
        
    def detect_os(self) -> str:
        """Detect the operating system"""
        system = platform.system()
        if system == 'Darwin':
            return 'macos'
        elif system == 'Linux':
            return 'linux'
        elif system == 'Windows':
            return 'windows'
        else:
            return 'unknown'
    
    def detect_cpu_arch(self) -> str:
        """Detect CPU architecture"""
        machine = platform.machine().lower()
        if machine in ['arm64', 'aarch64']:
            return 'arm64'
        elif machine in ['x86_64', 'amd64', 'x64']:
            return 'x64'
        elif machine in ['i386', 'i686', 'x86']:
            return 'x86'
        else:
            return machine
    
    def detect_cpu_model(self) -> str:
        """Detect the specific CPU model for worker naming"""
        try:
            system = platform.system()
            
            if system == 'Darwin':
                # macOS - use sysctl to get CPU brand
                result = subprocess.run(
                    ['sysctl', '-n', 'machdep.cpu.brand_string'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    cpu_brand = result.stdout.strip()
                    # Extract Apple Silicon chip name (M1, M2, M3, M4, etc.)
                    if 'Apple M' in cpu_brand:
                        match = re.search(r'Apple M(\d+)', cpu_brand)
                        if match:
                            return f"m{match.group(1)}"
                    return "mac"
            
            elif system == 'Linux':
                # Linux - read from /proc/cpuinfo
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            cpu_model = line.split(':')[1].strip()
                            # Try to extract meaningful CPU identifier
                            # AMD Ryzen
                            if 'Ryzen' in cpu_model:
                                match = re.search(r'Ryzen\s+(\d+)\s+(\d+)', cpu_model)
                                if match:
                                    return f"ryzen{match.group(1)}-{match.group(2)}"
                                return "ryzen"
                            # Intel Core
                            elif 'Intel' in cpu_model:
                                match = re.search(r'i(\d)-(\d+)', cpu_model)
                                if match:
                                    return f"i{match.group(1)}-{match.group(2)}"
                                return "intel"
                            break
                return "linux"
            
            elif system == 'Windows':
                # Windows - use wmic
                result = subprocess.run(
                    ['wmic', 'cpu', 'get', 'name'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        cpu_model = lines[1].strip()
                        # AMD Ryzen
                        if 'Ryzen' in cpu_model:
                            match = re.search(r'Ryzen\s+(\d+)\s+(\d+)', cpu_model)
                            if match:
                                return f"ryzen{match.group(1)}-{match.group(2)}"
                            return "ryzen"
                        # Intel Core
                        elif 'Intel' in cpu_model:
                            match = re.search(r'i(\d)-(\d+)', cpu_model)
                            if match:
                                return f"i{match.group(1)}-{match.group(2)}"
                            return "intel"
                return "windows"
        
        except Exception as e:
            print(f"Could not detect CPU model: {e}")
        
        # Fallback to generic names
        arch = self.detect_cpu_arch()
        return "arm64" if arch == 'arm64' else "x64"
    
    def detect_nvidia_gpu(self) -> bool:
        """Detect if an NVIDIA GPU is present"""
        os_type = self.detect_os()
        
        try:
            if os_type == 'windows':
                # Try nvidia-smi on Windows
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                if result.returncode == 0 and result.stdout.strip():
                    gpu_name = result.stdout.strip().split('\n')[0]
                    print(f"NVIDIA GPU detected: {gpu_name}")
                    return True
            else:
                # Linux/macOS - try nvidia-smi
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    gpu_name = result.stdout.strip().split('\n')[0]
                    print(f"NVIDIA GPU detected: {gpu_name}")
                    return True
        except FileNotFoundError:
            pass
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            print(f"Error detecting NVIDIA GPU: {e}")
        
        return False
    
    def get_latest_xmrig_release(self) -> Optional[Tuple[str, list]]:
        """Fetch the latest XMRig version and available files from GitHub"""
        try:
            url = "https://api.github.com/repos/xmrig/xmrig/releases/latest"
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                version = data['tag_name'].lstrip('v')
                
                # Extract list of asset filenames
                assets = [asset['name'] for asset in data.get('assets', [])]
                
                return version, assets
        except Exception as e:
            print(f"Error fetching latest release info: {e}")
            return None
    
    def get_latest_gminer_release(self) -> Optional[Tuple[str, List[dict]]]:
        """Fetch the latest GMiner version and available files from GitHub"""
        try:
            url = "https://api.github.com/repos/develsoftware/GMinerRelease/releases/latest"
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                version = data['tag_name'].lstrip('v')
                
                # Extract assets with download URLs
                assets = []
                for asset in data.get('assets', []):
                    assets.append({
                        'name': asset['name'],
                        'url': asset['browser_download_url']
                    })
                
                return version, assets
        except Exception as e:
            print(f"Error fetching latest GMiner release info: {e}")
            return None
    
    def find_matching_file(self, assets: list, os_type: str, arch: str) -> Optional[str]:
        """Find the matching file for the given OS and architecture"""
        # Build search patterns based on OS and architecture
        if os_type == 'macos':
            if arch == 'arm64':
                patterns = ['macos-arm64.tar.gz', 'macos-aarch64.tar.gz']
            elif arch == 'x64':
                patterns = ['macos-x64.tar.gz', 'macos-x86_64.tar.gz']
            else:
                return None
        elif os_type == 'linux':
            if arch == 'arm64':
                patterns = ['linux-static-arm64.tar.gz', 'linux-arm64.tar.gz', 'linux-aarch64.tar.gz']
            elif arch == 'x64':
                patterns = ['linux-static-x64.tar.gz', 'linux-x64.tar.gz', 'linux-x86_64.tar.gz']
            else:
                return None
        elif os_type == 'windows':
            if arch == 'x64':
                patterns = ['msvc-win64.zip', 'win64.zip', 'windows-x64.zip']
            elif arch == 'x86':
                patterns = ['msvc-win32.zip', 'win32.zip', 'windows-x86.zip']
            else:
                return None
        else:
            return None
        
        # Search for matching file
        for asset in assets:
            for pattern in patterns:
                if pattern in asset.lower():
                    return asset
        
        return None
    
    def find_matching_gminer_file(self, assets: List[dict], os_type: str) -> Optional[dict]:
        """Find the matching GMiner file for the given OS"""
        for asset in assets:
            name = asset['name'].lower()
            if os_type == 'windows' and 'windows' in name and name.endswith('.zip'):
                return asset
            elif os_type == 'linux' and 'linux' in name and name.endswith('.tar.xz'):
                return asset
        return None
    
    def check_xmrig_installed(self) -> bool:
        """Check if xmrig is installed"""
        # Check in script directory first
        local_paths = [
            os.path.join(self.script_dir, 'xmrig'),
            os.path.join(self.script_dir, 'xmrig.exe'),
        ]
        
        for path in local_paths:
            if os.path.exists(path) and os.access(path, os.X_OK if os.name != 'nt' else os.F_OK):
                return True
        
        # Check in system PATH (Unix-like systems)
        if os.name != 'nt':
            try:
                result = subprocess.run(['which', 'xmrig'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=5)
                if result.returncode == 0:
                    return True
            except:
                pass
        else:
            # Windows - check with 'where' command
            try:
                result = subprocess.run(['where', 'xmrig.exe'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=5)
                if result.returncode == 0:
                    return True
            except:
                pass
        
        return False
    
    def check_gminer_installed(self) -> bool:
        """Check if GMiner is installed in script directory"""
        os_type = self.detect_os()
        
        if os_type == 'windows':
            gminer_path = os.path.join(self.script_dir, 'miner.exe')
        else:
            gminer_path = os.path.join(self.script_dir, 'miner')
        
        return os.path.exists(gminer_path) and os.access(gminer_path, os.X_OK if os.name != 'nt' else os.F_OK)
    
    def download_file_with_progress(self, url: str, local_filename: str, max_retries: int = 3) -> bool:
        """Download a file with progress indication and retry logic"""
        for attempt in range(max_retries):
            try:
                req = urllib.request.Request(url)
                req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
                req.add_header('Accept', '*/*')
                
                with urllib.request.urlopen(req, timeout=30) as response:
                    total_size = int(response.headers.get('Content-Length', 0))
                    downloaded = 0
                    
                    with open(local_filename, 'wb') as f:
                        while True:
                            chunk = response.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size > 0:
                                percent = (downloaded / total_size) * 100
                                print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='', flush=True)
                
                print("\nDownload complete!")
                return True
                
            except urllib.error.HTTPError as e:
                print(f"\nHTTP Error {e.code}: {e.reason}")
                if attempt < max_retries - 1:
                    print(f"Retrying... (Attempt {attempt + 2}/{max_retries})")
                    time.sleep(2)
                else:
                    return False
            except Exception as e:
                print(f"\nError downloading file: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying... (Attempt {attempt + 2}/{max_retries})")
                    time.sleep(2)
                else:
                    return False
        
        return False
    
    def download_and_install_xmrig(self) -> bool:
        """Download and install XMRig based on OS and architecture"""
        os_type = self.detect_os()
        arch = self.detect_cpu_arch()
        
        print(f"\nDetected OS: {os_type}")
        print(f"Detected Architecture: {arch}")
        
        if os_type not in ['macos', 'linux', 'windows']:
            print(f"\nAutomatic installation is not supported for this OS.")
            print(f"Please install XMRig manually from: https://github.com/xmrig/xmrig/releases")
            return False
        
        # Get latest release info
        print("\nFetching latest XMRig release from GitHub...")
        release_info = self.get_latest_xmrig_release()
        
        if not release_info:
            print("Could not fetch release information from GitHub.")
            print("Please install XMRig manually from: https://github.com/xmrig/xmrig/releases")
            return False
        
        version, assets = release_info
        print(f"Latest version: {version}")
        print(f"Found {len(assets)} release files")
        
        # Find matching file for this OS and architecture
        filename = self.find_matching_file(assets, os_type, arch)
        
        if not filename:
            print(f"\nCould not find a compatible XMRig release for {os_type} {arch}")
            print(f"Available files:")
            for asset in assets:
                if asset.endswith(('.tar.gz', '.zip')):
                    print(f"  - {asset}")
            print("\nPlease download manually from: https://github.com/xmrig/xmrig/releases")
            return False
        
        print(f"Found matching file: {filename}")
        
        # Try HTTPS first
        https_url = f"https://github.com/xmrig/xmrig/releases/download/v{version}/{filename}"
        
        print(f"\nReady to download: {filename}")
        print(f"URL: {https_url}")
        
        # Prompt user (default to Yes)
        while True:
            response = input("\nDownload and install XMRig? (Y/N) [Y]: ").strip().upper()
            if response == '':
                response = 'Y'
            if response in ['Y', 'N']:
                break
            print("Please enter Y or N (or press ENTER for Yes)")
        
        if response == 'N':
            print("Installation cancelled.")
            return False
        
        # Download with HTTPS
        print(f"\nDownloading {filename} via HTTPS...")
        local_filename = os.path.join(self.script_dir, filename)
        
        download_success = self.download_file_with_progress(https_url, local_filename)
        
        # If HTTPS failed, offer HTTP fallback
        if not download_success:
            print(f"\nHTTPS download failed after multiple attempts.")
            print("\n" + "="*60)
            print("HTTP FALLBACK OPTION")
            print("="*60)
            print("WARNING: HTTP connections are not encrypted and less secure.")
            print("Only use this option if HTTPS continues to fail.")
            
            while True:
                response = input("\nAttempt download via HTTP instead? (Y/N) [N]: ").strip().upper()
                if response == '':
                    response = 'N'
                if response in ['Y', 'N']:
                    break
                print("Please enter Y or N (or press ENTER for No)")
            
            if response == 'Y':
                http_url = f"http://github.com/xmrig/xmrig/releases/download/v{version}/{filename}"
                print(f"\nDownloading {filename} via HTTP...")
                print(f"URL: {http_url}")
                
                download_success = self.download_file_with_progress(http_url, local_filename)
                
                if not download_success:
                    print(f"\nHTTP download also failed.")
                    print(f"Please download manually from: https://github.com/xmrig/xmrig/releases")
                    return False
            else:
                print("HTTP download declined.")
                print(f"Please download manually from: https://github.com/xmrig/xmrig/releases")
                return False
        
        # Extract
        print("Extracting archive...")
        try:
            is_zip = filename.endswith('.zip')
            
            if is_zip:
                # Windows ZIP file - extract all files to maintain driver support
                with zipfile.ZipFile(local_filename, 'r') as zip_ref:
                    # Get the root folder name in the archive
                    namelist = zip_ref.namelist()
                    root_folder = None
                    
                    # Find the root folder
                    for name in namelist:
                        if '/' in name:
                            root_folder = name.split('/')[0]
                            break
                    
                    # Extract all files
                    print("Extracting all files (including WinRing0 drivers)...")
                    for member in namelist:
                        # Skip directories
                        if member.endswith('/'):
                            continue
                        
                        # Remove root folder from path
                        if root_folder and member.startswith(root_folder + '/'):
                            target_name = member[len(root_folder) + 1:]
                        else:
                            target_name = member
                        
                        # Skip if empty
                        if not target_name:
                            continue
                        
                        # Extract file
                        with zip_ref.open(member) as source:
                            target_path = os.path.join(self.script_dir, target_name)
                            
                            # Create subdirectories if needed
                            os.makedirs(os.path.dirname(target_path), exist_ok=True)
                            
                            with open(target_path, 'wb') as target:
                                target.write(source.read())
                        
                        if target_name == 'xmrig.exe':
                            print(f"  ✓ {target_name}")
                        elif 'WinRing0' in target_name or target_name.endswith('.sys'):
                            print(f"  ✓ {target_name} (driver)")
                
                # Ensure ZIP file is closed before attempting to delete
                xmrig_path = os.path.join(self.script_dir, 'xmrig.exe')
                print(f"\nXMRig installed successfully at: {xmrig_path}")
                print("WinRing0 drivers extracted for MSR MOD support")
            else:
                # Unix TAR.GZ file
                with tarfile.open(local_filename, 'r:gz') as tar:
                    # Find the xmrig binary in the archive
                    for member in tar.getmembers():
                        if member.name.endswith('/xmrig') or member.name == 'xmrig':
                            member.name = 'xmrig'
                            tar.extract(member, self.script_dir)
                            break
                
                xmrig_path = os.path.join(self.script_dir, 'xmrig')
                
                # Make executable (Unix-like systems)
                os.chmod(xmrig_path, 0o755)
                print(f"XMRig installed successfully at: {xmrig_path}")
            
            # Clean up - add a small delay on Windows to ensure file handles are released
            if is_zip:
                time.sleep(0.5)
            
            try:
                os.remove(local_filename)
                print("Cleaned up temporary files.")
            except Exception as cleanup_error:
                print(f"Note: Could not remove temporary file {local_filename}")
                print(f"      You can manually delete it later.")
                # Don't fail the installation if cleanup fails
            
            return True
            
        except Exception as e:
            print(f"Error extracting archive: {e}")
            return False
    
    def download_and_install_gminer(self) -> bool:
        """Download and install GMiner for GPU mining"""
        os_type = self.detect_os()
        
        # GMiner only supports Windows and Linux
        if os_type not in ['windows', 'linux']:
            print(f"\nGMiner is not available for {os_type}.")
            print("GPU mining with GMiner is only supported on Windows and Linux.")
            return False
        
        print("\n" + "="*60)
        print("GMiner Installation (GPU Mining)")
        print("="*60)
        
        # Get latest release info
        print("\nFetching latest GMiner release from GitHub...")
        release_info = self.get_latest_gminer_release()
        
        if not release_info:
            print("Could not fetch release information from GitHub.")
            print("Please install GMiner manually from: https://github.com/develsoftware/GMinerRelease/releases")
            return False
        
        version, assets = release_info
        print(f"Latest version: {version}")
        print(f"Found {len(assets)} release files")
        
        # Find matching file for this OS
        asset = self.find_matching_gminer_file(assets, os_type)
        
        if not asset:
            print(f"\nCould not find a compatible GMiner release for {os_type}")
            print("Available files:")
            for a in assets:
                print(f"  - {a['name']}")
            print("\nPlease download manually from: https://github.com/develsoftware/GMinerRelease/releases")
            return False
        
        filename = asset['name']
        download_url = asset['url']
        
        print(f"Found matching file: {filename}")
        print(f"\nReady to download: {filename}")
        
        # Prompt user (default to Yes)
        while True:
            response = input("\nDownload and install GMiner for GPU mining? (Y/N) [Y]: ").strip().upper()
            if response == '':
                response = 'Y'
            if response in ['Y', 'N']:
                break
            print("Please enter Y or N (or press ENTER for Yes)")
        
        if response == 'N':
            print("GMiner installation cancelled. GPU mining will not be available.")
            return False
        
        # Download to temp directory
        print(f"\nDownloading {filename}...")
        temp_dir = tempfile.mkdtemp()
        local_filename = os.path.join(temp_dir, filename)
        
        download_success = self.download_file_with_progress(download_url, local_filename)
        
        if not download_success:
            print(f"\nDownload failed.")
            print("Please download GMiner manually from: https://github.com/develsoftware/GMinerRelease/releases")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False
        
        # Extract just the miner executable
        print("Extracting GMiner...")
        try:
            if os_type == 'windows':
                # Windows ZIP file
                with zipfile.ZipFile(local_filename, 'r') as zip_ref:
                    # Find miner.exe in the archive
                    for member in zip_ref.namelist():
                        if member.endswith('miner.exe'):
                            # Extract to temp, then copy just the exe
                            zip_ref.extract(member, temp_dir)
                            src_path = os.path.join(temp_dir, member)
                            dst_path = os.path.join(self.script_dir, 'miner.exe')
                            shutil.copy2(src_path, dst_path)
                            print(f"  ✓ miner.exe")
                            break
                
                gminer_path = os.path.join(self.script_dir, 'miner.exe')
            else:
                # Linux tar.xz file
                import lzma
                
                with lzma.open(local_filename) as xz:
                    with tarfile.open(fileobj=xz) as tar:
                        # Find the miner binary in the archive
                        for member in tar.getmembers():
                            if member.name.endswith('/miner') or member.name == 'miner':
                                # Extract to temp
                                tar.extract(member, temp_dir)
                                src_path = os.path.join(temp_dir, member.name)
                                dst_path = os.path.join(self.script_dir, 'miner')
                                shutil.copy2(src_path, dst_path)
                                os.chmod(dst_path, 0o755)
                                print(f"  ✓ miner")
                                break
                
                gminer_path = os.path.join(self.script_dir, 'miner')
            
            print(f"\nGMiner installed successfully at: {gminer_path}")
            
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return True
            
        except Exception as e:
            print(f"Error extracting GMiner: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return False
    
    def prompt_wallet_address(self) -> str:
        """Prompt user for wallet address"""
        default_wallet = "85NGrygcwq36kjLaNKZevT53H4EeHRQYeje5Y3gq3GYkKsEpwKpGjqd1tGxAVEjDfxEha6SYtyNYPbmPXduYqy47Q6JwbuW"
        
        print("\n" + "="*60)
        print("Monero Wallet Configuration")
        print("="*60)
        print(f"\nDefault wallet address:")
        print(f"{default_wallet}")
        print("\nPress ENTER to use the default wallet, or paste your own:")
        
        wallet = input("Wallet Address: ").strip()
        
        if not wallet:
            wallet = default_wallet
            print("Using default wallet address.")
        else:
            print("Using your wallet address.")
        
        return wallet
    
    def prompt_pool_selection(self) -> Tuple[str, bool, Optional[str]]:
        """Prompt user to select a mining pool"""
        print("\n" + "="*60)
        print("Mining Pool Selection")
        print("="*60)
        print("\nAvailable pools:")
        
        for i, pool in enumerate(self.known_pools):
            default_marker = " (default)" if i == 0 else ""
            tls_marker = " [TLS]" if pool["tls"] else ""
            min_payout = pool.get("min_payout", "")
            no_api = " [no stats]" if pool.get("no_api") else ""
            print(f"  {i + 1}. {pool['name']}: {pool['address']}{tls_marker} (Min: {min_payout}){no_api}{default_marker}")
        
        print(f"  {len(self.known_pools) + 1}. Custom pool (enter your own)")
        
        print("\nPress ENTER to use MoneroOcean, or enter a number:")
        
        while True:
            choice = input("Pool Selection: ").strip()
            
            if choice == '':
                # Default to MoneroOcean
                pool = self.known_pools[0]
                print(f"Using {pool['name']} pool.")
                return pool['address'], pool['tls'], pool.get('coin')
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(self.known_pools):
                    pool = self.known_pools[choice_num - 1]
                    print(f"Using {pool['name']} pool.")
                    return pool['address'], pool['tls'], pool.get('coin')
                elif choice_num == len(self.known_pools) + 1:
                    # Custom pool
                    print("\nEnter custom pool address (e.g., pool.example.com:3333):")
                    custom_addr = input("Pool Address: ").strip()
                    if not custom_addr:
                        print("Invalid address. Please try again.")
                        continue
                    
                    while True:
                        tls_choice = input("Enable TLS? (Y/N) [N]: ").strip().upper()
                        if tls_choice == '':
                            tls_choice = 'N'
                        if tls_choice in ['Y', 'N']:
                            break
                        print("Please enter Y or N")
                    
                    print(f"Using custom pool: {custom_addr}")
                    return custom_addr, tls_choice == 'Y', "XMR"
                else:
                    print(f"Please enter a number between 1 and {len(self.known_pools) + 1}")
            except ValueError:
                print("Please enter a valid number or press ENTER for default")
    
    def check_windows_admin(self) -> bool:
        """Check if script is running with Administrator privileges on Windows"""
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    def prompt_msr_mod(self, os_type: str) -> bool:
        """Prompt user to enable MSR MOD for performance optimization"""
        # MSR MOD is only supported on Windows and Linux
        if os_type not in ['windows', 'linux']:
            return False
        
        print("\n" + "="*60)
        print("MSR MOD - Performance Optimization")
        print("="*60)
        print("\nMSR (Model-Specific Register) modification can improve")
        print("mining performance by 10-50% by optimizing CPU behavior.")
        print("\nNOTE: Requires administrator/root privileges")
        print("WARNING: May cause system instability if misconfigured")
        
        if os_type == 'linux':
            print("\nOn Linux, MSR MOD requires:")
            print("  1. Loading the msr kernel module")
            print("  2. Running the miner with sudo/root")
        elif os_type == 'windows':
            print("\nOn Windows, MSR MOD requires:")
            print("  1. Running as Administrator")
            print("  2. XMRig will automatically load WinRing0 driver")
        
        while True:
            response = input("\nEnable MSR MOD? (Y/N) [N]: ").strip().upper()
            if response == '':
                response = 'N'
            if response in ['Y', 'N']:
                break
            print("Please enter Y or N (or press ENTER for No)")
        
        if response == 'Y':
            print("MSR MOD will be enabled.")
            if os_type == 'windows':
                if not self.check_windows_admin():
                    print("\n⚠ WARNING: Not running as Administrator!")
                    print("  Please restart this script by:")
                    print("  1. Right-click on Command Prompt or PowerShell")
                    print("  2. Select 'Run as Administrator'")
                    print("  3. Run the script again")
                else:
                    print("✓ Running with Administrator privileges")
            else:
                print("\nSetting up MSR support on Linux...")
                self.setup_linux_msr()
            return True
        else:
            print("MSR MOD disabled (standard mining mode).")
            return False
    
    def setup_linux_msr(self):
        """Setup MSR kernel module on Linux"""
        try:
            # Check if msr module is loaded
            result = subprocess.run(['lsmod'], capture_output=True, text=True)
            if 'msr' not in result.stdout:
                print("\nLoading MSR kernel module...")
                print("You may be prompted for your sudo password.")
                
                # Try to load msr module
                result = subprocess.run(['sudo', 'modprobe', 'msr'], 
                                      capture_output=True, 
                                      text=True)
                
                if result.returncode == 0:
                    print("✓ MSR module loaded successfully")
                else:
                    print("⚠ Could not load MSR module automatically")
                    print("  Please run manually: sudo modprobe msr")
            else:
                print("✓ MSR module already loaded")
            
            # Check if running with sudo
            if os.geteuid() != 0:
                print("\n⚠ IMPORTANT: You must run the miner with sudo for MSR to work!")
                print("  Example: sudo python3 miner-monero.py")
            else:
                print("✓ Running with root privileges")
                
        except Exception as e:
            print(f"\n⚠ Could not setup MSR automatically: {e}")
            print("  Manual setup required:")
            print("  1. Run: sudo modprobe msr")
            print("  2. Start miner with: sudo python3 miner-monero.py")
    
    def prompt_gpu_mining(self) -> bool:
        """Prompt user to enable GPU mining if NVIDIA GPU is detected"""
        print("\n" + "="*60)
        print("GPU Mining Configuration")
        print("="*60)
        print("\nAn NVIDIA GPU was detected on your system.")
        print("GPU mining can significantly increase your earnings by mining")
        print("GPU-friendly algorithms (like KAWPOW) while your CPU mines RandomX.")
        print("Both will be paid out in XMR via MoneroOcean.")
        
        while True:
            response = input("\nEnable GPU mining? (Y/N) [Y]: ").strip().upper()
            if response == '':
                response = 'Y'
            if response in ['Y', 'N']:
                break
            print("Please enter Y or N (or press ENTER for Yes)")
        
        if response == 'Y':
            print("GPU mining will be enabled.")
            return True
        else:
            print("GPU mining disabled.")
            return False
    
    def setup_initial_config(self):
        """Setup initial configuration with user input"""
        os_type = self.detect_os()
        arch = self.detect_cpu_arch()
        is_mac = os_type == 'macos'
        
        # Get wallet address from user
        wallet_address = self.prompt_wallet_address()
        
        # Get pool selection from user
        pool_address, tls_enabled, coin = self.prompt_pool_selection()
        
        # Prompt for MSR MOD
        enable_msr = self.prompt_msr_mod(os_type)
        
        # Check for NVIDIA GPU and prompt for GPU mining
        enable_gpu_mining = False
        if self.has_nvidia_gpu:
            enable_gpu_mining = self.prompt_gpu_mining()
        
        # Determine xmrig path based on OS
        if os_type == 'windows':
            miner_executable = "xmrig.exe"
        else:
            # macOS and Linux
            miner_executable = "./xmrig"
        
        # Detect CPU model for worker name
        cpu_model = self.detect_cpu_model()
        worker_name = f"{cpu_model}-miner"
        
        config = {
            "wallet_address": wallet_address,
            "mining_mode": "pool",
            "miner_executable": miner_executable,
            "pool_address": pool_address,
            "pool_password": "x",
            "worker_name": worker_name,
            "node_address": "127.0.0.1:18081",
            "threads": 0,
            "cpu_max_usage": 75,
            "huge_pages": True if not is_mac else False,
            "randomx_mode": "auto",
            "tls_enabled": tls_enabled,
            "coin": coin,
            "nicehash": False,
            "msr_mod": enable_msr,
            "gpu_mining": enable_gpu_mining,
            "gpu_algo": "kawpow",
            "gpu_worker_name": "gpu-worker",
            "extra_args": [],
            "log_file": "monero-miner.log",
            "api_port": 0,
            "donate_level": 1,
            "stats_update_interval": 300
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=4)
        
        print(f"\nConfiguration saved to: {self.config_file}")
        print(f"Worker name set to: {worker_name}")
        return config
        
    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        if not os.path.exists(self.config_file):
            print(f"Configuration file '{self.config_file}' not found.")
            print("Setting up initial configuration...")
            return None
            
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            self.validate_config(config)
            return config
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in configuration file: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            sys.exit(1)
    
    def validate_config(self, config: Dict):
        """Validate required configuration fields"""
        required_fields = ['wallet_address', 'mining_mode']
        
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        
        if config['mining_mode'] not in ['solo', 'pool']:
            raise ValueError("mining_mode must be 'solo' or 'pool'")
        
        if config['mining_mode'] == 'pool' and 'pool_address' not in config:
            raise ValueError("pool_address is required for pool mining")
    
    def is_supportxmr_pool(self) -> bool:
        """Check if the configured pool is SupportXMR"""
        if self.config['mining_mode'] != 'pool':
            return False
        
        pool_addr = self.config.get('pool_address', '').lower()
        return 'supportxmr.com' in pool_addr
    
    def is_moneroocean_pool(self) -> bool:
        """Check if the configured pool is MoneroOcean"""
        if self.config['mining_mode'] != 'pool':
            return False
        
        pool_addr = self.config.get('pool_address', '').lower()
        return 'moneroocean' in pool_addr
    
    def is_nanopool_pool(self) -> bool:
        """Check if the configured pool is NanoPool"""
        if self.config['mining_mode'] != 'pool':
            return False
        
        pool_addr = self.config.get('pool_address', '').lower()
        return 'nanopool' in pool_addr
    
    def is_hashvault_pool(self) -> bool:
        """Check if the configured pool is HashVault"""
        if self.config['mining_mode'] != 'pool':
            return False
        
        pool_addr = self.config.get('pool_address', '').lower()
        return 'hashvault' in pool_addr
    
    def is_herominers_pool(self) -> bool:
        """Check if the configured pool is HeroMiners"""
        if self.config['mining_mode'] != 'pool':
            return False
        
        pool_addr = self.config.get('pool_address', '').lower()
        return 'herominers' in pool_addr
    
    def fetch_pool_stats(self) -> Optional[Dict]:
        """Fetch mining statistics from pool API"""
        try:
            wallet = self.config['wallet_address']
            
            if self.is_supportxmr_pool():
                url = f"https://www.supportxmr.com/api/miner/{wallet}/stats"
            elif self.is_moneroocean_pool():
                url = f"https://api.moneroocean.stream/miner/{wallet}/stats"
            elif self.is_nanopool_pool():
                url = f"https://api.nanopool.org/v1/xmr/user/{wallet}"
            elif self.is_hashvault_pool():
                url = f"https://api.hashvault.pro/v3/monero/wallet/{wallet}/stats?chart=false"
            elif self.is_herominers_pool():
                url = f"https://monero.herominers.com/api/stats_address?address={wallet}"
            else:
                return None
            
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                # NanoPool wraps data differently
                if self.is_nanopool_pool():
                    if data.get('status') is True:
                        return data.get('data')
                    else:
                        error_msg = data.get('error', 'Unknown error')
                        if 'not found' in error_msg.lower():
                            print(f"\nNanoPool: Account not found yet.")
                            print("  This is normal for new miners - NanoPool creates your account")
                            print("  ~30 minutes after your first submitted share.")
                        else:
                            print(f"\nNanoPool API error: {error_msg}")
                        return None
                
                # HashVault returns data directly but may have error field
                if self.is_hashvault_pool():
                    if 'error' in data:
                        error_msg = data.get('error', 'Unknown error')
                        if 'not found' in str(error_msg).lower() or 'no data' in str(error_msg).lower():
                            print(f"\nHashVault: Account not found yet.")
                            print("  This is normal for new miners - stats appear after submitting shares.")
                        else:
                            print(f"\nHashVault API error: {error_msg}")
                        return None
                    return data
                
                return data
        except urllib.error.HTTPError as e:
            print(f"\nError fetching pool stats (HTTP {e.code}): {e.reason}")
            return None
        except urllib.error.URLError as e:
            print(f"\nError fetching pool stats (Network): {e.reason}")
            return None
        except Exception as e:
            print(f"\nError fetching pool stats: {e}")
            return None
    
    def format_hashrate(self, hash_rate: float) -> str:
        """Format hash rate in human-readable format"""
        if hash_rate >= 1000000:
            return f"{hash_rate / 1000000:.2f} MH/s"
        elif hash_rate >= 1000:
            return f"{hash_rate / 1000:.2f} KH/s"
        else:
            return f"{hash_rate:.2f} H/s"
    
    def format_xmr(self, piconero: int) -> str:
        """Convert piconero to XMR"""
        xmr = piconero / 1000000000000
        return f"{xmr:.12f} XMR"
    
    def format_time_ago(self, timestamp: int) -> str:
        """Format timestamp as time ago"""
        now = int(time.time())
        diff = now - timestamp
        
        if diff < 60:
            return f"{diff} seconds ago"
        elif diff < 3600:
            return f"{diff // 60} minutes ago"
        elif diff < 86400:
            return f"{diff // 3600} hours ago"
        else:
            return f"{diff // 86400} days ago"
    
    def display_pool_stats(self, stats: Dict):
        """Display pool statistics in a readable format"""
        print("\n" + "="*60)
        print(f"Pool Statistics - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # NanoPool uses different field names
        if self.is_nanopool_pool():
            hash_rate = stats.get('hashrate', 0) or 0
            avg_hashrate_1h = stats.get('avgHashrate', {}).get('h1', 0) or 0
            avg_hashrate_6h = stats.get('avgHashrate', {}).get('h6', 0) or 0
            avg_hashrate_24h = stats.get('avgHashrate', {}).get('h24', 0) or 0
            balance = stats.get('balance', 0) or 0
            unconfirmed_balance = stats.get('unconfirmed_balance', 0) or 0
            
            print(f"Current Hashrate:  {self.format_hashrate(hash_rate)}")
            print(f"1h Avg Hashrate:   {self.format_hashrate(avg_hashrate_1h)}")
            print(f"6h Avg Hashrate:   {self.format_hashrate(avg_hashrate_6h)}")
            print(f"24h Avg Hashrate:  {self.format_hashrate(avg_hashrate_24h)}")
            print(f"\nBalance:           {balance:.12f} XMR")
            print(f"Unconfirmed:       {unconfirmed_balance:.12f} XMR")
            
            # Worker info
            workers = stats.get('workers', [])
            if workers:
                print(f"\nWorkers ({len(workers)}):")
                for worker in workers:
                    w_name = worker.get('id', 'unknown')
                    w_hashrate = worker.get('hashrate', 0) or 0
                    w_rating = worker.get('rating', 0) or 0
                    print(f"  {w_name}: {self.format_hashrate(w_hashrate)} (rating: {w_rating})")
        
        # HashVault uses its own format
        elif self.is_hashvault_pool():
            collective = stats.get('collective', {})
            revenue = stats.get('revenue', {})
            
            hash_rate = collective.get('hashRate', 0) or 0
            total_hashes = collective.get('totalHashes', 0) or 0
            valid_shares = collective.get('validShares', 0) or 0
            invalid_shares = collective.get('invalidShares', 0) or 0
            
            confirmed_balance = revenue.get('confirmedBalance', 0) or 0
            pending_balance = revenue.get('pendingBalance', 0) or 0
            total_paid = revenue.get('totalPaid', 0) or 0
            
            print(f"Current Hashrate:  {self.format_hashrate(hash_rate)}")
            print(f"Total Hashes:      {total_hashes:,}")
            print(f"Valid Shares:      {valid_shares:,}")
            print(f"Invalid Shares:    {invalid_shares:,}")
            
            if valid_shares + invalid_shares > 0:
                efficiency = (valid_shares / (valid_shares + invalid_shares)) * 100
                print(f"Share Efficiency:  {efficiency:.2f}%")
            
            print(f"\nConfirmed Balance: {self.format_xmr(confirmed_balance)}")
            print(f"Pending Balance:   {self.format_xmr(pending_balance)}")
            print(f"Total Paid:        {self.format_xmr(total_paid)}")
        
        elif self.is_herominers_pool():
            # HeroMiners uses stats_address format
            stats_data = stats.get('stats', {})
            hash_rate = stats_data.get('hashrate', 0) or 0
            hash_rate_24h = stats_data.get('hashrate_24h', 0) or 0
            balance = stats_data.get('balance', 0) or 0
            paid = stats_data.get('paid', 0) or 0
            last_share = stats_data.get('lastShare', 0) or 0
            
            # Convert last_share to int if it's a string
            if isinstance(last_share, str):
                try:
                    last_share = int(last_share)
                except (ValueError, TypeError):
                    last_share = 0
            
            print(f"Current Hashrate:  {self.format_hashrate(hash_rate)}")
            print(f"24h Avg Hashrate:  {self.format_hashrate(hash_rate_24h)}")
            print(f"\nBalance:           {self.format_xmr(balance)}")
            print(f"Total Paid:        {self.format_xmr(paid)}")
            
            if last_share > 0:
                print(f"Last Share:        {self.format_time_ago(last_share)}")
            
            # Worker info if available
            workers = stats.get('workers', [])
            if workers:
                print(f"\nWorkers ({len(workers)}):")
                for worker in workers:
                    w_name = worker.get('name', 'unknown')
                    w_hashrate = worker.get('hashrate', 0) or 0
                    print(f"  {w_name}: {self.format_hashrate(w_hashrate)}")
        
        else:
            # SupportXMR and MoneroOcean format
            hash_rate = stats.get('hash', 0) or 0
            total_hashes = stats.get('totalHashes', 0) or 0
            valid_shares = stats.get('validShares', 0) or 0
            invalid_shares = stats.get('invalidShares', 0) or 0
            amt_paid = stats.get('amtPaid', 0) or 0
            amt_due = stats.get('amtDue', 0) or 0
            txn_count = stats.get('txnCount', 0) or 0
            last_hash = stats.get('lastHash', 0) or 0
            
            print(f"Current Hashrate:  {self.format_hashrate(hash_rate)}")
            print(f"Total Hashes:      {total_hashes:,}")
            print(f"Valid Shares:      {valid_shares:,}")
            print(f"Invalid Shares:    {invalid_shares:,}")
            
            if valid_shares + invalid_shares > 0:
                efficiency = (valid_shares / (valid_shares + invalid_shares)) * 100
                print(f"Share Efficiency:  {efficiency:.2f}%")
            
            print(f"\nAmount Paid:       {self.format_xmr(amt_paid)}")
            print(f"Amount Due:        {self.format_xmr(amt_due)}")
            print(f"Total Earned:      {self.format_xmr(amt_paid + amt_due)}")
            print(f"Payment Count:     {txn_count}")
            
            if last_hash > 0:
                print(f"Last Share:        {self.format_time_ago(last_hash)}")
            
            # Calculate earnings projections if currently mining (hashrate > 0)
            if hash_rate > 0 and last_hash > 0:
                # Calculate time elapsed since start (use last_hash as reference)
                now = int(time.time())
                time_elapsed_seconds = now - last_hash + (now - last_hash)  # Approximate mining duration
                
                # More accurate: use total earned and estimate time mining
                # We'll calculate based on amt_due if available
                total_earned_piconero = amt_paid + amt_due
                
                if total_earned_piconero > 0 and total_hashes > 0:
                    # Calculate earnings rate per hash
                    xmr_per_hash = total_earned_piconero / total_hashes
                    
                    # Project future earnings based on current hashrate
                    seconds_per_day = 86400
                    seconds_per_month = seconds_per_day * 30.44  # Average month
                    seconds_per_year = seconds_per_day * 365.25  # Account for leap years
                    
                    hashes_per_day = hash_rate * seconds_per_day
                    hashes_per_month = hash_rate * seconds_per_month
                    hashes_per_year = hash_rate * seconds_per_year
                    
                    xmr_per_day = (hashes_per_day * xmr_per_hash)
                    xmr_per_month = (hashes_per_month * xmr_per_hash)
                    xmr_per_year = (hashes_per_year * xmr_per_hash)
                    
                    print(f"\nProjected Earnings (at current hashrate):")
                    print(f"Earnings Per Day:   {self.format_xmr(int(xmr_per_day))}")
                    print(f"Earnings Per Month: {self.format_xmr(int(xmr_per_month))}")
                    print(f"Earnings Per Year:  {self.format_xmr(int(xmr_per_year))}")
        
        print("="*60 + "\n")
    
    def stats_monitor_thread(self):
        """Background thread to periodically fetch and display pool stats"""
        interval = self.config.get('stats_update_interval', 300)
        
        # Display stats immediately
        print("\nFetching initial pool statistics...")
        stats = self.fetch_pool_stats()
        if stats:
            self.display_pool_stats(stats)
        else:
            print("Could not fetch initial pool statistics. Will retry...\n")
        
        # Continue periodic updates
        while not self.stop_stats:
            # Wait for the interval, checking stop flag frequently
            for _ in range(interval):
                if self.stop_stats:
                    break
                time.sleep(1)
            
            if self.stop_stats:
                break
            
            # Fetch and display stats
            stats = self.fetch_pool_stats()
            if stats:
                self.display_pool_stats(stats)
    
    def start_stats_monitor(self):
        """Start the stats monitoring thread"""
        if not self.is_supportxmr_pool() and not self.is_moneroocean_pool() and not self.is_nanopool_pool() and not self.is_hashvault_pool() and not self.is_herominers_pool():
            return
        
        if self.is_herominers_pool():
            pool_name = "HeroMiners"
        elif self.is_hashvault_pool():
            pool_name = "HashVault"
        elif self.is_nanopool_pool():
            pool_name = "NanoPool"
        elif self.is_moneroocean_pool():
            pool_name = "MoneroOcean"
        else:
            pool_name = "SupportXMR"
        
        print(f"\nPool stats monitoring enabled for {pool_name}")
        interval = self.config.get('stats_update_interval', 300)
        print(f"Stats will be updated every {interval} seconds ({interval // 60} minutes)")
        
        self.stop_stats = False
        self.stats_thread = threading.Thread(target=self.stats_monitor_thread, daemon=True)
        self.stats_thread.start()
    
    def stop_stats_monitor(self):
        """Stop the stats monitoring thread"""
        if self.stats_thread:
            self.stop_stats = True
            self.stats_thread.join(timeout=2)
    
    def initialize(self):
        """Initialize the miner - check for xmrig and setup config"""
        # Check for NVIDIA GPU first
        print("\nChecking for NVIDIA GPU...")
        self.has_nvidia_gpu = self.detect_nvidia_gpu()
        if not self.has_nvidia_gpu:
            print("No NVIDIA GPU detected. CPU mining only.")
        
        # Check if xmrig is installed
        xmrig_was_just_installed = False
        
        if not self.check_xmrig_installed():
            print("\n" + "="*60)
            print("XMRig Not Detected")
            print("="*60)
            print("\nXMRig mining software is not installed.")
            
            # Try to install
            if not self.download_and_install_xmrig():
                print("\nPlease install XMRig manually and try again.")
                sys.exit(1)
            
            xmrig_was_just_installed = True
        else:
            print("\nXMRig detected ✓")
        
        # Load or create config
        self.config = self.load_config()
        
        # If config doesn't exist OR xmrig was just installed, setup new config with wallet prompt
        if self.config is None or xmrig_was_just_installed:
            self.config = self.setup_initial_config()
        
        # Check if GPU mining is enabled and GMiner needs to be installed
        if self.config.get('gpu_mining', False) and self.has_nvidia_gpu:
            if not self.check_gminer_installed():
                print("\n" + "="*60)
                print("GMiner Not Detected")
                print("="*60)
                print("\nGMiner is required for GPU mining.")
                
                if not self.download_and_install_gminer():
                    print("\nGPU mining will be disabled.")
                    self.config['gpu_mining'] = False
            else:
                print("GMiner detected ✓")
        
        # If NVIDIA GPU detected but not in config, offer to enable GPU mining
        if self.has_nvidia_gpu and not self.config.get('gpu_mining', False):
            if self.is_moneroocean_pool():  # Only MoneroOcean supports multi-algo
                print("\n" + "="*60)
                print("GPU Mining Available")
                print("="*60)
                print("\nAn NVIDIA GPU was detected but GPU mining is not enabled.")
                
                while True:
                    response = input("\nWould you like to enable GPU mining? (Y/N) [Y]: ").strip().upper()
                    if response == '':
                        response = 'Y'
                    if response in ['Y', 'N']:
                        break
                    print("Please enter Y or N")
                
                if response == 'Y':
                    self.config['gpu_mining'] = True
                    self.config['gpu_algo'] = 'kawpow'
                    self.config['gpu_worker_name'] = 'gpu-worker'
                    
                    # Save updated config
                    with open(self.config_file, 'w') as f:
                        json.dump(self.config, f, indent=4)
                    
                    # Install GMiner if needed
                    if not self.check_gminer_installed():
                        if not self.download_and_install_gminer():
                            print("\nGPU mining will be disabled.")
                            self.config['gpu_mining'] = False
    
    def build_command(self) -> list:
        """Build the XMRig mining command based on configuration"""
        cmd = [self.config.get('miner_executable', 'xmrig')]
        
        # Add wallet address
        wallet = self.config['wallet_address']
        
        # Configure based on mining mode
        if self.config['mining_mode'] == 'solo':
            # Solo mining - connect to local node
            node_addr = self.config.get('node_address', '127.0.0.1:18081')
            cmd.extend(['--daemon', '--daemon-poll-interval=1000'])
            cmd.extend(['--url', node_addr])
            cmd.extend(['--user', wallet])
            print(f"Solo mining mode - connecting to node at {node_addr}")
        else:
            # Pool mining
            pool_addr = self.config['pool_address']
            cmd.extend(['--url', pool_addr])
            cmd.extend(['--user', wallet])
            
            # Add worker name if specified
            worker = self.config.get('worker_name')
            if worker:
                cmd.extend(['--rig-id', worker])
            
            # Pool password
            pool_pass = self.config.get('pool_password', 'x')
            cmd.extend(['--pass', pool_pass])
            
            # TLS
            if self.config.get('tls_enabled', True):
                cmd.append('--tls')
            
            # NiceHash mode
            if self.config.get('nicehash', False):
                cmd.append('--nicehash')
            
            # Coin specification (required by some pools)
            coin = self.config.get('coin')
            if coin:
                cmd.extend(['--coin', coin])
            
            print(f"Pool mining mode - connecting to pool at {pool_addr}")
        
        # CPU Thread configuration
        threads = self.config.get('threads', 0)
        if threads > 0:
            cmd.extend(['--threads', str(threads)])
        
        # CPU max usage
        cpu_max = self.config.get('cpu_max_usage')
        if cpu_max:
            cmd.extend(['--cpu-max-threads-hint', str(cpu_max)])
        
        # Huge pages (not supported on macOS)
        if self.config.get('huge_pages', False) and platform.system() != 'Darwin':
            cmd.append('--hugepages')
        
        # RandomX mode
        rx_mode = self.config.get('randomx_mode', 'auto')
        if rx_mode in ['light', 'fast']:
            cmd.extend(['--randomx-mode', rx_mode])
        
        # MSR MOD for performance optimization
        if self.config.get('msr_mod', False):
            cmd.append('--randomx-wrmsr')
            print("MSR MOD enabled for optimized performance")
        
        # API port for monitoring
        api_port = self.config.get('api_port', 0)
        if api_port > 0:
            cmd.extend(['--http-port', str(api_port)])
            cmd.append('--http-enabled')
        
        # Donate level
        donate = self.config.get('donate_level', 1)
        cmd.extend(['--donate-level', str(donate)])
        
        # Add any extra arguments
        extra_args = self.config.get('extra_args', [])
        if extra_args:
            cmd.extend(extra_args)
        
        return cmd
    
    def build_gminer_command(self) -> list:
        """Build the GMiner command for GPU mining"""
        os_type = self.detect_os()
        
        if os_type == 'windows':
            gminer_path = os.path.join(self.script_dir, 'miner.exe')
        else:
            gminer_path = os.path.join(self.script_dir, 'miner')
        
        wallet = self.config['wallet_address']
        gpu_algo = self.config.get('gpu_algo', 'kawpow')
        gpu_worker = self.config.get('gpu_worker_name', 'gpu-worker')
        
        # MoneroOcean GPU mining endpoint
        cmd = [
            gminer_path,
            '--server', 'gulf.moneroocean.stream:10128',
            '--user', wallet,
            '--pass', f'{gpu_worker}~{gpu_algo}',
            '--algo', gpu_algo,
            '--proto', 'stratum'
        ]
        
        return cmd
    
    def start_gpu_mining(self):
        """Start the GPU mining process with GMiner"""
        if not self.config.get('gpu_mining', False):
            return
        
        if not self.has_nvidia_gpu:
            print("GPU mining enabled but no NVIDIA GPU detected. Skipping GPU miner.")
            return
        
        if not self.check_gminer_installed():
            print("GPU mining enabled but GMiner not installed. Skipping GPU miner.")
            return
        
        cmd = self.build_gminer_command()
        
        print("\n" + "="*60)
        print("Starting GPU Miner (GMiner)")
        print("="*60)
        print(f"Algorithm: {self.config.get('gpu_algo', 'kawpow')}")
        print(f"Worker: {self.config.get('gpu_worker_name', 'gpu-worker')}")
        print(f"Command: {' '.join(cmd)}")
        print("="*60 + "\n")
        
        try:
            # Start GMiner process
            if self.detect_os() == 'windows':
                self.gpu_process = subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                self.gpu_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            print("GPU miner started successfully.")
            
        except FileNotFoundError:
            print(f"\nError: GMiner executable not found.")
            print("GPU mining will not be available.")
        except Exception as e:
            print(f"Error starting GPU miner: {e}")
    
    def stop_gpu_mining(self):
        """Stop the GPU mining process"""
        if self.gpu_process:
            print("Stopping GPU miner...")
            self.gpu_process.terminate()
            try:
                self.gpu_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("Force killing GPU miner process...")
                self.gpu_process.kill()
            print("GPU miner stopped.")
    
    def start_mining(self):
        """Start the mining process"""
        cmd = self.build_command()
        
        # Check if MSR is enabled but not running with proper privileges
        if self.config.get('msr_mod', False):
            os_type = self.detect_os()
            if os_type == 'linux' and os.geteuid() != 0:
                print("\n" + "="*60)
                print("⚠ WARNING: MSR MOD ENABLED BUT NOT RUNNING AS ROOT")
                print("="*60)
                print("MSR modifications require root privileges on Linux.")
                print("Please restart the miner with sudo:")
                print(f"  sudo python3 {sys.argv[0]}")
                print("\nContinuing anyway (MSR features will be disabled)...")
                print("="*60 + "\n")
                time.sleep(3)
            elif os_type == 'windows' and not self.check_windows_admin():
                print("\n" + "="*60)
                print("⚠ WARNING: MSR MOD ENABLED BUT NOT RUNNING AS ADMINISTRATOR")
                print("="*60)
                print("MSR modifications require Administrator privileges on Windows.")
                print("Please restart this script as Administrator:")
                print("  1. Right-click Command Prompt or PowerShell")
                print("  2. Select 'Run as Administrator'")
                print(f"  3. Run: python {sys.argv[0]}")
                print("\nContinuing anyway (MSR features will be disabled)...")
                print("="*60 + "\n")
                time.sleep(3)
        
        print("\n" + "="*60)
        print("Monero Miner Starting")
        print("="*60)
        print(f"Wallet: {self.config['wallet_address'][:20]}...{self.config['wallet_address'][-10:]}")
        print(f"Mode: {self.config['mining_mode'].upper()}")
        print(f"Platform: {platform.system()} ({platform.machine()})")
        print(f"CPU Mining: Enabled (XMRig)")
        print(f"GPU Mining: {'Enabled (GMiner)' if self.config.get('gpu_mining', False) and self.has_nvidia_gpu else 'Disabled'}")
        print(f"Command: {' '.join(cmd)}")
        print("="*60 + "\n")
        
        # Start GPU mining first if enabled
        self.start_gpu_mining()
        
        # Start stats monitoring if using SupportXMR or MoneroOcean
        self.start_stats_monitor()
        
        # Setup logging if specified
        log_file = self.config.get('log_file')
        log_handle = None
        
        try:
            if log_file:
                log_handle = open(log_file, 'a')
                log_handle.write(f"\n{'='*60}\n")
                log_handle.write(f"Mining started at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                log_handle.write(f"Command: {' '.join(cmd)}\n")
                log_handle.write(f"{'='*60}\n\n")
                log_handle.flush()
            
            # Start the miner process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE if log_handle else None,
                stderr=subprocess.STDOUT if log_handle else None,
                universal_newlines=True,
                bufsize=1
            )
            
            # Monitor output if logging
            if log_handle and self.process.stdout:
                try:
                    for line in self.process.stdout:
                        print(line, end='')
                        log_handle.write(line)
                        log_handle.flush()
                except KeyboardInterrupt:
                    print("\n\nReceived interrupt signal. Stopping miner...")
                    self.stop_mining()
            else:
                # Wait for process to complete
                self.process.wait()
                
        except FileNotFoundError:
            print(f"\nError: Miner executable '{cmd[0]}' not found.")
            print("\nPlease ensure XMRig is properly installed.")
            sys.exit(1)
        except Exception as e:
            print(f"Error starting miner: {e}")
            sys.exit(1)
        finally:
            if log_handle:
                log_handle.close()
            self.stop_stats_monitor()
            self.stop_gpu_mining()
    
    def stop_mining(self):
        """Stop the mining process"""
        self.stop_stats_monitor()
        self.stop_gpu_mining()
        
        if self.process:
            print("Stopping CPU miner...")
            self.process.terminate()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                print("Force killing CPU miner process...")
                self.process.kill()
            print("CPU miner stopped.")
    
    def show_stats(self):
        """Display mining statistics if API is enabled"""
        api_port = self.config.get('api_port', 0)
        if api_port > 0:
            print(f"\nMining stats available at: http://127.0.0.1:{api_port}")
            print("You can view real-time statistics in your browser")

def signal_handler(signum, frame):
    """Handle interrupt signals"""
    print("\n\nShutdown signal received...")
    sys.exit(0)

def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    config_file = "miner-monero.json"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    
    # Create miner instance
    miner = MoneroMiner(config_file)
    
    try:
        # Initialize (check xmrig, setup config)
        miner.initialize()
        
        # Show stats info and start mining
        miner.show_stats()
        miner.start_mining()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        miner.stop_mining()
    except Exception as e:
        print(f"\nError: {e}")
        if miner.process:
            miner.stop_mining()
        sys.exit(1)

if __name__ == "__main__":
    main()
